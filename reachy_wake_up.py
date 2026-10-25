"""Wake Reachy Mini up and check it is ready, before starting a session.

Run this after switching the robot on, and start the conversation script once
it prints READY:

    .\\venv-client\\Scripts\\python.exe reachy_wake_up.py

Why it exists: on the first runs of the day the conversation script connects
to a robot that is still starting. The daemon answers on port 8000 well before
the motor backend, the WebRTC signalling server and the audio stack behind it
are up, so the session gets "Task did not complete in time", lost connections
and play_sound timeouts. Later runs are fine because by then everything is
loaded.

This script waits for each layer in turn -- for minutes if need be, rather
than a few quick retries -- and exercises every path the conversation uses
once, so the slow first-time work happens here and not in front of a child:

  1. find the robot on the network
  2. daemon running, motor backend up
  3. WebRTC signalling server up
  4. motors on, wake-up move (which also plays the wake-up sound)
  5. a short head and antenna movement
  6. speaker: the built-in test sound, then a sound uploaded from this PC
     (the upload is what timed out in the conversation script)
  7. WebRTC media link, opened the way the conversation opens it, listening
     to the microphone

It reads REACHY_HOST / REACHY_PORT from .env like the conversation script,
changes no files, and leaves the robot awake.
"""

import io
import math
import os
import socket
import sys
import time
import wave
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

REACHY_HOST = os.getenv("REACHY_HOST", "reachy-mini.local")
REACHY_PORT = int(os.getenv("REACHY_PORT", "8000"))
REACHY_MEDIA_BACKEND = os.getenv("REACHY_MEDIA_BACKEND", "webrtc")
REACHY_SIGNALLING_PORT = 8443  # hardcoded in the SDK's media_manager

S2S_HOST = os.getenv("S2S_HOST", "127.0.0.1")
S2S_PORT = int(os.getenv("S2S_PORT", "8765"))

# How long to wait for each layer before giving up. A robot that has just
# been switched on can take minutes; a warm one passes every step at once.
FIND_TIMEOUT = 180.0
BACKEND_TIMEOUT = 300.0
SIGNALLING_TIMEOUT = 180.0
MOVE_TIMEOUT = 30.0
FIRST_MIC_SAMPLE_TIMEOUT = 8.0
MIC_LISTEN_SECONDS = 4.0
SILENT_PEAK = 0.005  # same threshold as the conversation script's mic log

TOTAL_STEPS = 7


class NotReady(Exception):
    """A step could not complete; the message says what was being waited for."""


def step(n: int, title: str) -> float:
    print(f"\n[{n}/{TOTAL_STEPS}] {title}")
    return time.monotonic()


def done(message: str, started: float) -> float:
    took = time.monotonic() - started
    print(f"      OK - {message} ({took:.1f}s)")
    return took


def wait_for(
    check: Callable[[], Any], timeout: float, waiting_for: str, interval: float = 2.0
) -> Any:
    """Call check() until it returns something truthy; NotReady at timeout.

    Prints a progress line every ten seconds so a long wait reads as waiting
    rather than as a hang.
    """
    start = time.monotonic()
    last_note = start
    while True:
        result = check()
        if result:
            return result
        now = time.monotonic()
        if now - start >= timeout:
            raise NotReady(f"gave up after {timeout:.0f}s {waiting_for}")
        if now - last_note >= 10.0:
            print(f"      ... still {waiting_for} ({now - start:.0f}s)")
            last_note = now
        time.sleep(interval)


def with_retries(fn: Callable[[], Any], what: str, tries: int = 3) -> Any:
    """Retry fn on a timeout: the first audio calls on a cold robot are slow."""
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except requests.Timeout:
            if attempt == tries:
                raise NotReady(f"{what} timed out {tries} times")
            print(f"      ... {what} timed out, trying again ({attempt}/{tries})")


# ── Network ──────────────────────────────────────────────────────────────────

def resolve(host: str) -> Optional[str]:
    """IPv4 address for host, or None. Literal addresses are returned as-is."""
    try:
        socket.inet_aton(host)
        return host
    except OSError:
        pass
    try:
        return socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    except socket.gaierror:
        return None


