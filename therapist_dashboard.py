import streamlit as st
from datetime import datetime, timedelta, timezone
import html
import os
import tempfile
from pathlib import Path
import numpy as np
import requests

from lesson_planner_v3 import generate_lesson_plan_from_transcript
from supabase import create_client, Client


# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Reachy Mini", layout="centered")


# ── Supabase client ───────────────────────────────────────────
#  One client per browser session. The client carries the signed-in user's
#  token, so a single cached client would let the latest login on this server
#  replace everyone else's — and with it, whose rows RLS hands back.
def get_supabase() -> Client:
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(
            st.secrets["supabase"]["url"],
            st.secrets["supabase"]["anon_key"],
        )
    return st.session_state.supabase_client


supabase = get_supabase()


# ══════════════════════════════════════════════════════════════
#  LOCAL PARAKEET MODEL
# ══════════════════════════════════════════════════════════════
#  Same model the live Reachy pipeline uses for STT, so dashboard transcripts
#  and session transcripts come out of the same recogniser.
PARAKEET_MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v3"
PARAKEET_SAMPLE_RATE = 16000

#  Parakeet runs self-attention over the whole clip at once, so a long recap
#  would use far more memory than it needs to. Feed it in windows instead.
TRANSCRIBE_WINDOW_SECONDS = 30.0
TRANSCRIBE_BOUNDARY_SEARCH_SECONDS = 3.0


@st.cache_resource
def get_parakeet_model():
    import torch
    from nano_parakeet import from_pretrained

    device = "cuda" if torch.cuda.is_available() else "cpu"
    return from_pretrained(model_name=PARAKEET_MODEL_NAME, device=device)


