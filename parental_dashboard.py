import streamlit as st
from datetime import datetime
import html
from supabase import create_client, Client

st.set_page_config(page_title="Reachy Mini - Parent Portal", layout="centered")

# ── Supabase client ───────────────────────────────────────────
#  One client per browser session. The client carries the signed-in parent's
#  token, so a single cached client would let the latest login on this server
#  replace everyone else's, and parents would see each other's children.
def get_supabase() -> Client:
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(
            st.secrets["supabase"]["url"],
            st.secrets["supabase"]["anon_key"],
        )
    return st.session_state.supabase_client

supabase = get_supabase()

# ══════════════════════════════════════════════════════════════
#  CHILD DISPLAY
# ══════════════════════════════════════════════════════════════
#  Same rule as the therapist dashboard, so a child's avatar matches on both.
def initials_for(name):
    words = name.split()
    if len(words) > 1:
        return (words[0][0] + words[1][0]).upper()
    if len(name) <= 3 and any(ch.isdigit() for ch in name):
        return name.upper()
    return name[:2].upper()


INK = "#1C1917"
INK_SOFT = "#292524"
INK_MUTED = "#44403C"
TEAL = "#0D9488"
TEAL_DARK = "#0F766E"
RED = "#DC2626"
RED_DARK = "#B91C1C"

# ══════════════════════════════════════════════════════════════
#  GLOBAL STYLES
# ══════════════════════════════════════════════════════════════
#  Injected before the auth gate so the login screen is styled too — otherwise
#  its submit button keeps the browser default and renders white-on-white.
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;700&display=swap');

:root {{
    --primary-color: {INK};
}}

html, body {{
    background-color: #FFFFFF !important;
    font-family: 'Lora', Georgia, serif;
    color: {INK};
}}

.stApp, .stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"],
.main .block-container {{
    background-color: #FFFFFF !important;
    color: {INK};
}}

.block-container {{
    padding-top: 0 !important;
    max-width: 760px;
}}

#MainMenu, footer, header {{
    visibility: hidden;
}}

p, div, span, label {{
    color: {INK};
}}

[data-testid="column"] {{
    background-color: #FFFFFF !important;
}}

/* ───────────── NAV BAR ───────────── */
.nav-bar {{
    background: {INK};
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 14px;
    margin-bottom: 0;
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
    background: {INK_SOFT};
    border-radius: 20px;
    padding: 6px 14px;
    color: #A8A29E !important;
    font-size: 0.78rem;
    font-family: system-ui, sans-serif;
}}

.nav-user {{
    color: #A8A29E !important;
    font-size: 0.75rem;
    font-family: system-ui, sans-serif;
}}

/* ───────────── LOGO MARK ───────────── */
.logo-mark {{
    width: 54px;
    height: 54px;
    border-radius: 16px;
    background: {INK};
    color: #FAFAF9 !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: system-ui, sans-serif;
    font-weight: 800;
    font-size: 1.05rem;
    letter-spacing: 0.04em;
    margin: 0 auto 14px;
}}

/* ───────────── OVERVIEW HEADER ───────────── */
.hero-card {{
    background: #FFFFFF;
    border: 1.5px solid #E7E5E4;
    border-radius: 18px;
    padding: 24px 26px 22px;
    margin-top: 20px;
    margin-bottom: 4px;
}}

.hero-row {{
    display: flex;
    align-items: center;
    gap: 16px;
}}

.hero-avatar {{
    width: 64px;
    height: 64px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-family: system-ui, sans-serif;
    flex-shrink: 0;
}}

.hero-name {{
    font-size: 1.4rem;
    font-weight: 700;
    color: {INK} !important;
}}

.hero-meta {{
    font-size: 0.85rem;
    color: #78716C !important;
    font-family: system-ui, sans-serif;
}}

.hero-badge {{
    margin-left: auto;
    background: {INK};
    color: #FAFAF9 !important;
    border-radius: 99px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 5px 12px;
    font-family: system-ui, sans-serif;
    white-space: nowrap;
}}

