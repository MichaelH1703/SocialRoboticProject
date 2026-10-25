"""Test 3, interactive: you type as April, Reachy replies.

    python run_interactive.py            one new session (I1, I2, ...), then exits
    python run_interactive.py sheet      rating_sheet.tsv (shuffled) + rating_key.tsv
    python run_interactive.py results    results_row.tsv + results_by_session.tsv from ratings.tsv

Same setup as ../run_sessions.py, whose functions are imported unchanged:
April with her full context (same therapist id and event titles), saving off,
every Ollama model unloaded before the session, a brand-new process per
session (one launch = one session), and April's database rows snapshotted
before and after (appended to isolation_check.txt).

A session ends after 10 model replies the child heard (the kind analyse.py
rates: not the greeting, scripted lines, safety replacements or the "slow
today" apology), or on /end, or when Reachy's goodbye flow ends it.
Everything is written as it happens: raw/<id>.txt (console output, same format
as ../raw) and rows/<id>.tsv (session_id, child_said, reachy_said, as
../sheet_rows.tsv), so a crash loses nothing.
"""

import csv
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
TEST3 = HERE.parent
PROJECT = TEST3.parent.parent
sys.path[:0] = [str(PROJECT), str(TEST3)]

from run_sessions import THERAPIST_ID, db_snapshot, loaded_models, m, unload_all_models  # noqa: E402

REPLIES_PER_SESSION = 10
SHEET_SEED = 3
DIMENSIONS = ["responsive", "clear", "technique", "no_invention"]
RAW, ROWS = HERE / "raw", HERE / "rows"


def cell(v) -> str:
    return str(v).replace("\t", " ").replace("\n", " ")


class Tee:
    """Console output, also written straight to the raw log."""

    def __init__(self, console, path: Path):
        self.console, self.file = console, path.open("w", encoding="utf-8")
        self.turn = ""  # what the current turn printed

    def write(self, text: str) -> int:
        self.console.write(text)
        self.log(text)
        return len(text)

    def log(self, text: str) -> None:
        self.file.write(text)
        self.file.flush()
        self.turn += text

    def flush(self) -> None:
        self.console.flush()

    def isatty(self) -> bool:
        # As in the redirected scripted runs: no "(thinking...)" line in the log.
        return False


def session_ids() -> list:
    return sorted((p.stem for p in RAW.glob("I*.txt")), key=lambda s: int(s[1:]))


def check_event_titles() -> None:
    """April must have the five Test 3 event titles, as in the scripted run."""
    sql = (f"SELECT title FROM recount_event_prompts WHERE therapist_id = '{THERAPIST_ID}' "
           f"AND client_name = '{m['client_name']}' ORDER BY event_order;")
    titles = subprocess.run(
        ["docker", "exec", "-i", "supabase_db_ReachyVoiceCode", "psql", "-U", "postgres", "-d", "postgres", "-At"],
        input=sql.encode("utf-8"), capture_output=True, check=True).stdout.decode("utf-8").split("\n")
    expected = [s["event_title"] for s in m["stories"].values()]
    missing = [t for t in expected if t not in titles]
    if missing:
        raise SystemExit(f"April is missing Test 3 event titles {missing}. Re-add them (../add_event_titles.py) first.")


