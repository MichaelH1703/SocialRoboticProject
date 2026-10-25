"""Start the speech-to-speech realtime server so a physical Reachy Mini can talk to it.

Run with the project venv:
    ./venv/Scripts/python.exe test_reachy_conversation.py

Reachy Mini already runs its own realtime client (mic capture + speaker playback).
This script just brings up the backend on this PC and prints the WebSocket URL to
enter in Reachy Mini's client settings: ws://<this PC's LAN IP>:8765/v1/realtime
"""

import os
import socket
import sys
import urllib.request

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Only the optional tuning overrides come from .env; the server still
    # starts on its defaults without python-dotenv installed.
    pass

# LLM served locally via `ollama serve` (defaults to this URL)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
# qwen2.5:3b rather than qwen3: qwen3 is a reasoning model and, measured on the
# actual recount prompt, spent ~1335 tokens per turn (19.5s) producing a ~25
# token spoken reply, while also being too large to fit beside Parakeet and
# Qwen3-TTS -- Ollama ran it 49% on CPU. qwen2.5:3b emits ~27 tokens, no
# reasoning, and fits 100% on GPU: 2.5s per turn.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

WS_HOST = os.getenv("S2S_WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("S2S_PORT", "8765"))

# VAD tuning. The old script ran webrtcvad locally; Silero now runs inside the
# server, so these are CLI flags rather than env vars read at runtime.
#
# SILENCE_MS carries over directly and matters most: the server's 64 ms default
# ends a turn on the slightest pause, which cuts a child off mid-sentence.
VAD_MIN_SILENCE_MS = os.getenv("SILENCE_MS", "800")

# Silero speech-probability threshold. The 0.6 default proved too strict for
# Reachy's WebRTC microphone: VAD saw ~1.4s segments but scored only 32-128ms
# of each as speech, below min_speech_ms, so every turn was discarded. Raise
# this back toward 0.6 if background noise starts triggering false turns.
VAD_THRESH = os.getenv("VAD_THRESH", "0.35")

# MAX_LISTEN_SECONDS was a recording cap; the server's equivalent is expressed
# in milliseconds and forces a split rather than ending the capture.
_max_listen_s = os.getenv("MAX_LISTEN_SECONDS", "")
VAD_MAX_SPEECH_MS = str(int(float(_max_listen_s) * 1000)) if _max_listen_s else ""

S2S_TTS = os.getenv("S2S_TTS", "kokoro").lower()

# bm_fable is a British male voice, the closest match to the previous
# en_GB-alan-medium Piper voice, and far less emotive than Qwen3-TTS's Aiden.
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "bm_fable")
KOKORO_LANG = os.getenv("KOKORO_LANG", "b")
KOKORO_SPEED = os.getenv("KOKORO_SPEED", "1.0")

if S2S_TTS == "kokoro":
    TTS_ARGS = [
        "--tts", "kokoro",
        "--kokoro_voice", KOKORO_VOICE,
        "--kokoro_lang_code", KOKORO_LANG,
        "--kokoro_speed", KOKORO_SPEED,
    ]
else:
    TTS_ARGS = ["--tts", "qwen3", "--qwen3_tts_backend", "torch"]

PIPELINE_ARGS = [
    "--mode", "realtime",
    "--ws_host", WS_HOST,
    "--ws_port", str(WS_PORT),
    "--stt", "parakeet-tdt",
    "--llm_backend", "chat-completions",
    "--model_name", OLLAMA_MODEL,
    "--responses_api_base_url", OLLAMA_BASE_URL,
    "--responses_api_api_key", "ollama",
    *TTS_ARGS,
    "--thresh", VAD_THRESH,
    "--min_silence_ms", VAD_MIN_SILENCE_MS,
    "--enable_live_transcription",
]

if VAD_MAX_SPEECH_MS:
    PIPELINE_ARGS += ["--max_speech_ms", VAD_MAX_SPEECH_MS]