def port_open(ip: str, port: int) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=2.0):
            return True
    except OSError:
        return False


class DaemonApi:
    """The robot daemon's REST API, addressed by IP so mDNS cannot drop out."""

    def __init__(self, ip: str, port: int) -> None:
        self.base = f"http://{ip}:{port}/api"

    def get(self, path: str, timeout: float = 10.0, **kwargs: Any) -> requests.Response:
        return requests.get(self.base + path, timeout=timeout, **kwargs)

    def post(self, path: str, timeout: float = 10.0, **kwargs: Any) -> requests.Response:
        return requests.post(self.base + path, timeout=timeout, **kwargs)


# ── Steps ────────────────────────────────────────────────────────────────────

def find_robot() -> str:
    ip = wait_for(lambda: resolve(REACHY_HOST), FIND_TIMEOUT, f"looking up {REACHY_HOST}")
    if ip != REACHY_HOST:
        print(f"      {REACHY_HOST} -> {ip}")
    wait_for(
        lambda: port_open(ip, REACHY_PORT),
        FIND_TIMEOUT,
        f"waiting for the daemon to answer on {ip}:{REACHY_PORT}",
    )
    return ip


def wait_for_backend(api: DaemonApi) -> str:
    """Wait until the motor backend is up, and return the motor mode.

    The status field backend_status.ready cannot be used for this: the daemon
    creates it as False and never updates it (reachy_mini 1.9), so it reads
    False on a perfectly healthy robot. Endpoints that need the backend answer
    503 "Backend not running" until it is up, which is the real signal.
    """
    asked_to_start = False

    def check() -> Optional[str]:
        nonlocal asked_to_start
        try:
            status = api.get("/daemon/status", timeout=5).json()
        except (requests.RequestException, ValueError):
            return None

        state = status.get("state")
        if state == "error":
            raise NotReady(f"the daemon reports an error: {status.get('error')}")
        backend_error = (status.get("backend_status") or {}).get("error")
        if backend_error:
            raise NotReady(f"the motor backend reports an error: {backend_error}")
        if state in ("stopped", "not_initialized") and not asked_to_start:
            print(f"      daemon is {state}; asking it to start")
            try:
                api.post("/daemon/start", params={"wake_up": "false"})
            except requests.RequestException as e:
                print(f"      could not ask the daemon to start: {e}")
            asked_to_start = True
            return None
        if state != "running":
            return None

        try:
            r = api.get("/motors/status", timeout=5)
        except requests.RequestException:
            return None
        return r.json().get("mode") if r.ok else None

    return wait_for(check, BACKEND_TIMEOUT, "waiting for the motor backend")


def run_move(api: DaemonApi, path: str, body: Optional[Dict[str, Any]] = None) -> None:
    """Start a daemon move and block until it has finished."""
    r = api.post(path, json=body)
    r.raise_for_status()
    uuid = r.json()["uuid"]

    def finished() -> bool:
        try:
            running = api.get("/move/running", timeout=5).json()
        except (requests.RequestException, ValueError):
            return False
        return all(move.get("uuid") != uuid for move in running)

    wait_for(finished, MOVE_TIMEOUT, "waiting for the move to finish", interval=0.1)