def run_session() -> None:
    check_event_titles()
    RAW.mkdir(exist_ok=True)
    ROWS.mkdir(exist_ok=True)
    sid = f"I{len(session_ids()) + 1}"
    while (RAW / f"{sid}.txt").exists():
        sid = f"I{int(sid[1:]) + 1}"

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    console = sys.stdout
    before = db_snapshot()
    unloaded = unload_all_models()

    os.environ["THERAPIST_ID"] = THERAPIST_ID
    os.environ["CLIENT_NAME"] = m["client_name"]
    os.chdir(PROJECT)
    tee = Tee(console, RAW / f"{sid}.txt")
    sys.stdout = tee

    import reachy_text_chat as rtc

    rtc.SAVE_TO_SUPABASE = False
    print(f"[Interactive] session {sid}, typed by a person; {REPLIES_PER_SESSION} model replies, /end to stop")
    isolation = (f"new process pid {os.getpid()}; Reachy chat history {len(rtc.chat_history)} items, "
                 f"conversation log {len(rtc.conversation_log)} rows; models loaded in Ollama: {loaded_models() or 'none'}")
    print(f"[Isolation] {isolation}")
    rtc.warm_up_model()

    context = rtc.build_context_from_supabase(rtc.THERAPIST_ID, rtc.CLIENT_NAME)
    print(f"[Interactive] Event titles: {', '.join(rtc.session_state.get('teacher_titles', []))}")
    chat = rtc.TextSession(context)
    chat.update_instructions()
    chat.greet()

    rows_file = (ROWS / f"{sid}.tsv").open("w", encoding="utf-8", newline="")
    replies, end = 0, "Ctrl+C or end of input"
    try:
        while replies < REPLIES_PER_SESSION:
            console.write("You: ")
            console.flush()
            line = sys.stdin.readline()
            if not line:
                break
            text = line.strip()
            if not text:
                continue
            if text.lower() == "/end":
                end = "/end"
                break
            if text.startswith("/"):
                console.write("Only /end works here.\n")
                continue
            tee.log(f"You: {text}\n")
            tee.turn, before_turn = "", len(rtc.chat_history)
            chat.handle(text)
            if "[Latency] Turn:" in tee.turn and "[Safety] Replaced a reply that" not in tee.turn \
                    and "[LLM] No reply within" not in tee.turn:
                reply = " ".join(e["text"] for e in rtc.chat_history[before_turn:] if e["role"] == "assistant")
                rows_file.write("\t".join(cell(v) for v in (sid, text, reply)) + "\n")
                rows_file.flush()
                replies += 1
                print(f"[Interactive] Reply {replies} of {REPLIES_PER_SESSION} saved.")
            if chat.ended:
                end = "Reachy's goodbye"
                break
        else:
            end = f"{REPLIES_PER_SESSION} replies"
    except KeyboardInterrupt:
        pass
    finally:
        rows_file.close()
        print(f"[Interactive] Session {sid} ended ({end}), {replies} replies saved.")
        after = db_snapshot()
        log = [f"{sid} ({time.strftime('%Y-%m-%d %H:%M')}): {unloaded} before starting", f"    {isolation}"]
        log += [f"    {t}: before {before[t]} | after {after[t]}" for t in before]
        log += [f"    Unchanged by the session: {before == after}", ""]
        with (HERE / "isolation_check.txt").open("a", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n")
        print(f"[Interactive] Database unchanged by the session: {before == after}")
        sys.stdout = console
        tee.file.close()


def tsv(rows: list, columns: list) -> str:
    return "\n".join(["\t".join(columns)] + ["\t".join(cell(r[c]) for c in columns) for r in rows]) + "\n"


def sheet() -> None:
    if (HERE / "ratings.tsv").exists():
        raise SystemExit("ratings.tsv exists: rebuilding the sheet would reshuffle it. Move ratings.tsv first.")
    replies = []
    for sid in session_ids():
        path = ROWS / f"{sid}.tsv"
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        for n, line in enumerate(lines, start=1):
            _, child, reachy = line.split("\t")
            replies.append({"session_id": sid, "reply_no": n, "child_said": child, "reachy_said": reachy})
        print(f"{sid}: {len(lines)} replies")
    random.Random(SHEET_SEED).shuffle(replies)
    for i, r in enumerate(replies, start=1):
        r["reply_id"] = i
        for c in DIMENSIONS + ["harm", "notes"]:
            r[c] = ""
    (HERE / "rating_sheet.tsv").write_text(
        tsv(replies, ["reply_id", "child_said", "reachy_said"] + DIMENSIONS + ["harm", "notes"]), encoding="utf-8")
    (HERE / "rating_key.tsv").write_text(
        tsv(replies, ["reply_id", "session_id", "reply_no", "child_said", "reachy_said"]), encoding="utf-8")
    print(f"{len(replies)} replies, shuffled with seed {SHEET_SEED}: rating_sheet.tsv, key in rating_key.tsv")


def results() -> None:
    def read(name: str) -> list:
        with (HERE / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f, delimiter="\t"))
    key = {r["reply_id"]: r for r in read("rating_key.tsv")}
    rows = read("ratings.tsv")
    assert sorted(r["reply_id"] for r in rows) == sorted(key), \
        f"ratings.tsv must have every reply_id in rating_key.tsv ({len(key)}), got {len(rows)}"

    def summary(group: list) -> list:
        means = [mean(int(r[d]) for r in group) for d in DIMENSIONS]
        overall = mean(mean(int(r[d]) for d in DIMENSIONS) for r in group)
        harmful = sum(r["harm"].strip().upper() == "Y" for r in group)
        return [f"{x:.2f}" for x in means] + [f"{overall:.2f}", str(harmful)]

    header = DIMENSIONS + ["overall_mean", "harmful"]
    row = summary(rows)
    (HERE / "results_row.tsv").write_text("\t".join(row) + "\n", encoding="utf-8")
    by_session = ["\t".join(["session_id", "replies"] + header)]
    for sid in session_ids():
        group = [r for r in rows if key[r["reply_id"]]["session_id"] == sid]
        if group:
            by_session.append("\t".join([sid, str(len(group))] + summary(group)))
    (HERE / "results_by_session.tsv").write_text("\n".join(by_session) + "\n", encoding="utf-8")
    print("Mean responsive, clear, technique, no_invention, overall mean, harmful replies:")
    print("\t".join(row))
    print("\n".join(by_session))


if __name__ == "__main__":
    {"sheet": sheet, "results": results}.get(sys.argv[1] if sys.argv[1:] else "", run_session)()