# ══════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════
def login_screen():
    st.markdown("""
    <div style="max-width:380px;margin:80px auto 0;text-align:center;">
        <div style="font-size:2.4rem;margin-bottom:10px;">🤖</div>
        <h2 style="margin-bottom:4px;font-family:'Lora',Georgia,serif;font-size:1.7rem;">Reachy Mini</h2>
        <p style="color:#78716C;font-size:0.88rem;margin-bottom:32px;font-family:system-ui,sans-serif;">
            Therapist Dashboard — please log in
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="therapist@clinic.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

    if submitted:
        try:
            resp = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state.user = resp.user
            st.session_state.access_token = resp.session.access_token
            st.rerun()
        except Exception:
            st.error("Incorrect email or password.")


def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


if "user" not in st.session_state:
    login_screen()
    st.stop()

USER_ID = st.session_state.user.id


# ══════════════════════════════════════════════════════════════
#  CLIENT DISPLAY
# ══════════════════════════════════════════════════════════════
#  Handed out to new clients in turn. The colour is stored with the client so
#  the parent portal shows each child in the same colour.
CLIENT_COLORS = [
    "#FF8C69", "#6B9FD4", "#72C472", "#B48EDB",
    "#E6A23C", "#4FB3BF", "#E57A9B", "#8D99AE",
]
CARDS_PER_ROW = 3


def initials_for(name):
    words = name.split()
    if len(words) > 1:
        return (words[0][0] + words[1][0]).upper()
    # Short participant codes such as "P07" read better whole.
    if len(name) <= 3 and any(ch.isdigit() for ch in name):
        return name.upper()
    return name[:2].upper()


def client_from_row(row):
    return {
        "name": row["client_name"],
        "age": row.get("age"),
        "initials": initials_for(row["client_name"]),
        "color": row.get("color") or "#A8A29E",
        "archived": row.get("archived_at") is not None,
    }


def age_label(client):
    return f"Age {client['age']}" if client.get("age") else "Age not recorded"


def next_client_color(clients):
    in_use = {c["color"] for c in clients if not c["archived"]}
    for color in CLIENT_COLORS:
        if color not in in_use:
            return color
    return CLIENT_COLORS[len(clients) % len(CLIENT_COLORS)]


def error_text(exc):
    # PostgREST errors carry the database's message (including the ones raised
    # by the link/delete functions) on .message; str() adds JSON noise.
    return getattr(exc, "message", None) or str(exc)


def flash(message):
    # st.success() just before st.rerun() is never seen, so confirmations are
    # held over and shown on the next run instead.
    st.session_state.flash = message


def show_flash():
    message = st.session_state.pop("flash", None)
    if message:
        st.success(message)


TEAL = "#0D9488"
TEAL_DARK = "#0F766E"
RED = "#DC2626"
RED_DARK = "#B91C1C"


# ══════════════════════════════════════════════════════════════
#  DATABASE HELPERS
# ══════════════════════════════════════════════════════════════
def db_load_clients():
    rows = (
        supabase.table("clients")
        .select("*")
        .eq("therapist_id", USER_ID)
        .order("created_at")
        .execute()
        .data
    )
    return [client_from_row(row) for row in rows]


def db_add_client(client_name, age, color):
    return (
        supabase.table("clients")
        .insert(
            {
                "therapist_id": USER_ID,
                "client_name": client_name,
                "age": age,
                "color": color,
            }
        )
        .execute()
    )


def db_update_client(client_name, fields):
    return (
        supabase.table("clients")
        .update(fields)
        .eq("therapist_id", USER_ID)
        .eq("client_name", client_name)
        .execute()
    )


def db_set_client_archived(client_name, archived):
    archived_at = datetime.now(timezone.utc).isoformat() if archived else None
    return db_update_client(client_name, {"archived_at": archived_at})


def db_delete_client_permanently(client_name):
    # Storage first: once the rows are gone nothing records where the audio
    # is, and a withdrawn participant's recordings must not be left behind.
    audio_paths = [
        row["audio_path"]
        for row in db_load_daily_recap_sessions(client_name)
        if row.get("audio_path")
    ]
    if audio_paths:
        supabase.storage.from_("daily-recap-audio").remove(audio_paths)

    return supabase.rpc(
        "delete_client_permanently", {"p_client_name": client_name}
    ).execute()


def db_load_parent_links(client_name):
    return (
        supabase.table("parent_accounts")
        .select("id, parent_email")
        .eq("therapist_id", USER_ID)
        .eq("client_name", client_name)
        .order("parent_email")
        .execute()
        .data
    )


def db_link_parent(client_name, parent_email):
    return supabase.rpc(
        "link_parent_to_client",
        {"p_client_name": client_name, "p_parent_email": parent_email},
    ).execute()


def db_unlink_parent(link_id):
    return (
        supabase.table("parent_accounts")
        .delete()
        .eq("id", link_id)
        .eq("therapist_id", USER_ID)
        .execute()
    )


def db_load_safety_events(client_name):
    return (
        supabase.table("safety_events")
        .select("*")
        .eq("therapist_id", USER_ID)
        .eq("client_name", client_name)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def db_load_parent_feedback(client_name):
    return (
        supabase.table("parent_feedback")
        .select("id, parent_id, timestamp, feedback_text")
        .eq("therapist_id", USER_ID)
        .eq("client_name", client_name)
        .order("id", desc=True)
        .execute()
        .data
    )


def db_load_parent_emails(client_name):
    # parent_id -> email for the parents linked to this client, to say who
    # wrote each piece of feedback. A parent since unlinked has no entry.
    rows = (
        supabase.table("parent_accounts")
        .select("parent_id, parent_email")
        .eq("therapist_id", USER_ID)
        .eq("client_name", client_name)
        .execute()
        .data
    )
    return {row["parent_id"]: row["parent_email"] for row in rows}


def db_load_conversation_logs(client_name):
    # "*" rather than naming session_id/turn_index, so the tab still loads
    # before conversation_logs_sessions.sql has added them.
    return (
        supabase.table("conversation_logs")
        .select("*")
        .eq("therapist_id", USER_ID)
        .eq("client_name", client_name)
        .execute()
        .data
    )


def db_set_safety_event_reviewed(event_id, reviewed):
    reviewed_at = datetime.now(timezone.utc).isoformat() if reviewed else None
    return (
        supabase.table("safety_events")
        .update({"reviewed_at": reviewed_at})
        .eq("id", event_id)
        .eq("therapist_id", USER_ID)
        .execute()
    )


def db_load_profiles():
    rows = (
        supabase.table("client_profiles")
        .select("*")
        .eq("therapist_id", USER_ID)
        .execute()
        .data
    )
    return {row["client_name"]: row["profile_text"] for row in rows}


def db_save_profile(client_name, text):
    return (
        supabase.table("client_profiles")
        .upsert(
            {
                "therapist_id": USER_ID,
                "client_name": client_name,
                "profile_text": text,
            },
            on_conflict="therapist_id,client_name",
        )
        .execute()
    )


def db_load_notes():
    rows = (
        supabase.table("session_notes")
        .select("*")
        .eq("therapist_id", USER_ID)
        .order("id")
        .execute()
        .data
    )
    result = {}
    for row in rows:
        result.setdefault(row["client_name"], []).append(
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "text": row["note_text"],
            }
        )
    return result


def db_add_note(client_name, timestamp, text):
    return (
        supabase.table("session_notes")
        .insert(
            {
                "therapist_id": USER_ID,
                "client_name": client_name,
                "timestamp": timestamp,
                "note_text": text,
            }
        )
        .execute()
    )


def db_delete_note(note_id):
    return (
        supabase.table("session_notes")
        .delete()
        .eq("id", note_id)
        .eq("therapist_id", USER_ID)
        .execute()
    )


def db_add_daily_recap_session(
    client_name, audio_path, original_filename, transcript=None, lesson_plan=None
):
    return (
        supabase.table("daily_recap_sessions")
        .insert(
            {
                "therapist_id": USER_ID,
                "client_name": client_name,
                "audio_path": audio_path,
                "original_filename": original_filename,
                "transcript": transcript,
                "lesson_plan": lesson_plan,
            }
        )
        .execute()
    )


def db_load_daily_recap_sessions(client_name):
    return (
        supabase.table("daily_recap_sessions")
        .select("*")
        .eq("therapist_id", USER_ID)
        .eq("client_name", client_name)
        .order("uploaded_at", desc=True)
        .execute()
        .data
    )


def db_update_daily_recap_transcript(session_id, transcript_text):
    return (
        supabase.table("daily_recap_sessions")
        .update({"transcript": transcript_text})
        .eq("id", session_id)
        .eq("therapist_id", USER_ID)
        .execute()
    )


def db_update_daily_recap_lesson_plan(session_id, lesson_plan_text):
    return (
        supabase.table("daily_recap_sessions")
        .update({"lesson_plan": lesson_plan_text})
        .eq("id", session_id)
        .eq("therapist_id", USER_ID)
        .execute()
    )


# ══════════════════════════════════════════════════════════════
#  STORAGE + TRANSCRIPTION HELPERS
# ══════════════════════════════════════════════════════════════
def normalize_audio_content_type(uploaded_audio):
    filename = uploaded_audio.name.lower()

    if filename.endswith(".m4a"):
        return "audio/mp4"
    if filename.endswith(".wav"):
        return "audio/wav"
    if filename.endswith(".mp3"):
        return "audio/mpeg"
    if filename.endswith(".mpeg") or filename.endswith(".mpg"):
        return "audio/mpeg"

    return uploaded_audio.type or "audio/mpeg"


def upload_daily_recap_audio(file_bytes, filename, content_type):
    bucket = "daily-recap-audio"
    safe_name = filename.replace(" ", "_")
    storage_path = f"{USER_ID}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"

    supabase.storage.from_(bucket).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )
    return storage_path


def get_audio_signed_url(storage_path, expires_in=3600):
    try:
        res = supabase.storage.from_("daily-recap-audio").create_signed_url(
            storage_path, expires_in
        )
        return res.get("signedURL") or res.get("signed_url") or ""
    except Exception:
        return ""


def decode_audio_to_mono_16k(audio_path):
    """Decode any uploaded format to the 16 kHz mono float32 Parakeet expects."""
    try:
        return _decode_with_pyav(audio_path)
    except Exception:
        # PyAV covers m4a/mp4; soundfile is the fallback for wav/flac/ogg/mp3.
        return _decode_with_soundfile(audio_path)


def _decode_with_pyav(audio_path):
    import av
    from av.audio.resampler import AudioResampler

    resampler = AudioResampler(format="flt", layout="mono", rate=PARAKEET_SAMPLE_RATE)
    blocks = []

    with av.open(audio_path) as container:
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                blocks.append(resampled.to_ndarray().reshape(-1))
        for resampled in resampler.resample(None):
            blocks.append(resampled.to_ndarray().reshape(-1))

    if not blocks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(blocks).astype(np.float32)


def _decode_with_soundfile(audio_path):
    import soundfile as sf
    from math import gcd
    from scipy.signal import resample_poly

    audio, sample_rate = sf.read(audio_path, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)

    if sample_rate != PARAKEET_SAMPLE_RATE:
        divisor = gcd(int(sample_rate), PARAKEET_SAMPLE_RATE)
        audio = resample_poly(
            audio,
            PARAKEET_SAMPLE_RATE // divisor,
            int(sample_rate) // divisor,
        )

    return audio.astype(np.float32)


def split_audio_for_transcription(audio):
    """Cut audio into windows, breaking at the quietest point near each boundary
    so a word is never split across two windows."""
    window = int(TRANSCRIBE_WINDOW_SECONDS * PARAKEET_SAMPLE_RATE)
    if len(audio) <= window:
        return [audio] if len(audio) else []

    search = int(TRANSCRIBE_BOUNDARY_SEARCH_SECONDS * PARAKEET_SAMPLE_RATE)
    frame = PARAKEET_SAMPLE_RATE // 100  # 10 ms
    chunks = []
    start = 0

    while start < len(audio):
        end = start + window
        if end >= len(audio):
            chunks.append(audio[start:])
            break

        low = max(start + frame, end - search)
        high = min(len(audio) - frame, end + search)
        if high > low:
            region = audio[low:high]
            frame_count = len(region) // frame
            if frame_count:
                energies = (
                    np.abs(region[: frame_count * frame])
                    .reshape(frame_count, frame)
                    .mean(axis=1)
                )
                end = low + int(np.argmin(energies)) * frame

        chunks.append(audio[start:end])
        start = end

    return [chunk for chunk in chunks if len(chunk)]


def transcribe_audio_from_signed_url(
    audio_url, original_filename, progress_callback=None
):
    model = get_parakeet_model()
    suffix = Path(original_filename).suffix or ".mp3"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        response = requests.get(audio_url, timeout=120)
        response.raise_for_status()
        tmp.write(response.content)
        temp_path = tmp.name

    try:
        audio = decode_audio_to_mono_16k(temp_path)
        if not len(audio):
            return ""

        chunks = split_audio_for_transcription(audio)
        pieces = []

        for index, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(index, len(chunks))
            text = str(model.transcribe(chunk)).strip()
            if text:
                pieces.append(text)

        if progress_callback:
            progress_callback(len(chunks), len(chunks))

        return " ".join(pieces).strip()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ══════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════
if "data_loaded" not in st.session_state:
    st.session_state.client_profiles = db_load_profiles()
    st.session_state.session_notes = db_load_notes()
    st.session_state.selected_client = None
    st.session_state.data_loaded = True

if "selected_client" not in st.session_state:
    st.session_state.selected_client = None


# ══════════════════════════════════════════════════════════════
#  STYLES
# ══════════════════════════════════════════════════════════════
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;700&display=swap');

/* ───────────── GLOBAL ───────────── */
html, body {{
    background-color: #FFFFFF !important;
    font-family: 'Lora', Georgia, serif;
    color: #1C1917;
}}

.stApp, .stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"],
.main .block-container {{
    background-color: #FFFFFF !important;
    color: #1C1917;
}}

.block-container {{
    padding-top: 0 !important;
    max-width: 820px;
}}

#MainMenu, footer, header {{
    visibility: hidden;
}}

.main .block-container p,
.main .block-container label {{
    color: #1C1917;
}}

/* ───────────── NAV BAR ───────────── */
.nav-bar {{
    background: #1C1917;
    padding: 16px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -1rem 0 -1rem;
    position: sticky;
    top: 0;
    z-index: 100;
}}

.nav-bar * {{
    color: #FAFAF9 !important;
}}

.nav-title {{
    color: #FAFAF9 !important;
    font-weight: 700;
    font-size: 1.05rem;
}}

.nav-sub {{
    color: #A8A29E !important;
    font-size: 0.72rem;
    text-transform: uppercase;
    font-family: system-ui, sans-serif;
}}

.nav-date {{
    background: #292524;
    border-radius: 20px;
    padding: 6px 14px;
    color: #78716C !important;
    font-size: 0.78rem;
    font-family: system-ui, sans-serif;
}}

.nav-user {{
    color: #A8A29E !important;
    font-size: 0.75rem;
    font-family: system-ui, sans-serif;
}}

/* ───────────── CLIENT CARDS ───────────── */
.client-card {{
    background: white;
    border: 2px solid #E7E5E4;
    border-radius: 16px;
    padding: 20px 16px;
    text-align: center;
    margin-bottom: 6px;
}}

.client-card.selected {{
    border-color: var(--c);
    background: color-mix(in srgb, var(--c) 8%, white);
}}

.client-avatar {{
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 10px;
    font-weight: 800;
    font-size: 0.9rem;
    font-family: system-ui, sans-serif;
}}

.client-name {{
    font-weight: 700;
    font-size: 1rem;
    color: #1C1917 !important;
    margin-bottom: 2px;
}}

.client-age {{
    color: #78716C !important;
    font-size: 0.78rem;
    font-family: system-ui, sans-serif;
}}

.client-badge {{
    display: inline-block;
    margin-top: 10px;
    color: white !important;
    border-radius: 99px;
    font-size: 0.7rem;
    padding: 2px 10px;
    font-weight: 700;
    font-family: system-ui, sans-serif;
}}

/* ───────────── SECTION HEADERS ───────────── */
.step-label {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
    margin-top: 16px;
}}

.step-num {{
    font-size: 0.7rem;
    font-weight: 800;
    color: #A8A29E !important;
    background: #E7E5E4;
    border-radius: 6px;
    padding: 3px 8px;
    font-family: system-ui, sans-serif;
}}

.step-text {{
    font-size: 1.05rem;
    font-weight: 700;
    color: #1C1917 !important;
}}

.step-line {{
    flex: 1;
    height: 1px;
    background: #E7E5E4;
}}

/* ───────────── INFO BOX ───────────── */
.info-box {{
    background: #F0FDFA;
    border: 1px solid #99F6E4;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 20px;
    font-family: system-ui, sans-serif;
    font-size: 0.83rem;
    color: #134E4A !important;
}}

.info-box * {{
    color: #134E4A !important;
}}

.danger-box {{
    background: #FEF2F2;
    border: 1px solid #FECACA;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 14px;
    font-family: system-ui, sans-serif;
    font-size: 0.83rem;
    color: #7F1D1D !important;
}}

.danger-box * {{
    color: #7F1D1D !important;
}}

.removed-client {{
    font-family: system-ui, sans-serif;
    font-size: 0.9rem;
    padding-top: 8px;
}}

.removed-client span {{
    color: #78716C !important;
    font-size: 0.8rem;
}}

/* ───────────── NOTES ───────────── */
.note-entry {{
    background: white;
    border: 1px solid #E7E5E4;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 8px;
}}

.note-entry-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}}

.note-entry-date {{
    font-size: 0.72rem;
    font-weight: 700;
    color: #0D9488 !important;
    font-family: system-ui, sans-serif;
    background: #F0FDFA;
    border: 1px solid #99F6E4;
    border-radius: 99px;
    padding: 2px 10px;
}}

.note-entry-text {{
    font-size: 0.88rem;
    color: #1C1917 !important;
    line-height: 1.65;
    white-space: pre-wrap;
    font-family: 'Lora', Georgia, serif;
}}

/* ───────────── BUTTONS ───────────── */
/* Streamlit puts regular buttons, form submit buttons and download buttons in
   three different containers. Anything left unstyled keeps the browser theme's
   own colours, which on this hard-coded white page means a white button with
   white or near-invisible text — so every variant is listed here. */
.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stBaseButton-primaryFormSubmit"] {{
    background-color: {TEAL} !important;
    color: #FFFFFF !important;
    border: 1px solid {TEAL} !important;
    border-radius: 10px !important;
    font-family: system-ui, sans-serif !important;
    font-weight: 600 !important;
}}

.stButton > button:hover,
.stButton > button:focus,
.stButton > button:active,
.stFormSubmitButton > button:hover,
.stFormSubmitButton > button:focus,
.stFormSubmitButton > button:active,
.stDownloadButton > button:hover,
.stDownloadButton > button:focus,
.stDownloadButton > button:active {{
    background-color: {TEAL_DARK} !important;
    border-color: {TEAL_DARK} !important;
    color: #FFFFFF !important;
}}

/* Labels render inside a <p>, which the global paragraph colour would
   otherwise darken to near-black on the teal fill. */
.stButton > button *,
.stFormSubmitButton > button *,
.stDownloadButton > button *,
.stLinkButton a * {{
    color: inherit !important;
}}

/* Link buttons are <a> elements in their own container — styled as the quiet
   secondary action next to the teal primary buttons. */
.stLinkButton a,
[data-testid="stBaseLinkButton-secondary"],
[data-testid="stBaseLinkButton-primary"] {{
    background-color: #FFFFFF !important;
    color: {TEAL} !important;
    border: 1px solid {TEAL} !important;
    border-radius: 10px !important;
    font-family: system-ui, sans-serif !important;
    font-weight: 600 !important;
    text-decoration: none !important;
}}

.stLinkButton a:hover,
.stLinkButton a:focus,
[data-testid="stBaseLinkButton-secondary"]:hover,
[data-testid="stBaseLinkButton-primary"]:hover {{
    background-color: #F0FDFA !important;
    color: {TEAL_DARK} !important;
    border-color: {TEAL_DARK} !important;
}}

/* A markdown <div> wrapper does not enclose the widget rendered after it, so
   these two are targeted by their widget key instead. */
.st-key-logout_btn button {{
    background-color: #292524 !important;
    border-color: #292524 !important;
    color: #FAFAF9 !important;
    font-size: 0.75rem !important;
    padding: 4px 12px !important;
}}

.st-key-logout_btn button:hover,
.st-key-logout_btn button:focus {{
    background-color: #1C1917 !important;
    border-color: #1C1917 !important;
    color: #FFFFFF !important;
}}

[class*="st-key-delete_note_"] button,
[class*="st-key-delete_client_"] button,
[class*="st-key-archive_client_"] button,
[class*="st-key-unlink_parent_"] button {{
    background-color: #FFFFFF !important;
    color: {RED} !important;
    border: 1px solid #FECACA !important;
    font-size: 0.75rem !important;
}}

[class*="st-key-delete_note_"] button:hover,
[class*="st-key-delete_note_"] button:focus,
[class*="st-key-delete_client_"] button:hover,
[class*="st-key-delete_client_"] button:focus,
[class*="st-key-archive_client_"] button:hover,
[class*="st-key-archive_client_"] button:focus,
[class*="st-key-unlink_parent_"] button:hover,
[class*="st-key-unlink_parent_"] button:focus {{
    background-color: #FEF2F2 !important;
    color: {RED_DARK} !important;
    border-color: {RED} !important;
}}

/* The one irreversible action gets a solid red fill. */
[class*="st-key-confirm_delete_client_"] button {{
    background-color: {RED} !important;
    border-color: {RED} !important;
    color: #FFFFFF !important;
}}

[class*="st-key-confirm_delete_client_"] button:hover,
[class*="st-key-confirm_delete_client_"] button:focus {{
    background-color: {RED_DARK} !important;
    border-color: {RED_DARK} !important;
    color: #FFFFFF !important;
}}

[class*="st-key-cancel_delete_client_"] button {{
    background-color: #FFFFFF !important;
    color: #1C1917 !important;
    border: 1px solid #D6D3D1 !important;
}}

[class*="st-key-cancel_delete_client_"] button:hover,
[class*="st-key-cancel_delete_client_"] button:focus {{
    background-color: #F5F5F4 !important;
    color: #1C1917 !important;
    border-color: #A8A29E !important;
}}

div[data-testid="column"] .stButton > button {{
    width: 100%;
}}

/* ───────────── TABS ───────────── */
/* Targets the tabs themselves ([role="tab"]); a `button` selector here would
   also catch every button inside the tab panels and grey them all out. */
[data-testid="stTabs"] [role="tab"] {{
    font-family: 'Lora', Georgia, serif !important;
    font-weight: 700;
    font-size: 0.95rem;
    color: #78716C !important;
    background-color: #FAFAF9 !important;
    border: 1px solid #E7E5E4 !important;
    border-radius: 8px !important;
    padding: 6px 14px !important;
}}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: #FAFAF9 !important;
    background-color: #1C1917 !important;
    border-color: #1C1917 !important;
}}

[data-testid="stTabs"] [role="tab"]:hover {{
    background-color: #E7E5E4 !important;
    color: #1C1917 !important;
}}

[data-testid="stTabs"] [role="tab"] * {{
    color: inherit !important;
}}

/* ───────────── SELECTBOX / DROPDOWN ───────────── */
div[data-baseweb="select"] > div {{
    background-color: #1C1917 !important;
    color: #FAFAF9 !important;
    border-color: #292524 !important;
    border-radius: 8px !important;
}}

div[data-baseweb="select"] > div *,
div[data-baseweb="select"] span,
div[data-baseweb="select"] svg,
div[data-baseweb="select"] input {{
    color: #FAFAF9 !important;
    fill: #FAFAF9 !important;
}}

[data-baseweb="popover"],
[data-baseweb="menu"],
ul[role="listbox"] {{
    background-color: #1C1917 !important;
    border: 1px solid #292524 !important;
}}

ul[role="listbox"] li,
[data-baseweb="menu"] [role="option"] {{
    color: #FAFAF9 !important;
    background-color: #1C1917 !important;
}}

ul[role="listbox"] li:hover,
[data-baseweb="menu"] [role="option"]:hover,
[data-baseweb="menu"] [role="option"][aria-selected="true"] {{
    background-color: #292524 !important;
    color: #FAFAF9 !important;
}}

/* ───────────── TEXT INPUTS / TEXT AREAS ───────────── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stNumberInput"] input {{
    background-color: #FAFAF9 !important;
    color: #1C1917 !important;
    border: 1px solid #E7E5E4 !important;
    border-radius: 10px !important;
    font-family: system-ui, sans-serif !important;
}}

div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {{
    color: #A8A29E !important;
}}

div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stNumberInput"] label,
div[data-baseweb="select"] ~ label,
.stSelectbox label {{
    color: #1C1917 !important;
}}

/* ───────────── FILE UPLOADER ───────────── */
[data-testid="stFileUploader"] {{
    background: #FAFAF9;
    border: 1px dashed #D6D3D1;
    border-radius: 12px;
    padding: 8px;
}}

[data-testid="stFileUploader"] label {{
    color: #1C1917 !important;
}}

[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {{
    background-color: #FFFFFF !important;
    border: 1px dashed #D6D3D1 !important;
    border-radius: 10px !important;
}}

[data-testid="stFileUploaderDropzone"] *,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small {{
    color: #1C1917 !important;
}}

[data-testid="stFileUploaderDropzone"] button {{
    background-color: #FFFFFF !important;
    color: {TEAL} !important;
    border: 1px solid {TEAL} !important;
    border-radius: 8px !important;
}}

[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {{
    background: #F5F5F4 !important;
    border-radius: 8px !important;
}}

[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] * {{
    color: #1C1917 !important;
}}

/* ───────────── SPINNER / STATUS / ALERTS ───────────── */
div[data-testid="stStatusWidget"] *,
div[role="status"] *,
div[data-testid="stAlert"] {{
    color: #1C1917 !important;
}}

div[data-testid="stAlert"] * {{
    color: inherit !important;
}}
</style>
""",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════
#  NAV BAR
# ══════════════════════════════════════════════════════════════
today = datetime.now().strftime("%a, %b %d").replace(" 0", " ")
user_email = st.session_state.user.email

nav_left, nav_right = st.columns([6, 1])
with nav_left:
    st.markdown(
        f"""
    <div class="nav-bar">
        <div>
            <div class="nav-title">Reachy Mini</div>
            <div class="nav-sub">
                Therapist Dashboard ·
                <span class="nav-user">{user_email}</span>
            </div>
        </div>
        <div class="nav-date">{today}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with nav_right:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    if st.button("Log out", key="logout_btn"):
        logout()


# ══════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════
def client_card_html(client, badge=None):
    color = client["color"]
    badge_html = (
        f'<div class="client-badge" style="background:{color}">{badge}</div>'
        if badge
        else ""
    )
    selected = " selected" if badge else ""
    return f"""
    <div class="client-card{selected}" style="--c:{color}">
        <div class="client-avatar"
             style="background:{color}28;
                    border:2px solid {color}60;
                    color:{color}">
            {html.escape(client['initials'])}
        </div>
        <div class="client-name">{html.escape(client['name'])}</div>
        <div class="client-age">{age_label(client)}</div>
        {badge_html}
    </div>
    """


def render_client_selection(clients):
    active = [c for c in clients if not c["archived"]]
    removed = [c for c in clients if c["archived"]]

    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">01</span>'
        '<span class="step-text">Select Client</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        "Choose a client to open their dashboard. Inside each client you can upload session audio, generate transcripts, "
        "generate lesson plans, add session notes, edit their profile, and link parents in Settings."
        "</div>",
        unsafe_allow_html=True,
    )

    if not active:
        st.info("No clients yet. Add your first client below.")

    for start in range(0, len(active), CARDS_PER_ROW):
        cols = st.columns(CARDS_PER_ROW)
        for client, col in zip(active[start:start + CARDS_PER_ROW], cols):
            with col:
                st.markdown(client_card_html(client), unsafe_allow_html=True)

                if st.button(
                    f"Open {client['name']}",
                    key=f"open_client_{client['name']}",
                ):
                    st.session_state.selected_client = client["name"]
                    st.rerun()

    render_add_client(clients)
    render_removed_clients(removed)


def render_add_client(clients):
    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">02</span>'
        '<span class="step-text">Add Client</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("add_client_form", clear_on_submit=True):
        name_col, age_col = st.columns([3, 1])
        with name_col:
            name = st.text_input(
                "Name or participant ID",
                placeholder="e.g. Sam or P07",
                max_chars=40,
            )
        with age_col:
            age = st.number_input(
                "Age",
                min_value=1,
                max_value=99,
                value=None,
                step=1,
                placeholder="Optional",
            )
        submitted = st.form_submit_button("Add Client", use_container_width=True)

    if not submitted:
        return

    # This name is what the robot's CLIENT_NAME setting and every other table
    # match on, so stray or doubled spaces are squeezed out up front.
    name = " ".join(name.split())
    existing = {c["name"].lower(): c for c in clients}

    if not name:
        st.warning("Enter a name or participant ID.")
    elif name.lower() in existing:
        match = existing[name.lower()]
        if match["archived"]:
            st.warning(
                f"{match['name']} was removed earlier. Restore them under "
                "Removed Clients below to bring back their data."
            )
        else:
            st.warning(f"{match['name']} is already in your client list.")
    else:
        try:
            db_add_client(
                name,
                int(age) if age is not None else None,
                next_client_color(clients),
            )
        except Exception as e:
            st.error(f"Could not add client: {error_text(e)}")
        else:
            flash(f"Added {name}.")
            st.rerun()


def render_removed_clients(removed):
    if not removed:
        return

    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">03</span>'
        '<span class="step-text">Removed Clients</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        "Removed clients are hidden from your list and from their parents' portal, but all of their data is kept. "
        "Restore a client to pick up where you left off, or delete them permanently if they withdraw from the trial."
        "</div>",
        unsafe_allow_html=True,
    )

    for client in removed:
        cname = client["name"]
        name_col, restore_col, delete_col = st.columns([3, 1.2, 1.8])

        with name_col:
            st.markdown(
                f'<div class="removed-client"><strong>{html.escape(cname)}</strong> '
                f"<span>· {age_label(client)}</span></div>",
                unsafe_allow_html=True,
            )

        with restore_col:
            if st.button(
                "Restore",
                key=f"restore_client_{cname}",
                use_container_width=True,
            ):
                try:
                    db_set_client_archived(cname, False)
                except Exception as e:
                    st.error(f"Could not restore {cname}: {error_text(e)}")
                else:
                    flash(f"{cname} is back in your client list.")
                    st.rerun()

        with delete_col:
            if st.button(
                "Delete permanently",
                key=f"delete_client_{cname}",
                use_container_width=True,
            ):
                st.session_state.pending_delete = cname
                st.rerun()

        if st.session_state.get("pending_delete") == cname:
            render_delete_confirmation(client)


def render_delete_confirmation(client):
    cname = client["name"]

    st.markdown(
        f'<div class="danger-box">Permanently delete <strong>{html.escape(cname)}</strong>? '
        "This erases their profile, session notes, uploaded audio, transcripts, lesson plans, "
        "robot conversation logs, parent feedback, recount choices and parent links. "
        "It cannot be undone.</div>",
        unsafe_allow_html=True,
    )

    typed = st.text_input(
        f'Type "{cname}" to confirm',
        key=f"confirm_delete_input_{cname}",
    )

    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button(
            f"Delete {cname} and all data",
            key=f"confirm_delete_client_{cname}",
            use_container_width=True,
        ):
            if typed.strip() != cname:
                st.error(f'Type "{cname}" exactly to confirm.')
            else:
                try:
                    db_delete_client_permanently(cname)
                except Exception as e:
                    st.error(f"Could not delete {cname}: {error_text(e)}")
                else:
                    st.session_state.pending_delete = None
                    # Notes and profiles are cached for the session; drop the
                    # deleted client's so re-adding the name starts clean.
                    st.session_state.client_profiles = db_load_profiles()
                    st.session_state.session_notes = db_load_notes()
                    flash(f"{cname} and all of their data were deleted.")
                    st.rerun()

    with cancel_col:
        if st.button(
            "Cancel",
            key=f"cancel_delete_client_{cname}",
            use_container_width=True,
        ):
            st.session_state.pending_delete = None
            st.rerun()


def render_upload_audio_tab(client):
    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">AUDIO</span>'
        '<span class="step-text">Upload Audio</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        "Upload a Daily Recap audio file for this client. The file will be stored in Supabase Storage for later transcription and planning."
        "</div>",
        unsafe_allow_html=True,
    )

    uploaded_audio = st.file_uploader(
        "Upload audio file",
        type=["mp3", "wav", "m4a", "mpeg", "mpg"],
        key=f"audio_upload_{client['name']}",
    )

    if uploaded_audio is not None:
        st.audio(uploaded_audio)

        if st.button(
            "Upload Audio",
            use_container_width=True,
            key=f"upload_btn_{client['name']}",
        ):
            try:
                file_bytes = uploaded_audio.getvalue()
                content_type = normalize_audio_content_type(uploaded_audio)

                storage_path = upload_daily_recap_audio(
                    file_bytes=file_bytes,
                    filename=uploaded_audio.name,
                    content_type=content_type,
                )

                db_add_daily_recap_session(
                    client_name=client["name"],
                    audio_path=storage_path,
                    original_filename=uploaded_audio.name,
                    transcript=None,
                    lesson_plan=None,
                )

                st.success("Audio uploaded successfully.")
                st.rerun()

            except Exception as e:
                st.error(f"Audio upload failed: {e}")

    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">FILES</span>'
        '<span class="step-text">Uploaded Audio</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    try:
        uploads = db_load_daily_recap_sessions(client["name"])
    except Exception as e:
        st.error(f"Could not load uploaded audio list: {e}")
        return

    if uploads:
        for row in uploads:
            transcript_status = (
                "Transcript saved" if row.get("transcript") else "No transcript yet"
            )
            lesson_plan_status = (
                "Lesson plan saved" if row.get("lesson_plan") else "No lesson plan yet"
            )

            st.markdown(
                f"""
            <div class="note-entry">
                <div class="note-entry-header">
                    <span class="note-entry-date">🕐 {row.get('uploaded_at', '')}</span>
                </div>
                <div style="font-size:0.84rem;font-family:system-ui,sans-serif;color:#78716C;">
                    <strong>File:</strong> {row.get('original_filename', 'Unknown')}
                </div>
                <div style="font-size:0.84rem;font-family:system-ui,sans-serif;color:#78716C;margin-top:4px;">
                    <strong>Transcript:</strong> {transcript_status}
                </div>
                <div style="font-size:0.84rem;font-family:system-ui,sans-serif;color:#78716C;margin-top:4px;">
                    <strong>Lesson Plan:</strong> {lesson_plan_status}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No uploaded audio files yet for this client.")


def render_generate_transcript_tab(client):
    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">TEXT</span>'
        '<span class="step-text">Generate Transcript</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        "Select one of the client’s uploaded audio files and generate a transcript locally using Parakeet TDT. "
        "You can then generate a future lesson plan from that transcript and save both to Supabase."
        "</div>",
        unsafe_allow_html=True,
    )

    try:
        sessions = db_load_daily_recap_sessions(client["name"])
    except Exception as e:
        st.error(f"Could not load audio files: {e}")
        return

    if not sessions:
        st.info("No uploaded audio files found for this client.")
        return

    options = {
        f"{row.get('original_filename', 'Unknown')} · {row.get('uploaded_at', '')}": row
        for row in sessions
    }

    selected_label = st.selectbox(
        "Select uploaded audio",
        list(options.keys()),
        key=f"select_transcript_audio_{client['name']}",
    )
    selected_row = options[selected_label]

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button(
            "Generate Transcript",
            use_container_width=True,
            key=f"gen_transcript_{client['name']}",
        ):
            try:
                audio_url = get_audio_signed_url(selected_row["audio_path"])
                if not audio_url:
                    st.error("Could not generate signed URL for audio file.")
                else:
                    progress_slot = st.empty()

                    def report_progress(done, total):
                        progress_slot.progress(
                            done / total if total else 1.0,
                            text=f"Transcribing segment {min(done + 1, total)} of {total}...",
                        )

                    try:
                        with st.spinner(
                            "Generating transcript locally with Parakeet..."
                        ):
                            transcript_text = transcribe_audio_from_signed_url(
                                audio_url=audio_url,
                                original_filename=selected_row.get(
                                    "original_filename", "audio.mp3"
                                ),
                                progress_callback=report_progress,
                            )
                    finally:
                        progress_slot.empty()

                    db_update_daily_recap_transcript(
                        selected_row["id"], transcript_text
                    )
                    st.success("Transcript generated and saved.")
                    st.rerun()

            except Exception as e:
                st.error(f"Transcription failed: {e}")

    with col2:
        if selected_row.get("audio_path"):
            audio_url = get_audio_signed_url(selected_row["audio_path"])
            if audio_url:
                st.link_button("Open Audio", audio_url, use_container_width=True)

    try:
        refreshed_sessions = db_load_daily_recap_sessions(client["name"])
        selected_row = next(
            (r for r in refreshed_sessions if r["id"] == selected_row["id"]),
            selected_row,
        )
    except Exception:
        pass

    if selected_row.get("transcript"):
        st.markdown(
            '<div class="step-label" style="margin-top:24px">'
            '<span class="step-num">VIEW</span>'
            '<span class="step-text">Saved Transcript</span>'
            '<span class="step-line"></span>'
            "</div>",
            unsafe_allow_html=True,
        )

        st.text_area(
            "Transcript",
            value=selected_row["transcript"],
            height=320,
            key=f"transcript_view_{selected_row['id']}",
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="step-label" style="margin-top:24px">'
            '<span class="step-num">PLAN</span>'
            '<span class="step-text">Future Lesson Plan</span>'
            '<span class="step-line"></span>'
            "</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "Generate Lesson Plan",
            use_container_width=True,
            key=f"gen_lesson_plan_{selected_row['id']}",
        ):
            try:
                with st.spinner("Generating future lesson plan..."):
                    lesson_plan_text = generate_lesson_plan_from_transcript(
                        selected_row["transcript"]
                    )

                db_update_daily_recap_lesson_plan(
                    selected_row["id"], lesson_plan_text
                )
                st.success("Lesson plan generated and saved.")
                st.rerun()

            except Exception as e:
                st.error(f"Lesson plan generation failed: {e}")

        try:
            refreshed_sessions = db_load_daily_recap_sessions(client["name"])
            selected_row = next(
                (r for r in refreshed_sessions if r["id"] == selected_row["id"]),
                selected_row,
            )
        except Exception:
            pass

        if selected_row.get("lesson_plan"):
            st.text_area(
                "Saved Lesson Plan",
                value=selected_row["lesson_plan"],
                height=320,
                key=f"lesson_plan_view_{selected_row['id']}",
                label_visibility="collapsed",
            )
        else:
            st.info("No lesson plan has been generated for this transcript yet.")
    else:
        st.info("This audio file does not have a transcript yet.")


def render_session_notes_tab(client):
    cname = client["name"]
    notes_list = st.session_state.session_notes.setdefault(cname, [])

    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">NOTES</span>'
        '<span class="step-text">Session Notes</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    new_note = st.text_area(
        "New session note",
        height=160,
        placeholder="Write your session observations here...",
        key=f"session_note_input_{cname}",
        label_visibility="collapsed",
    )

    if st.button(
        "Save Note",
        type="primary",
        use_container_width=True,
        key=f"save_note_{cname}",
    ):
        if new_note.strip():
            timestamp = datetime.now().strftime("%d %b %Y · %I:%M %p")
            db_add_note(cname, timestamp, new_note.strip())
            st.session_state.session_notes = db_load_notes()
            st.rerun()
        else:
            st.warning("Please write something before saving.")

    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">LOG</span>'
        '<span class="step-text">Previous Notes</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if notes_list:
        for entry in reversed(notes_list):
            st.markdown(
                f"""
            <div class="note-entry">
                <div class="note-entry-header">
                    <span class="note-entry-date">🕐 {entry['timestamp']}</span>
                </div>
                <div class="note-entry-text">{entry['text']}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            if st.button(
                "🗑 Delete entry",
                key=f"delete_note_{cname}_{entry['id']}",
            ):
                db_delete_note(entry["id"])
                st.session_state.session_notes = db_load_notes()
                st.rerun()
    else:
        st.info("No session notes yet for this client.")


def render_profile_tab(client):
    cname = client["name"]
    current_profile = st.session_state.client_profiles.get(cname, "")

    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">PROFILE</span>'
        '<span class="step-text">Client Profile</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        "Create or update the client profile here. You can store background information, therapy goals, communication notes, sensory needs, or anything else relevant to sessions."
        "</div>",
        unsafe_allow_html=True,
    )

    profile_text = st.text_area(
        "Client Profile",
        value=current_profile,
        height=420,
        key=f"profile_text_{cname}",
        label_visibility="collapsed",
    )

    if st.button(
        "Save Profile",
        type="primary",
        use_container_width=True,
        key=f"profile_save_{cname}",
    ):
        st.session_state.client_profiles[cname] = profile_text
        db_save_profile(cname, profile_text)
        st.success(f"Profile saved for {cname}.")


SEVERITY_STYLES = {
    # severity: (label, text colour, background, border)
    "critical": ("CRITICAL", "#B91C1C", "#FEF2F2", "#FECACA"),
    "high": ("HIGH", "#C2410C", "#FFF7ED", "#FED7AA"),
    "medium": ("MEDIUM", "#A16207", "#FEFCE8", "#FDE68A"),
}


def format_event_time(created_at):
    try:
        when = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return when.astimezone().strftime("%d %b %Y · %I:%M %p")
    except (AttributeError, ValueError):
        return created_at or ""


def render_safety_events_tab(client, events):
    cname = client["name"]

    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">SAFETY</span>'
        '<span class="step-text">Safety Events</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if events is None:
        st.error(
            "Could not load safety events. Has safety_events.sql been applied "
            "to the database?"
        )
        return

    st.markdown(
        '<div class="info-box">'
        "Each entry is a moment where one of Reachy's safety rules fired during a "
        f"conversation with {html.escape(cname)}, with what the child said. "
        "Critical events (a disclosure of harm, not wanting to be alive, or a "
        "request to keep a secret) need an adult to follow up. Mark an event as "
        "reviewed once it has been followed up."
        "</div>",
        unsafe_allow_html=True,
    )

    if not events:
        st.info("No safety events have been recorded for this client.")
        return

    show_reviewed = st.toggle(
        "Show reviewed events",
        value=False,
        key=f"safety_show_reviewed_{cname}",
    )
    visible = [e for e in events if show_reviewed or not e.get("reviewed_at")]

    if not visible:
        st.success("All safety events for this client have been reviewed.")
        return

    for event in visible:
        label, color, bg, border = SEVERITY_STYLES.get(
            event.get("severity"), SEVERITY_STYLES["medium"]
        )
        reviewed_at = event.get("reviewed_at")
        status = (
            f"Reviewed {format_event_time(reviewed_at)}"
            if reviewed_at
            else "Needs review"
        )
        extras = []
        if event.get("lesson_stopped"):
            extras.append("Lesson stopped")
        extras.append(status)

        reachy_html = ""
        if event.get("reachy_text"):
            reachy_html = (
                '<div style="font-size:0.72rem;font-weight:700;color:#78716C;'
                'font-family:system-ui,sans-serif;margin:10px 0 2px;">'
                "REACHY REPLIED</div>"
                f'<div class="note-entry-text">{html.escape(event["reachy_text"])}</div>'
            )

        # Lines are stripped and blanks dropped: an empty reachy_html would
        # otherwise leave a blank line that ends the HTML block in Markdown.
        card = f"""
        <div class="note-entry" style="border-left:4px solid {color};">
            <div class="note-entry-header">
                <span class="note-entry-date">🕐 {format_event_time(event.get('created_at'))}</span>
                <span style="font-size:0.7rem;font-weight:800;color:{color};background:{bg};border:1px solid {border};border-radius:99px;padding:2px 10px;font-family:system-ui,sans-serif;">{label}</span>
            </div>
            <div style="font-size:0.84rem;font-weight:700;color:#1C1917;font-family:system-ui,sans-serif;">
                {html.escape(event.get('rule_name') or '')}
                <span style="font-weight:500;color:#78716C;">({html.escape(event.get('rule_id') or '')})</span>
            </div>
            <div style="font-size:0.72rem;font-weight:700;color:#78716C;font-family:system-ui,sans-serif;margin:10px 0 2px;">
                {html.escape(cname.upper())} SAID</div>
            <div class="note-entry-text">“{html.escape(event.get('child_text') or '')}”</div>
            {reachy_html}
            <div style="font-size:0.75rem;color:#78716C;font-family:system-ui,sans-serif;margin-top:10px;">
                {" · ".join(extras)}
            </div>
        </div>
        """
        st.markdown(
            "\n".join(line.strip() for line in card.splitlines() if line.strip()),
            unsafe_allow_html=True,
        )

        if reviewed_at:
            if st.button("↩ Mark as not reviewed", key=f"safety_unreview_{event['id']}"):
                db_set_safety_event_reviewed(event["id"], False)
                st.rerun()
        elif st.button("✓ Mark as reviewed", key=f"safety_review_{event['id']}"):
            db_set_safety_event_reviewed(event["id"], True)
            st.rerun()


def render_parent_feedback_tab(client):
    cname = client["name"]

    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">PARENTS</span>'
        '<span class="step-text">Parental Feedback</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    try:
        feedback = db_load_parent_feedback(cname)
    except Exception as e:
        st.error(f"Could not load parental feedback. ({error_text(e)})")
        return

    try:
        emails = db_load_parent_emails(cname)
    except Exception:
        emails = {}

    st.markdown(
        '<div class="info-box">'
        f"Feedback written by {html.escape(cname)}'s parents in the parent "
        "dashboard, newest first. Parents are linked in the Settings tab."
        "</div>",
        unsafe_allow_html=True,
    )

    if not feedback:
        st.info(f"No parental feedback has been submitted for {cname} yet.")
        return

    for entry in feedback:
        author = emails.get(entry.get("parent_id"), "A parent no longer linked")
        card = f"""
        <div class="note-entry">
            <div class="note-entry-header">
                <span class="note-entry-date">🕐 {html.escape(entry.get('timestamp') or '')}</span>
                <span style="font-size:0.75rem;color:#78716C;font-family:system-ui,sans-serif;">{html.escape(author)}</span>
            </div>
            <div class="note-entry-text">{html.escape(entry.get('feedback_text') or '')}</div>
        </div>
        """
        st.markdown(
            "\n".join(line.strip() for line in card.splitlines() if line.strip()),
            unsafe_allow_html=True,
        )


# The robot writes the same format (reachy_s2s_conversation.py, _record).
LOG_TIMESTAMP_FORMAT = "%d %b %Y · %I:%M %p"
# Rows written before conversation_logs_sessions.sql have no session_id. Robot
# runs are often only minutes apart, so for those a gap this long between turns
# is taken as a new session; that is a best guess, not a record.
SESSION_GAP = timedelta(minutes=5)


def parse_log_timestamp(row):
    try:
        return datetime.strptime(row.get("timestamp") or "", LOG_TIMESTAMP_FORMAT)
    except ValueError:
        return None


def group_logs_into_sessions(rows):
    """Split log rows into sessions, newest session first, turns oldest first.

    Rows with a session_id are grouped by it and ordered by turn_index. Older
    rows are grouped by SESSION_GAP; any whose timestamp cannot be parsed are
    kept together as a final group with start None, so nothing is hidden.
    """
    by_id, legacy, undated = {}, [], []
    for row in rows:
        when = parse_log_timestamp(row)
        if row.get("session_id"):
            by_id.setdefault(row["session_id"], []).append((when, row))
        elif when is None:
            undated.append(row)
        else:
            legacy.append((when, row))

    sessions = []
    for turns in by_id.values():
        turns.sort(key=lambda pair: pair[1].get("turn_index") or 0)
        times = [when for when, _ in turns if when is not None]
        sessions.append(
            {
                "start": min(times) if times else None,
                "end": max(times) if times else None,
                "turns": [row for _, row in turns],
                "guessed": False,
            }
        )

    # sort() is stable; within a minute the order is whatever the database gave.
    legacy.sort(key=lambda pair: pair[0])
    current = None
    for when, row in legacy:
        if current and when - current["end"] <= SESSION_GAP:
            current["end"] = when
            current["turns"].append(row)
        else:
            current = {"start": when, "end": when, "turns": [row], "guessed": True}
            sessions.append(current)

    sessions.sort(key=lambda s: s["start"] or datetime.min, reverse=True)
    if undated:
        sessions.append(
            {"start": None, "end": None, "turns": undated, "guessed": True}
        )
    return sessions


def session_title(session):
    turns = len(session["turns"])
    count = f"{turns} turn" + ("" if turns == 1 else "s")
    start, end = session["start"], session["end"]
    if start is None:
        return f"Undated turns · {count}"
    span = start.strftime("%d %b %Y · %I:%M %p")
    if end != start:
        span += " – " + end.strftime("%I:%M %p")
    return f"{span} · {count}"


def render_conversation_logs_tab(client, logs, safety_events):
    cname = client["name"]

    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">LOGS</span>'
        '<span class="step-text">Conversation Logs</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if logs is None:
        st.error(
            "Could not load conversation logs. Has conversation_logs_sessions.sql "
            "been applied to the database?"
        )
        return

    if not logs:
        st.info(
            f"No conversations with Reachy have been recorded for {cname} yet. "
            "If you expected some, check conversation_logs_sessions.sql has been "
            "applied: without it the logs cannot be read."
        )
        return

    st.markdown(
        '<div class="info-box">'
        f"Everything {html.escape(cname)} and Reachy said, grouped by session. "
        "A turn where a safety rule fired is marked 🛡️; see the Safety Events "
        "tab for details."
        "</div>",
        unsafe_allow_html=True,
    )

    flagged = {
        (e.get("child_text") or "").strip() for e in safety_events or []
    } - {""}

    for index, session in enumerate(group_logs_into_sessions(logs)):
        turns = session["turns"]
        has_flag = any((t.get("user_text") or "").strip() in flagged for t in turns)
        title = ("🛡️ " if has_flag else "") + session_title(session)

        with st.expander(title, expanded=index == 0):
            if session["guessed"]:
                st.caption(
                    "Recorded before sessions were tracked: grouped by the time "
                    "between turns, so short sessions close together may be "
                    "merged, and turns in the same minute may be out of order."
                )
            for turn in turns:
                child_text = turn.get("user_text") or ""
                mark = " 🛡️" if child_text.strip() in flagged else ""
                card = f"""
                <div class="note-entry">
                    <div class="note-entry-header">
                        <span class="note-entry-date">🕐 {html.escape(turn.get('timestamp') or '')}</span>
                    </div>
                    <div style="font-size:0.72rem;font-weight:700;color:#78716C;font-family:system-ui,sans-serif;margin-bottom:2px;">
                        {html.escape(cname.upper())}{mark}</div>
                    <div class="note-entry-text">{html.escape(child_text)}</div>
                    <div style="font-size:0.72rem;font-weight:700;color:{TEAL};font-family:system-ui,sans-serif;margin:10px 0 2px;">
                        REACHY</div>
                    <div class="note-entry-text">{html.escape(turn.get('assistant_text') or '')}</div>
                </div>
                """
                st.markdown(
                    "\n".join(line.strip() for line in card.splitlines() if line.strip()),
                    unsafe_allow_html=True,
                )


def render_settings_tab(client):
    cname = client["name"]

    # ── Details ──
    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">DETAILS</span>'
        '<span class="step-text">Client Details</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form(f"details_form_{cname}"):
        age = st.number_input(
            "Age",
            min_value=1,
            max_value=99,
            value=client["age"],
            step=1,
            placeholder="Not recorded",
        )
        if st.form_submit_button("Save Details", use_container_width=True):
            try:
                db_update_client(
                    cname, {"age": int(age) if age is not None else None}
                )
            except Exception as e:
                st.error(f"Could not save details: {error_text(e)}")
            else:
                flash(f"Details saved for {cname}.")
                st.rerun()

    # ── Parent access ──
    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">PARENTS</span>'
        '<span class="step-text">Parent Access</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        f"Link a parent's login so they can follow {html.escape(cname)} in the Parent Portal. "
        "The parent's account must already exist (Supabase Studio → Authentication → Add user). "
        "A parent linked to more than one child can switch between them in the portal."
        "</div>",
        unsafe_allow_html=True,
    )

    try:
        links = db_load_parent_links(cname)
    except Exception as e:
        st.error(f"Could not load linked parents: {error_text(e)}")
        links = []

    for link in links:
        email_col, unlink_col = st.columns([4, 1])
        with email_col:
            st.markdown(
                '<div class="note-entry" style="padding:10px 16px">'
                '<div class="note-entry-text">'
                f"{html.escape(link.get('parent_email') or 'Unknown account')}"
                "</div></div>",
                unsafe_allow_html=True,
            )
        with unlink_col:
            if st.button(
                "Unlink",
                key=f"unlink_parent_{link['id']}",
                use_container_width=True,
            ):
                try:
                    db_unlink_parent(link["id"])
                except Exception as e:
                    st.error(f"Could not unlink parent: {error_text(e)}")
                else:
                    flash(f"Unlinked {link.get('parent_email') or 'parent'} from {cname}.")
                    st.rerun()

    if not links:
        st.info(f"No parents are linked to {cname} yet.")

    with st.form(f"link_parent_form_{cname}", clear_on_submit=True):
        parent_email = st.text_input(
            "Parent's login email",
            placeholder="parent@email.com",
        )
        link_submitted = st.form_submit_button(
            "Link Parent", use_container_width=True
        )

    if link_submitted:
        parent_email = parent_email.strip()
        if "@" not in parent_email:
            st.warning("Enter the email address the parent logs in with.")
        else:
            try:
                db_link_parent(cname, parent_email)
            except Exception as e:
                st.error(error_text(e))
            else:
                flash(f"Linked {parent_email} to {cname}.")
                st.rerun()

    # ── Remove ──
    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">REMOVE</span>'
        '<span class="step-text">Remove Client</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        f"Removing hides {html.escape(cname)} from your client list and from their parents' portal. "
        "Nothing is deleted: you can restore them from the client list, or delete their data "
        "permanently from there if they withdraw."
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button(
        f"Remove {cname}",
        key=f"archive_client_{cname}",
        use_container_width=True,
    ):
        try:
            db_set_client_archived(cname, True)
        except Exception as e:
            st.error(f"Could not remove {cname}: {error_text(e)}")
        else:
            st.session_state.selected_client = None
            flash(f"{cname} was removed. Their data is kept under Removed Clients.")
            st.rerun()


def render_client_dashboard(client):
    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">CLIENT</span>'
        '<span class="step-text">Current Client</span>'
        '<span class="step-line"></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        client_card_html(client, badge="ACTIVE CLIENT"),
        unsafe_allow_html=True,
    )

    back_col1, back_col2 = st.columns([1, 3])
    with back_col1:
        if st.button("← Back", use_container_width=True, key="back_to_selection"):
            st.session_state.selected_client = None
            st.rerun()

    # Loaded up front so the tab label can show how many events need review.
    try:
        safety_events = db_load_safety_events(client["name"])
    except Exception:
        safety_events = None
    unreviewed = sum(1 for e in safety_events or [] if not e.get("reviewed_at"))
    safety_label = "🛡️ Safety Events" + (f" ({unreviewed})" if unreviewed else "")

    try:
        conversation_logs = db_load_conversation_logs(client["name"])
    except Exception:
        conversation_logs = None

    (
        tab_session,
        tab_profile,
        tab_logs,
        tab_feedback,
        tab_safety,
        tab_settings,
    ) = st.tabs(
        [
            "📋 Session",
            "👤 Client Profile",
            "💬 Conversation Logs",
            "👪 Parental Feedback",
            safety_label,
            "⚙️ Settings",
        ]
    )

    with tab_session:
        sub_upload, sub_transcript, sub_notes = st.tabs(
            ["Upload Audio", "Generate Transcript", "Session Notes"]
        )

        with sub_upload:
            render_upload_audio_tab(client)

        with sub_transcript:
            render_generate_transcript_tab(client)

        with sub_notes:
            render_session_notes_tab(client)

    with tab_profile:
        render_profile_tab(client)

    with tab_logs:
        render_conversation_logs_tab(client, conversation_logs, safety_events)

    with tab_feedback:
        render_parent_feedback_tab(client)

    with tab_safety:
        render_safety_events_tab(client, safety_events)

    with tab_settings:
        render_settings_tab(client)


# ══════════════════════════════════════════════════════════════
#  APP ENTRY
# ══════════════════════════════════════════════════════════════
#  The client list is re-read on every run so additions, removals and edits
#  show straight away; selected_client holds just the name.
try:
    clients = db_load_clients()
except Exception as e:
    st.error(
        "Could not load your client list. If the dashboard was just updated, "
        "apply participants_migration.sql to the database first. "
        f"({error_text(e)})"
    )
    st.stop()

selected = next(
    (
        c
        for c in clients
        if not c["archived"] and c["name"] == st.session_state.selected_client
    ),
    None,
)

show_flash()

if selected is None:
    st.session_state.selected_client = None
    render_client_selection(clients)
else:
    render_client_dashboard(selected)