def head_pose(yaw_deg: float = 0.0) -> Dict[str, float]:
    return {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": math.radians(yaw_deg)}


def stretch(api: DaemonApi) -> None:
    """Look left, look right, back to centre, with an antenna wiggle."""
    for yaw_deg, antennas in ((20.0, [0.5, -0.5]), (-20.0, [-0.5, 0.5]), (0.0, [0.0, 0.0])):
        run_move(
            api,
            "/move/goto",
            {"head_pose": head_pose(yaw_deg), "antennas": antennas, "duration": 0.8},
        )


def chime_wav() -> bytes:
    """Two short soft notes as a WAV file, built in memory."""
    rate = 16000
    notes = []
    for freq in (660.0, 880.0):
        t = np.arange(int(rate * 0.15)) / rate
        notes.append(np.sin(2 * np.pi * freq * t) * np.hanning(t.size))
    audio = (np.concatenate(notes) * 0.25 * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(audio.tobytes())
    return buf.getvalue()


def test_speaker(api: DaemonApi) -> float:
    """Play the built-in test sound, then upload and play a chime.

    The upload is the path the conversation script's play_sound() takes: the
    SDK sends the file to /api/media/sounds/upload with a 30 second timeout,
    and the daemon probes it with GStreamer before accepting it -- slow on a
    cold robot. Returns how long the upload took.
    """
    def builtin() -> None:
        r = api.post("/volume/test-sound", timeout=30)
        r.raise_for_status()
        if r.json().get("status") == "busy":
            print("      built-in test sound skipped: the robot's audio device is busy")

    with_retries(builtin, "built-in test sound")
    time.sleep(1.5)  # let it finish before the next sound

    data = chime_wav()

    def upload() -> str:
        r = api.post(
            "/media/sounds/upload",
            timeout=60,
            files={"file": ("wake_up_check.wav", data, "audio/wav")},
        )
        r.raise_for_status()
        return r.json()["path"]

    t0 = time.monotonic()
    remote_path = with_retries(upload, "sound upload")
    upload_s = time.monotonic() - t0
    print(f"      sound upload took {upload_s:.1f}s")

    with_retries(
        lambda: api.post("/media/play_sound", timeout=30, json={"file": remote_path}).raise_for_status(),
        "playing the uploaded sound",
    )
    return upload_s


def pin_media_host(host: str) -> None:
    """Point the WebRTC media link at the address we already reach the robot on.

    Same patch as in reachy_s2s_conversation.py (copied, not imported: that
    module connects to Supabase when imported). The SDK takes the media
    address from the daemon's wlan_ip, which is the hotspot gateway 10.42.0.1
    when the robot also runs its own hotspot, and unreachable from here.
    """
    from reachy_mini.media import media_manager

    original_init = media_manager.MediaManager.__init__

    def patched_init(self: Any, *args: Any, **kwargs: Any) -> None:
        reported = kwargs.get("signalling_host")
        if reported and reported != host:
            print(f"      robot reports its media address as {reported}; using {host} instead")
            kwargs["signalling_host"] = host
        original_init(self, *args, **kwargs)

    media_manager.MediaManager.__init__ = patched_init


def check_media_link(ip: str) -> Tuple[float, float]:
    """Open the media link the way the conversation does and listen.

    Returns (seconds until the first microphone sample, peak level).
    """
    # Imported here: loading the SDK pulls in GStreamer, which is itself slow
    # the first time after the PC starts -- another thing worth warming.
    from reachy_mini import ReachyMini

    pin_media_host(ip)

    reachy = None
    for attempt in range(1, 6):
        try:
            reachy = ReachyMini(
                connection_mode="network",
                host=ip,
                port=REACHY_PORT,
                media_backend=REACHY_MEDIA_BACKEND,
            )
            break
        except (OSError, KeyError) as e:  # same set the conversation script retries
            print(f"      media link not ready ({attempt}/5): {type(e).__name__}: {e}")
            time.sleep(3.0)
    if reachy is None:
        raise NotReady("could not open the WebRTC media link")

    with reachy:
        reachy.media.start_recording()
        t0 = time.monotonic()
        first_sample: Optional[float] = None
        peak = 0.0
        while True:
            now = time.monotonic()
            if first_sample is None and now - t0 > FIRST_MIC_SAMPLE_TIMEOUT:
                break
            if first_sample is not None and now - t0 > first_sample + MIC_LISTEN_SECONDS:
                break
            sample = reachy.media.get_audio_sample()
            if sample is None:
                time.sleep(0.05)
                continue
            if first_sample is None:
                first_sample = now - t0
                print(f"      microphone audio arriving; listening {MIC_LISTEN_SECONDS:.0f}s...")
            chunk = np.asarray(sample, dtype=np.float32)
            if chunk.size:
                peak = max(peak, float(np.abs(chunk).max()))
        try:
            reachy.media.stop_recording()
        except Exception:
            pass

    if first_sample is None:
        raise NotReady(f"no microphone audio within {FIRST_MIC_SAMPLE_TIMEOUT:.0f}s")
    return first_sample, peak


# ── Main ─────────────────────────────────────────────────────────────────────

def banner(lines: list) -> None:
    print()
    print("=" * 70)
    for line in lines:
        print(line)
    print("=" * 70)


def main() -> int:
    print(f"[Wake] Waking Reachy Mini at {REACHY_HOST}:{REACHY_PORT}")
    print("[Wake] Each step waits for the robot, so the first run after power-on may take a few minutes.")
    run_start = time.monotonic()
    current = "starting"

    try:
        current = "finding the robot"
        t = step(1, "Finding the robot on the network")
        ip = find_robot()
        done(f"daemon answering at {ip}", t)
        api = DaemonApi(ip, REACHY_PORT)

        current = "waiting for the motor backend"
        t = step(2, "Waiting for the daemon and motor backend")
        mode = wait_for_backend(api)
        backend_s = done(f"backend up, motors {mode}", t)

        current = "waiting for WebRTC signalling"
        t = step(3, "Waiting for the WebRTC signalling server")
        wait_for(
            lambda: port_open(ip, REACHY_SIGNALLING_PORT),
            SIGNALLING_TIMEOUT,
            f"waiting for port {REACHY_SIGNALLING_PORT}",
        )
        done(f"port {REACHY_SIGNALLING_PORT} open", t)

        current = "waking up"
        t = step(4, "Motors on and wake-up move")
        if mode != "enabled":
            api.post("/motors/set_mode/enabled").raise_for_status()
            print(f"      motors were {mode}; now enabled")
        run_move(api, "/move/play/wake_up")
        wake_s = done("wake-up move finished", t)

        current = "moving"
        t = step(5, "Stretching: look left, right, centre")
        stretch(api)
        done("head and antennas moved", t)

        current = "testing the speaker"
        t = step(6, "Speaker check (you should hear two sounds)")
        upload_s = test_speaker(api)
        done("speaker played both sounds", t)

        current = "opening the media link"
        t = step(7, "WebRTC media link and microphone")
        first_mic_s, mic_peak = check_media_link(ip)
        done(f"first mic audio after {first_mic_s:.1f}s, peak {mic_peak:.4f}", t)

    except KeyboardInterrupt:
        print("\n[Wake] Stopped.")
        return 1
    except (NotReady, requests.RequestException) as e:
        hints = [
            f"[Wake] NOT READY - failed while {current}.",
            f"  {type(e).__name__}: {e}",
            "",
            "  - give the robot another minute and run this again",
            "  - check the Reachy Mini App is running and shows connected",
        ]
        if resolve(REACHY_HOST) == REACHY_HOST:
            hints.append(
                f"  - REACHY_HOST is a fixed IP ({REACHY_HOST}); the robot's IP changes"
                " between networks, REACHY_HOST=reachy-mini.local follows it"
            )
        hints.append("  - if it keeps failing at the same step, switch the robot off and on again")
        banner(hints)
        return 1

    total = time.monotonic() - run_start
    lines = [
        "[Wake] READY - Reachy is awake. Start the conversation script now.",
        f"  robot {ip}, total {total:.0f}s"
        f" (backend {backend_s:.0f}s, wake-up {wake_s:.1f}s, sound upload {upload_s:.1f}s)",
    ]
    if mic_peak < SILENT_PEAK:
        lines.append(
            f"  - microphone was very quiet (peak {mic_peak:.4f}); fine in a silent"
            " room, but speak near Reachy and re-run if unsure"
        )
    if port_open(S2S_HOST, S2S_PORT):
        lines.append(f"  - speech-to-speech server is running on {S2S_HOST}:{S2S_PORT}")
    else:
        lines.append(
            f"  - speech-to-speech server is NOT running on {S2S_HOST}:{S2S_PORT}:"
            " start test_reachy_conversation.py first"
        )
    banner(lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