def lan_ip() -> str:
    """Best-effort LAN IP: opens a UDP socket toward a public address without sending data."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def check_ollama() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/models", timeout=2) as resp:
            return resp.status == 200
    except OSError:
        return False


def limit_to_one_question() -> None:
    """Cut every reply off at its first question, before it is spoken.

    The prompt already asks for at most one question, but qwen2.5:3b does not
    reliably follow it and still stacks two ("Who was there? Did you have
    fun?"), which is a lot to put to a child at once. So the rule is enforced
    on the model's output as it streams: everything after the first question
    mark is dropped, so it is never spoken or sent to the client. The same cut
    is applied to the reply written back to the model's history, so it sees
    only what the child actually heard and is not nudged toward two questions
    again by its own earlier replies.

    Patches the LLM handler shared by both OpenAI-compatible backends, so it
    must run before the pipeline starts.
    """
    from speech_to_speech.LLM import base_openai_compatible_language_model as llm

    def through_first_question(text: str) -> str:
        cut = text.find("?")
        return text if cut < 0 else text[: cut + 1]

    original_iter_events = llm.BaseOpenAICompatibleHandler._iter_events

    def _iter_events(self, api_response):  # type: ignore[no-untyped-def]
        asked = False
        for event in original_iter_events(self, api_response):
            if isinstance(event, llm.TextDelta):
                if asked:
                    continue
                kept = through_first_question(event.text)
                asked = kept.endswith("?")
                event = llm.TextDelta(text=kept)
            elif isinstance(event, llm.AssistantMessage):
                parts = []
                for part in event.content:
                    if part.text:
                        kept = through_first_question(part.text)
                        if kept != part.text:
                            print(f"[Question limit] Dropped: {part.text[len(kept):].strip()!r}")
                        part = part.model_copy(update={"text": kept})
                    parts.append(part)
                event = llm.AssistantMessage(content=parts)
            yield event

    llm.BaseOpenAICompatibleHandler._iter_events = _iter_events


def install_safety_gate() -> None:
    """Put the hard safety rules (reachy_safety.py) around the model.

    Before generation, the child's latest words are checked. When a critical or
    high rule fires -- or a critical one has already stopped the practice --
    the model is not called at all: the scripted line goes out as this turn's
    reply and into the history, so what the model remembers matches what the
    child heard. A medium rule still lets the model answer, with one extra
    instruction for that reply only.

    After generation, the reply is checked before it reaches TTS, and one that
    breaks a hard rule (a promised secret, "I love you", a medicine, the
    therapist's notes, a swear word) is replaced. The whole reply is held to do
    that; it is at most two short sentences, and the client buffers the whole
    utterance before playing it anyway.

    The robot client runs the same rules on the same transcript, which is how
    it knows to alert the operator, with no extra protocol between the two.
    Safety state is kept on the conversation's Chat, which the server creates
    fresh for each connection, so a stopped practice ends with its session.

    Must run after limit_to_one_question, so the reply check sees the cut text.
    """
    import reachy_safety
    from openai.types.realtime.conversation_item import RealtimeConversationItemUserMessage
    from speech_to_speech.LLM import base_openai_compatible_language_model as llm
    from speech_to_speech.LLM.chat import make_assistant_message, make_system_message

    class ChatSafety:
        def __init__(self) -> None:
            self.monitor = reachy_safety.SafetyMonitor()
            self.turn = None
            self.verdict = reachy_safety.Verdict()

    def assess(chat):  # type: ignore[no-untyped-def]
        safety = getattr(chat, "_reachy_safety", None)
        if safety is None:
            safety = chat._reachy_safety = ChatSafety()

        buffer = list(chat.buffer)
        if not buffer or not isinstance(buffer[-1], RealtimeConversationItemUserMessage):
            return reachy_safety.Verdict()  # nothing new from the child, e.g. the greeting
        last = buffer[-1]
        text = " ".join(p.text for p in last.content if p.type == "input_text" and p.text)

        # Assessed once per user turn: a retried generation for the same words
        # must not count as another turn of the stopped practice.
        turn = (last.id, text)
        if turn != safety.turn:
            safety.turn = turn
            safety.verdict = safety.monitor.assess(text)
        return safety.verdict

    def scripted_turn(self, chat, turn, text):  # type: ignore[no-untyped-def]
        """Emit `text` as this turn's reply, the way _generate emits the model's."""
        if not self._generation_is_stale(turn.gen) and self._turn_output_allowed(turn.turn_id, turn.turn_revision):
            yield self._chunk(turn, text=text)
            chat.add_item(make_assistant_message(text))
            chat.trim_if_needed(self.compactor)
        yield llm.EndOfResponse(turn_id=turn.turn_id, turn_revision=turn.turn_revision, cancel_generation=turn.gen)

    original_generate = llm.BaseOpenAICompatibleHandler._generate

    def _generate(self, active_chat, original_chat, turn, optional_kwargs):  # type: ignore[no-untyped-def]
        if llm.is_out_of_band(turn.response):
            yield from original_generate(self, active_chat, original_chat, turn, optional_kwargs)
            return

        verdict = assess(original_chat)
        if verdict.reply:
            source = reachy_safety.describe(verdict.rule) if verdict.rule else "practice stopped"
            print(f"[Safety] {source}: scripted reply, model not called")
            yield from scripted_turn(self, original_chat, turn, verdict.reply)
            return

        if verdict.guidance:
            print(f"[Safety] {reachy_safety.describe(verdict.rule)}: model guided for this reply")
            # active_chat is this turn's copy, so the extra instruction is
            # never written back to the history.
            system = active_chat.init_chat_message
            text = system.content[0].text if system and system.content else ""
            active_chat.init_chat(make_system_message(f"{text}\n\nFor this reply only: {verdict.guidance}"))

        yield from original_generate(self, active_chat, original_chat, turn, optional_kwargs)

    previous_iter_events = llm.BaseOpenAICompatibleHandler._iter_events

    def _iter_events(self, api_response):  # type: ignore[no-untyped-def]
        events = list(previous_iter_events(self, api_response))
        spoken = "".join(e.text for e in events if isinstance(e, llm.TextDelta))
        blocked = reachy_safety.check_reply(spoken)
        if blocked is None:
            yield from events
            return

        reason, replacement = blocked
        print(f"[Safety] Replaced a reply that {reason}: {spoken.strip()!r}")
        yield llm.TextDelta(text=replacement)
        yield llm.AssistantMessage(content=[llm.AssistantContent(type="output_text", text=replacement)])
        yield from (e for e in events if isinstance(e, llm.Usage))

    llm.BaseOpenAICompatibleHandler._generate = _generate
    llm.BaseOpenAICompatibleHandler._iter_events = _iter_events


def main() -> None:
    if not check_ollama():
        print(
            f"WARNING: could not reach Ollama at {OLLAMA_BASE_URL}. "
            "Start it with `ollama serve` (or open the Ollama app) before continuing.",
            file=sys.stderr,
        )

    ip = lan_ip()
    print("=" * 70)
    print("Starting speech-to-speech realtime server...")
    tts_desc = f"kokoro ({KOKORO_VOICE})" if S2S_TTS == "kokoro" else "qwen3 (torch backend)"
    print(f"STT: parakeet-tdt | LLM: {OLLAMA_MODEL} via Ollama | TTS: {tts_desc}")
    print(
        f"VAD: thresh={VAD_THRESH}, min_silence_ms={VAD_MIN_SILENCE_MS}"
        + (f", max_speech_ms={VAD_MAX_SPEECH_MS}" if VAD_MAX_SPEECH_MS else "")
    )
    print("Replies: at most one question (anything after the first '?' is cut)")
    print("Safety: hard rules checked before the model, every reply checked after (reachy_safety.py)")
    print(f"Listening at ws://{ip}:{WS_PORT}/v1/realtime")
    print()
    print("This is only the voice backend -- it does not talk to Reachy itself.")
    print("It stays idle until a client connects. In a SECOND terminal, run the")
    print("bridge that joins Reachy's mic/speaker to this server:")
    print("    .\\venv-client\\Scripts\\python.exe reachy_s2s_conversation.py")
    print()
    print(f"(Ctrl+C to stop. If it will not exit: taskkill /F /PID {os.getpid()} /T)")
    print("=" * 70)

    # Run the pipeline in this process rather than a subprocess. A subprocess
    # layer swallowed Ctrl+C on Windows: the console signal reached this parent
    # while uvicorn and the pipeline's handler threads kept the child alive.
    # In-process, SIGINT lands directly on the server that has to act on it.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.argv = ["s2s_pipeline", *PIPELINE_ARGS]

    limit_to_one_question()
    install_safety_gate()

    from speech_to_speech.s2s_pipeline import main as pipeline_main

    try:
        pipeline_main()
    except KeyboardInterrupt:
        print("\n[Shutdown] Stopping the speech-to-speech server...")


if __name__ == "__main__":
    main()