.hero-stats {{
    display: flex;
    gap: 10px;
    margin-top: 22px;
    padding-top: 20px;
    border-top: 1px solid #E7E5E4;
}}

.stat {{
    flex: 1;
    background: #FAFAF9;
    border: 1px solid #E7E5E4;
    border-radius: 12px;
    padding: 13px 10px;
    text-align: center;
}}

.stat-num {{
    font-size: 1.5rem;
    font-weight: 800;
    color: {INK} !important;
    font-family: system-ui, sans-serif;
    line-height: 1.1;
}}

.stat-label {{
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #78716C !important;
    font-family: system-ui, sans-serif;
    margin-top: 5px;
}}

.hero-footer {{
    margin-top: 14px;
    font-size: 0.78rem;
    color: #78716C !important;
    font-family: system-ui, sans-serif;
}}

/* ───────────── SECTION HEADERS ───────────── */
.step-label {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
    margin-top: 8px;
}}

.step-num {{
    font-size: 0.7rem;
    font-weight: 800;
    color: #FAFAF9 !important;
    background: {INK};
    border-radius: 6px;
    padding: 3px 8px;
    font-family: system-ui, sans-serif;
}}

.step-text {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {INK} !important;
}}

.step-line {{
    flex: 1;
    height: 1px;
    background: #E7E5E4;
}}

/* ───────────── ENTRIES ───────────── */
.note-entry {{
    background: #FFFFFF;
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
    color: {INK} !important;
    line-height: 1.65;
    white-space: pre-wrap;
    font-family: 'Lora', Georgia, serif;
}}

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

.empty-state {{
    text-align: center;
    padding: 48px 0;
    color: #A8A29E !important;
    font-family: system-ui, sans-serif;
    font-size: 0.88rem;
}}

/* ───────────── BUTTONS ───────────── */
/* Streamlit splits regular buttons, form submit buttons and download buttons
   across three containers, and each has its own test id. A bare `button` rule
   would also repaint the tab strip, so every variant is listed explicitly. */
.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stBaseButton-primaryFormSubmit"] {{
    background-color: {INK} !important;
    color: #FAFAF9 !important;
    border: 1px solid {INK} !important;
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
    background-color: {INK_SOFT} !important;
    border-color: {TEAL} !important;
    color: #FFFFFF !important;
}}

/* Button labels render inside a <p>, which the global paragraph colour would
   otherwise darken to near-black on the dark fill. */
.stButton > button *,
.stFormSubmitButton > button *,
.stDownloadButton > button * {{
    color: inherit !important;
}}

/* A markdown <div> wrapper does not enclose the widget rendered after it, so
   per-button overrides are targeted by their widget key instead. */
[class*="st-key-clear_recount_choices_"] button {{
    background-color: {INK_MUTED} !important;
    border-color: {INK_MUTED} !important;
}}

[class*="st-key-clear_recount_choices_"] button:hover,
[class*="st-key-clear_recount_choices_"] button:focus {{
    background-color: {INK_SOFT} !important;
    border-color: {TEAL} !important;
}}

[class*="st-key-fb_del_"] button {{
    background-color: {INK} !important;
    color: #FCA5A5 !important;
    border-color: {INK_SOFT} !important;
    font-size: 0.75rem !important;
    padding: 4px 14px !important;
}}

[class*="st-key-fb_del_"] button:hover,
[class*="st-key-fb_del_"] button:focus {{
    background-color: {RED_DARK} !important;
    border-color: {RED} !important;
    color: #FFFFFF !important;
}}

div[data-testid="column"] .stButton > button {{
    width: 100%;
}}

/* ───────────── CHILD SWITCHER ───────────── */
.st-key-child_switch {{
    margin-top: 18px;
}}

/* Styled like the tab strip below: muted when idle, ink when chosen. */
[data-variant="segmented_control"] {{
    background-color: #FAFAF9 !important;
    color: #78716C !important;
    border: 1px solid #E7E5E4 !important;
    font-family: system-ui, sans-serif !important;
    font-weight: 600 !important;
}}

[data-variant="segmented_control"]:hover {{
    background-color: #E7E5E4 !important;
    color: {INK} !important;
}}

[data-variant="segmented_control"][aria-checked="true"],
[data-variant="segmented_control"][aria-checked="true"]:hover {{
    background-color: {INK} !important;
    color: #FAFAF9 !important;
    border-color: {INK} !important;
}}

[data-variant="segmented_control"] * {{
    color: inherit !important;
}}

/* ───────────── TABS ───────────── */
[data-testid="stTabs"] {{
    margin-top: 1.6rem;
}}

[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 6px;
}}

[data-testid="stTabs"] [role="tab"] {{
    font-family: 'Lora', Georgia, serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    color: #78716C !important;
    background-color: #FAFAF9 !important;
    border: 1px solid #E7E5E4 !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    white-space: nowrap !important;
    min-width: fit-content !important;
    flex-shrink: 0 !important;
}}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: #FAFAF9 !important;
    background-color: {INK} !important;
    border-color: {INK} !important;
}}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {{
    color: #FAFAF9 !important;
}}

[data-testid="stTabs"] [role="tab"]:hover {{
    background-color: #E7E5E4 !important;
    color: {INK} !important;
}}

/* ───────────── TEXT INPUTS / TEXT AREAS ───────────── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {{
    background-color: #FAFAF9 !important;
    color: {INK} !important;
    border: 1px solid #E7E5E4 !important;
    border-radius: 10px !important;
    font-family: system-ui, sans-serif !important;
}}

div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {{
    color: #A8A29E !important;
}}

div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label {{
    color: {INK} !important;
}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════
def login_screen():
    st.markdown("""
    <div style="max-width:380px;margin:80px auto 0;text-align:center;">
        <div class="logo-mark">RM</div>
        <h2 style="margin-bottom:4px;font-family:'Lora',Georgia,serif;font-size:1.7rem;">Reachy Mini</h2>
        <p style="color:#78716C;font-size:0.88rem;margin-bottom:32px;font-family:system-ui,sans-serif;">
            Parent Portal - please log in
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="parent@email.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

    if submitted:
        try:
            resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
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
    # Left in the URL, ?logout=1 would sign the parent straight back out the
    # moment they next log in.
    st.query_params.clear()
    st.rerun()


if "user" not in st.session_state:
    login_screen()
    st.stop()

USER_ID = st.session_state.user.id

# ══════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════
def db_get_linked_children():
    """Return every child linked to this parent account, sorted by name.

    Children the therapist has removed are left out.
    """
    try:
        links = (
            supabase.table("parent_accounts")
            .select("client_name, therapist_id")
            .eq("parent_id", USER_ID)
            .execute()
            .data
        ) or []
    except Exception:
        return []

    if not links:
        return []

    try:
        rows = (
            supabase.table("clients")
            .select("therapist_id, client_name, age, color, archived_at")
            .in_("client_name", sorted({link["client_name"] for link in links}))
            .execute()
            .data
        ) or []
    except Exception:
        # Details are cosmetic; without them the child still shows, just with
        # a neutral avatar.
        rows = []

    details = {(r["therapist_id"], r["client_name"]): r for r in rows}
    children = []

    for link in links:
        row = details.get((link["therapist_id"], link["client_name"]), {})
        if row.get("archived_at"):
            continue
        name = link["client_name"]
        children.append({
            "key": f"{link['therapist_id']}_{name}",
            "name": name,
            "therapist_id": link["therapist_id"],
            "age": row.get("age"),
            "initials": initials_for(name),
            "color": row.get("color") or "#A8A29E",
        })

    return sorted(children, key=lambda c: c["name"].lower())


def db_load_session_notes(therapist_id, client_name):
    try:
        rows = (
            supabase.table("session_notes")
            .select("*")
            .eq("therapist_id", therapist_id)
            .eq("client_name", client_name)
            .order("id")
            .execute()
            .data
        )
        return [
            {"id": r["id"], "timestamp": r["timestamp"], "text": r["note_text"]}
            for r in rows
        ]
    except Exception:
        return []


def db_load_parent_feedback(therapist_id, client_name):
    try:
        rows = (
            supabase.table("parent_feedback")
            .select("*")
            .eq("parent_id", USER_ID)
            .eq("therapist_id", therapist_id)
            .eq("client_name", client_name)
            .order("id")
            .execute()
            .data
        )
        return [
            {"id": r["id"], "timestamp": r["timestamp"], "text": r["feedback_text"]}
            for r in rows
        ]
    except Exception:
        return []


def db_add_parent_feedback(therapist_id, client_name, timestamp, text):
    supabase.table("parent_feedback").insert({
        "parent_id": USER_ID,
        "therapist_id": therapist_id,
        "client_name": client_name,
        "timestamp": timestamp,
        "feedback_text": text,
    }).execute()


def db_delete_parent_feedback(feedback_id):
    supabase.table("parent_feedback").delete().eq("id", feedback_id).execute()


def db_load_recount_prompts(therapist_id, client_name):
    try:
        rows = (
            supabase.table("recount_event_prompts")
            .select("*")
            .eq("parent_id", USER_ID)
            .eq("therapist_id", therapist_id)
            .eq("client_name", client_name)
            .order("event_order")
            .execute()
            .data
        )
        return rows or []
    except Exception:
        return []


def db_save_recount_prompts(therapist_id, client_name, titles):
    clean_titles = [t.strip() for t in titles if t.strip()]

    try:
        (
            supabase.table("recount_event_prompts")
            .delete()
            .eq("parent_id", USER_ID)
            .eq("therapist_id", therapist_id)
            .eq("client_name", client_name)
            .execute()
        )

        if clean_titles:
            payload = []
            for i, title in enumerate(clean_titles, start=1):
                payload.append({
                    "parent_id": USER_ID,
                    "therapist_id": therapist_id,
                    "client_name": client_name,
                    "title": title,
                    "event_order": i,
                })

            supabase.table("recount_event_prompts").insert(payload).execute()

        return True
    except Exception as e:
        st.error(f"Could not save recount choices: {e}")
        return False


def db_delete_recount_prompts(therapist_id, client_name):
    try:
        (
            supabase.table("recount_event_prompts")
            .delete()
            .eq("parent_id", USER_ID)
            .eq("therapist_id", therapist_id)
            .eq("client_name", client_name)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Could not clear recount choices: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  LINKED CHILDREN
# ══════════════════════════════════════════════════════════════
#  Re-read on every run, so a child the therapist links or removes appears or
#  disappears without the parent having to log in again.
children = db_get_linked_children()

# ══════════════════════════════════════════════════════════════
#  NAV BAR  (rendered as a single full-width block — no columns)
# ══════════════════════════════════════════════════════════════
today = datetime.now().strftime("%a, %b %d").replace(" 0", " ")
user_email = st.session_state.user.email

# Handle logout via query param (avoids any Streamlit widget outside tabs)
if st.query_params.get("logout") == "1":
    logout()

st.markdown(f"""
<div class="nav-bar">
    <div>
        <div class="nav-title">Reachy Mini</div>
        <div class="nav-sub">
            Parent Portal &middot;
            <span class="nav-user">{user_email}</span>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
        <div class="nav-date">{today}</div>
        <a href="?logout=1" style="background:{INK_SOFT};color:#FAFAF9;font-size:0.75rem;padding:6px 14px;border-radius:10px;text-decoration:none;font-family:system-ui,sans-serif;font-weight:600;">Log out</a>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Not linked yet ─────────────────────────────────────────────
if not children:
    st.markdown("""
    <div style="text-align:center;padding:80px 0;font-family:system-ui,sans-serif;color:#78716C;">
        <div class="logo-mark">RM</div>
        <div style="font-weight:700;font-size:1rem;margin-bottom:8px;color:#1C1917;">Account not yet linked</div>
        <div style="font-size:0.88rem;max-width:360px;margin:0 auto;line-height:1.6;">
            Your account has not been linked to a child's therapy record yet.
            Please contact your therapist to complete the setup.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Child switcher ─────────────────────────────────────────────
#  Only shown to parents linked to more than one child. Everything below it
#  (header, notes, recount choices, feedback) follows the chosen child, and
#  each child's inputs are keyed separately so nothing typed for one child
#  carries over to another.
children_by_key = {c["key"]: c for c in children}

if st.session_state.get("child_switch") not in children_by_key:
    st.session_state.pop("child_switch", None)

if len(children) > 1:
    active_key = st.segmented_control(
        "Choose a child",
        options=list(children_by_key),
        format_func=lambda k: children_by_key[k]["name"],
        default=children[0]["key"],
        required=True,
        key="child_switch",
    )
else:
    active_key = children[0]["key"]

child = children_by_key[active_key]
child_key = child["key"]

# ── Load data for the chosen child ─────────────────────────────
client_name = child["name"]
therapist_id = child["therapist_id"]

notes = db_load_session_notes(therapist_id, client_name)
recount_prompts = db_load_recount_prompts(therapist_id, client_name)
feedback_list = db_load_parent_feedback(therapist_id, client_name)

# ══════════════════════════════════════════════════════════════
#  OVERVIEW HEADER
# ══════════════════════════════════════════════════════════════
#  Sits above the tabs rather than inside a Home tab of its own, so the child's
#  details and the at-a-glance counts stay visible whichever tab is open.
hero_color = child["color"]
hero_bg = hero_color + "22"
hero_age = f"Age {child['age']}" if child["age"] else "Age not recorded"
last_note = notes[-1]["timestamp"] if notes else None
last_activity = (
    f"Last therapist note: {last_note}" if last_note else "No therapist notes yet."
)

st.markdown(
    f"""
    <div class="hero-card">
        <div class="hero-row">
            <div class="hero-avatar" style="background:{hero_bg};color:{hero_color};">
                {html.escape(child['initials'])}
            </div>
            <div>
                <div class="hero-name">{html.escape(client_name)}</div>
                <div class="hero-meta">{hero_age}</div>
            </div>
            <div class="hero-badge">LINKED</div>
        </div>
        <div class="hero-stats">
            <div class="stat">
                <div class="stat-num">{len(notes)}</div>
                <div class="stat-label">Therapist notes</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len(recount_prompts)}<span style="font-size:0.9rem;color:#A8A29E;">/5</span></div>
                <div class="stat-label">Recount choices</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len(feedback_list)}</div>
                <div class="stat-label">Your feedback</div>
            </div>
        </div>
        <div class="hero-footer">{last_activity}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════
tab_notes, tab_recount, tab_feedback = st.tabs([
    "Therapist Notes",
    "Recount Choices",
    "Reachy Feedback",
])

# ══════════════════════════════════════════════════════════════
#  TAB 1 — THERAPIST NOTES
# ══════════════════════════════════════════════════════════════
with tab_notes:
    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">LOG</span>'
        '<span class="step-text">Therapist Notes</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        'These notes are written by your therapist after each session. '
        'They are read-only.'
        '</div>',
        unsafe_allow_html=True,
    )

    if notes:
        for entry in reversed(notes):
            st.markdown(f"""
            <div class="note-entry">
                <div class="note-entry-header">
                    <span class="note-entry-date">{entry['timestamp']}</span>
                </div>
                <div class="note-entry-text">{entry['text']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="empty-state">No therapist notes yet.</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════
#  TAB 2 — RECOUNT CHOICES
# ══════════════════════════════════════════════════════════════
with tab_recount:
    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">SETUP</span>'
        '<span class="step-text">Recount Choices</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        'Add up to 5 short story titles based on events provided by the teacher. '
        'These will be used by Reachy as prompt choices during the recount task.'
        '</div>',
        unsafe_allow_html=True,
    )

    existing_titles = ["", "", "", "", ""]
    for row in recount_prompts:
        order = row.get("event_order", 0)
        title = row.get("title", "")
        if 1 <= order <= 5:
            existing_titles[order - 1] = title

    # The inputs below have no keys of their own on purpose: inside a form
    # keyed per child they are already separate per child, and without a key
    # they reset to the saved titles after Save or Clear.
    with st.form(f"recount_choices_form_{child_key}"):
        title_1 = st.text_input("Choice 1", value=existing_titles[0], placeholder="e.g. Assembly award")
        title_2 = st.text_input("Choice 2", value=existing_titles[1], placeholder="e.g. Art activity")
        title_3 = st.text_input("Choice 3", value=existing_titles[2], placeholder="e.g. Playground game")
        title_4 = st.text_input("Choice 4", value=existing_titles[3], placeholder="e.g. Hurt at recess")
        title_5 = st.text_input("Choice 5", value=existing_titles[4], placeholder="e.g. Sports practice")

        save_choices = st.form_submit_button("Save Recount Choices", use_container_width=True)

    if save_choices:
        titles = [title_1, title_2, title_3, title_4, title_5]
        if db_save_recount_prompts(therapist_id, client_name, titles):
            st.success("Recount choices saved.")
            st.rerun()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if st.button(
        "Clear All Recount Choices",
        key=f"clear_recount_choices_{child_key}",
        use_container_width=True,
    ):
        if db_delete_recount_prompts(therapist_id, client_name):
            st.success("Recount choices cleared.")
            st.rerun()

    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">CURRENT</span>'
        '<span class="step-text">Saved Choices</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    saved_prompts = db_load_recount_prompts(therapist_id, client_name)

    if saved_prompts:
        for row in saved_prompts:
            st.markdown(f"""
            <div class="note-entry">
                <div class="note-entry-header">
                    <span class="note-entry-date">Choice {row['event_order']}</span>
                </div>
                <div class="note-entry-text">{row['title']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="empty-state">No recount choices saved yet.</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════
#  TAB 3 — REACHY FEEDBACK
# ══════════════════════════════════════════════════════════════
with tab_feedback:
    st.markdown(
        '<div class="step-label">'
        '<span class="step-num">ADD</span>'
        '<span class="step-text">Reachy Feedback</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        'Share anything you noticed during or after the recount activity - for example engagement, difficulty, helpful prompts, behaviours, or concerns.'
        '</div>',
        unsafe_allow_html=True,
    )

    new_feedback = st.text_area(
        "Your observation",
        height=160,
        placeholder=" ",
        key=f"feedback_input_{child_key}",
        label_visibility="collapsed",
    )

    if st.button(
        "Submit Feedback",
        type="primary",
        use_container_width=True,
        key=f"feedback_add_{child_key}",
    ):
        if new_feedback.strip():
            timestamp = datetime.now().strftime("%d %b %Y - %I:%M %p")
            db_add_parent_feedback(therapist_id, client_name, timestamp, new_feedback.strip())
            st.rerun()
        else:
            st.warning("Please write something before submitting.")

    st.markdown(
        '<div class="step-label" style="margin-top:28px">'
        '<span class="step-num">LOG</span>'
        '<span class="step-text">Previous Feedback</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    feedback_list = db_load_parent_feedback(therapist_id, client_name)

    if feedback_list:
        for entry in reversed(feedback_list):
            st.markdown(f"""
            <div class="note-entry">
                <div class="note-entry-header">
                    <span class="note-entry-date">{entry['timestamp']}</span>
                </div>
                <div class="note-entry-text">{entry['text']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Delete", key=f"fb_del_{entry['id']}"):
                db_delete_parent_feedback(entry["id"])
                st.rerun()
    else:
        st.markdown(
            '<div class="empty-state">No feedback submitted yet.</div>',
            unsafe_allow_html=True,
        )
