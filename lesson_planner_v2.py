"""Lesson plan generator, version 2. Same interface as lesson_planner.py.

Version 1 handed the raw transcript to a 3B model with one free-form request.
Test 6 found three systematic problems with that: the therapist's words were
credited to the child, absences were never noticed (a child who gave no
reasons), and feelings and gaps were invented. Version 2 changes how the
analysis is done, not what it is asked about:

1. Speakers are separated in code, from the "Therapist." / "Child." labels.
   Only the child's turns count as the child's words.
2. Simple measures are counted in code from the child's turns: linking words
   ("because", "so", "then"...), emotion words, vague words, and answer length.
3. The model fills a recount checklist (who, where, what happened, ending),
   quoting the child's exact words for each part it says was given.
4. Every quote gets two checks: in code, that its sentences really are the
   child's; and by a short yes/no question, that they really state that part
   (a bare "yes" or "um" never counts). A part that fails, even after one
   focused second look, counts as not given. For the ending there is one more
   check in code: if the therapist later asked how it ended and the child
   said they did not know, the earlier words were not the child's ending.
5. Sections 2-4 of the plan are built from those verified facts, so every
   quote in them is the child's own. The model writes only the summary, the
   practice goals and Reachy's prompts. The goals themselves are chosen in
   code from the verified gaps; the model only phrases them and writes one
   prompt each, without seeing the transcript, so they work for any event.

A bigger model (qwen3:8b, thinking off) at low temperature is used: the plan
is made offline in the dashboard, so speed matters less than consistency.

Real session transcripts have no speaker labels. The model then labels each
sentence as the therapist's or the child's (sentence numbers keep its labels
in line), a rule in code catches the therapist echoing the child's words, and
the plan notes that the labels were added automatically. If labelling fails,
the plan says so and the checks run on the whole transcript.
"""

import json
import os
import re
import urllib.error
import urllib.request
from difflib import SequenceMatcher
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")
DEFAULT_MODEL = os.getenv("LESSON_PLANNER_MODEL", "qwen3:8b")

# The parts of a recount checked by the model. Feelings are counted in code.
STORY_PARTS = {
    "who": "who was there or took part (people or animals)",
    "where": "where it happened (the place)",
    "what_happened": "what happened: the main events, or what the child did",
    "ending": "how it ended: how the event finished, or what happened at the very end of it",
}
PART_NAMES = {"who": "who was there", "where": "where it happened",
              "what_happened": "what happened", "ending": "how it ended"}

EMOTION_WORDS = {
    "happy", "sad", "angry", "cross", "mad", "scared", "afraid", "frightened", "worried", "nervous",
    "excited", "proud", "annoyed", "upset", "glad", "bored", "lonely", "jealous", "embarrassed",
    "surprised", "calm", "frustrated", "grumpy", "shy", "relieved", "disappointed", "cheerful",
    "thrilled", "delighted", "confused", "silly", "fed",
}
# "fed" only as in "fed up". Pain ("it hurt"), tiredness and apologies are not
# counted: they are not named emotions.
REASON_WORDS = re.compile(r"\b(?:because|cos|'cause)\b|\bso\s+(?=(?:i|we|you|he|she|they|it|the|my|our|"
                          r"everyone|everybody|nobody|mum|mom|dad|then)\b)", re.I)
SEQUENCE_WORDS = re.compile(r"\b(?:then|first|next|after|afterwards|finally|later|before)\b", re.I)
VAGUE_WORDS = re.compile(r"\b(?:stuff|thing|things|something)\b", re.I)
LABEL = re.compile(r"\b(Therapist|Child)\s*[.:]\s+")


# ── Transcript parsing and counted facts ─────────────────────────────────────

def split_turns(transcript: str) -> Optional[List[Tuple[str, str]]]:
    """[(speaker, words)] from the spoken labels, or None if there are none."""
    parts = LABEL.split(transcript)
    turns = [(parts[i].lower(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)
             if parts[i + 1].strip()]
    if not any(speaker == "child" for speaker, _ in turns):
        return None
    return turns


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


def emotion_words_in(text: str) -> List[str]:
    found = []
    for word in re.findall(r"[a-z']+", text.lower()):
        if word in EMOTION_WORDS and word not in found:
            if word == "fed" and not re.search(r"\bfed up\b", text, re.I):
                continue
            found.append("fed up" if word == "fed" else word)
    return found


def count_facts(child_turns: List[str]) -> Dict[str, Any]:
    """Measures counted from the child's turns only. No model involved."""
    feelings = []
    for turn in child_turns:
        for word in emotion_words_in(turn):
            if word not in [f["word"] for f in feelings]:
                feelings.append({"word": word, "child_words": turn})
    return {
        "child_turns": len(child_turns),
        "mean_words_per_turn": round(mean(len(t.split()) for t in child_turns), 1) if child_turns else 0,
        "reasons": [t for t in child_turns if REASON_WORDS.search(t)],
        "sequence_words": sorted({m.lower() for t in child_turns for m in SEQUENCE_WORDS.findall(t)}),
        "vague_words": sorted({m.lower() for t in child_turns for m in VAGUE_WORDS.findall(t)}),
        "feelings": feelings,
        "feeling_reasons": [t for t in child_turns if emotion_words_in(t) and REASON_WORDS.search(t)],
    }


def is_childs_words(quote: str, child_turns: List[str]) -> bool:
    """Whether a quote is really the child's: word for word, or very nearly."""
    q = _norm(quote)
    if not q:
        return False
    if q in _norm(" ".join(child_turns)):
        return True
    return any(SequenceMatcher(None, q, _norm(t)).ratio() >= 0.85 for t in child_turns)


FILLER = re.compile(r"^(?:yeah|yes|yep|no|nope|ok|okay|um+|uh+|mm+|hmm+)$")


def childs_sentences(quote: str, child_turns: List[str]) -> str:
    """The sentences of a quote that are really the child's, skipping bare yes/no/um.

    Quotes often join several of the child's turns, skipping the ones between,
    so they are checked a sentence at a time rather than as one string.
    """
    kept = [s for s in re.split(r"(?<=[.!?])\s+", quote.strip())
            if s and not FILLER.match(_norm(s)) and is_childs_words(s, child_turns)]
    return " ".join(kept)


def question_before(words: str, turns: Optional[List[Tuple[str, str]]], transcript: str = "") -> str:
    """The therapist's last line before the child's turn that holds `words`.

    Without speaker labels there is no turn to find, so the text just before
    the words is given instead.
    """
    if not turns:
        first = re.split(r"(?<=[.!?])\s+", words)[0][:40]
        at = transcript.find(first) if first else -1
        return transcript[max(0, at - 200):at].strip() if at > 0 else ""
    first = _norm(re.split(r"(?<=[.!?])\s+", words)[0])
    for i, (speaker, text) in enumerate(turns):
        if speaker == "child" and first and first in _norm(text):
            for prev_speaker, prev_text in reversed(turns[:i]):
                if prev_speaker == "therapist":
                    return prev_text
            break
    return ""


ENDING_QUESTION = re.compile(r"\b(?:end|ended|ending|finish|finished)\b[^.!?]*\?", re.I)
NOT_KNOWN = re.compile(r"\b(?:don'?t know|dunno|can'?t remember|don'?t remember|not sure|no idea|"
                       r"don'?t want to say)\b", re.I)


def ending_not_known(words: str, turns: Optional[List[Tuple[str, str]]]) -> bool:
    """Whether, after the child said `words`, the therapist asked how it ended
    and the child said they did not know (or did not want to say).

    Then `words` were not the ending in the child's own account, however much
    they sound like one: a story's last event is not always its ending.
    """
    if not turns:
        return False
    first = _norm(re.split(r"(?<=[.!?])\s+", words)[0])
    start = next((i for i, (speaker, text) in enumerate(turns)
                  if speaker == "child" and first and first in _norm(text)), None)
    if start is None:
        return False
    for (speaker, text), (next_speaker, reply) in zip(turns[start + 1:], turns[start + 2:]):
        if speaker == "therapist" and next_speaker == "child" and ENDING_QUESTION.search(text):
            return bool(NOT_KNOWN.search(reply)) and len(reply.split()) <= 8
    return False


# ── Model calls ──────────────────────────────────────────────────────────────

def _chat(model: str, system: str, user: str, temperature: float) -> Dict[str, Any]:
    body = {
        "model": model, "stream": False, "format": "json", "think": False,
        "options": {"temperature": temperature, "seed": 0},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    def post(payload: Dict[str, Any]) -> str:
        request = urllib.request.Request(OLLAMA_CHAT_URL, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=300) as resp:
            return json.load(resp)["message"]["content"]
    try:
        content = post(body)
    except urllib.error.HTTPError as e:
        # Models without a thinking mode can reject the flag.
        if e.code != 400:
            raise
        body.pop("think")
        content = post(body)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


CHECKLIST_SYSTEM = (
    "You check a speech therapy transcript for the parts of a recount that the CHILD gave. "
    "You copy the child's words exactly. The therapist's words never count as the child's."
)


VERIFY_SYSTEM = "You check one detail of a child's recount. Answer only from the words given."


def confirm_part(part: str, words: str, question: str, model: str) -> bool:
    """A focused second check: do these words of the child's really state this part?"""
    exchange = (f'Therapist: "{question}"\n' if question else "") + f'Child: "{words}"'
    user = (f"Part of a conversation between a speech therapist and a child:\n{exchange}\n\n"
            f"Do the child's words tell us {STORY_PARTS[part]}? A short answer counts when it answers the "
            "therapist: for example, Therapist: \"Where did you go?\" Child: \"The beach.\" tells us where it "
            "happened. Answer false only if the child's words do not give this, for example because they talk "
            'about something else or say they do not know. Return JSON: {"states_it": true or false}')
    return bool(_chat(model, VERIFY_SYSTEM, user, temperature=0.0).get("states_it"))


def check_story_parts(child_turns: List[str], transcript: str, turns: Optional[List[Tuple[str, str]]],
                      model: str) -> Dict[str, Any]:
    labelled = turns is not None
    if labelled:
        source = ("The child's turns, numbered. Only these are the child's words:\n"
                  + "\n".join(f"C{i}: {t}" for i, t in enumerate(child_turns, start=1))
                  + f"\n\nFull transcript, for context only:\n<<<\n{transcript}\n>>>")
    else:
        source = ("This transcript has no speaker labels, so take care to use only what the child "
                  f"seems to say:\n<<<\n{transcript}\n>>>")
    parts = "\n".join(f'- "{key}": {desc}' for key, desc in STORY_PARTS.items())
    user = (
        f"{source}\n\nFor each part of the recount below, decide whether the CHILD said it, and copy the "
        "child's exact words that say it. A part only counts if the child's own words state it. If only the "
        "therapist said it, or the child said they did not know or could not remember, it is not given. "
        "A 'yes' or 'no' on its own never counts.\n"
        f"{parts}\n\n"
        'Return JSON: {"event": "<a few words naming what the child talked about>", '
        + ", ".join(f'"{k}": {{"given": true or false, "child_words": "<exact words, or empty>"}}' for k in STORY_PARTS)
        + "}"
    )
    raw = _chat(model, CHECKLIST_SYSTEM, user, temperature=0.0)

    def verified(claim: str) -> str:
        # Two checks: the words must really be the child's (code), and must
        # really state this part (a focused yes/no question to the model).
        words = childs_sentences(claim, child_turns) if claim else ""
        if key == "ending" and words and ending_not_known(words, turns):
            return ""
        ok = bool(words) and confirm_part(key, words, question_before(words, turns, transcript), model)
        return words if ok else ""

    checked = {"event": str(raw.get("event", "")).strip()}
    for key in STORY_PARTS:
        item = raw.get(key) if isinstance(raw.get(key), dict) else {}
        claim = str(item.get("child_words", "")).strip() if item.get("given") else ""
        words = verified(claim)
        second = ""
        if not words and labelled:
            # One focused second look at just this part. The checklist pass
            # sometimes picks the wrong turn ("Yeah." for an ending) when the
            # right one is there; the same two checks still apply.
            second = find_part(key, turns, model)
            words = verified(second)
        checked[key] = {"given": bool(words), "child_words": words,
                        "rejected_claim": "" if words else " | ".join(c for c in (claim, second) if c)}
    return checked


def find_part(part: str, turns: List[Tuple[str, str]], model: str) -> str:
    """Ask about one part only: which of the child's turns, if any, states it?

    Each child turn is shown after the end of the therapist's line before it,
    since the question often shows what a short answer is about.
    """
    lines, child_turns = [], []
    for i, (speaker, text) in enumerate(turns):
        if speaker != "child":
            continue
        if i and turns[i - 1][0] == "therapist":
            lines.append("Therapist: " + " ".join(re.split(r"(?<=[.!?])\s+", turns[i - 1][1].strip())[-2:]))
        child_turns.append(text)
        lines.append(f"C{len(child_turns)}: {text}")
    user = ("The conversation, with the child's turns numbered:\n" + "\n".join(lines)
            + f"\n\nWhich one of the child's turns, if any, states {STORY_PARTS[part]}? It must say it in the "
            'child\'s own words; a "yes" or "no" on its own never counts. '
            'Return JSON: {"turn": <number of the C turn, or 0 if none>}')
    found = re.search(r"\d+", str(_chat(model, CHECKLIST_SYSTEM, user, temperature=0.0).get("turn", 0)))
    n = int(found.group()) if found else 0
    return child_turns[n - 1] if 1 <= n <= len(child_turns) else ""


LABEL_SYSTEM = "You label speakers in transcripts of speech therapy sessions."
LABEL_CHUNK = 80  # sentences per call; a long session is labelled in parts
# Words a therapist adds when echoing a child's answer back ("You kicked the
# ball", "And then you jumped", "Really annoyed").
ECHO_EXTRA = {"and", "then", "so", "the", "a", "an", "you", "your", "really", "very", "oh", "ah", "wow",
              "great", "nice", "good", "well", "done", "okay", "ok", "yeah", "right"}


def split_sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip()) if s]


def label_speakers(sentences: List[str], model: str) -> Optional[List[str]]:
    """The model's "T"/"C" for each sentence, or None if too many are missing.

    Each label is keyed by its sentence number: asked for a plain list, the
    model sometimes returns one label too many and every later label slips.
    """
    labels: List[str] = []
    for first in range(1, len(sentences) + 1, LABEL_CHUNK):
        last = min(first + LABEL_CHUNK - 1, len(sentences))
        context = ""
        if first > 1:
            context = ("Lines just before these, already labelled:\n" + "\n".join(
                f"{n}. [{labels[n - 1]}] {sentences[n - 1]}" for n in range(max(1, first - 6), first)) + "\n\n")
        user = ("This is a transcript of a speech therapy session between a therapist (an adult) and a child. The "
                "speaker labels are missing. Each numbered line is one sentence.\n\n"
                'Label who said each sentence: "T" for the therapist or "C" for the child.\n'
                "- The therapist usually starts. They ask questions, tell a short story of their own, repeat or "
                "rephrase the child's words, praise, and say the child's story back to them.\n"
                "- The child usually gives short answers.\n"
                "- When the therapist repeats the child's words back, that sentence is still the therapist's.\n\n"
                + context + "\n".join(f"{n}. {sentences[n - 1]}" for n in range(first, last + 1))
                + f'\n\nReturn JSON with one entry per line number, {first} to {last}: '
                f'{{"{first}": "T" or "C", ...}}')
        raw = _chat(model, LABEL_SYSTEM, user, temperature=0.0)
        labels += [str(raw.get(str(n), "")).strip().upper()[:1] for n in range(first, last + 1)]
    missing = sum(label not in ("T", "C") for label in labels)
    if missing > len(labels) / 10:
        return None
    # When unsure, never credit a sentence to the child.
    return [label if label in ("T", "C") else "T" for label in labels]


def is_echo(sentence: str, child_before: List[str]) -> bool:
    """A short sentence made only of the child's words just before it."""
    words = _norm(sentence).split()
    said = set(_norm(" ".join(child_before)).split())
    content = [w for w in words if w not in ECHO_EXTRA]
    return 0 < len(words) <= 6 and bool(content) and all(w in said for w in content)


def auto_label(transcript: str, model: str) -> Optional[Dict[str, Any]]:
    """Speaker labels for a transcript that has none, a sentence at a time.

    A "child" sentence that only repeats the child's words just before it is
    relabelled as the therapist's echo. If the child really did repeat
    themselves, nothing is lost: those words are already in their turn.
    Returns None if labelling failed or found no child.
    """
    sentences = split_sentences(LABEL.sub("", transcript))
    labels = label_speakers(sentences, model) if sentences else None
    if not labels:
        return None
    echoes, run = [], []
    for i, (label, sentence) in enumerate(zip(labels, sentences)):
        if label == "C" and run and is_echo(sentence, run):
            labels[i] = "T"
            echoes.append(i)
        run = run + [sentence] if labels[i] == "C" else []
    if "C" not in labels:
        return None
    return {"sentences": [["therapist" if l == "T" else "child", s] for l, s in zip(labels, sentences)],
            "echoes_relabelled": echoes}


def to_turns(sentences: List[List[str]]) -> List[Tuple[str, str]]:
    """Join consecutive sentences by the same speaker into turns."""
    turns: List[Tuple[str, str]] = []
    for speaker, sentence in sentences:
        if turns and turns[-1][0] == speaker:
            turns[-1] = (speaker, f"{turns[-1][1]} {sentence}")
        else:
            turns.append((speaker, sentence))
    return turns


WRITER_SYSTEM = (
    "You help a speech and language therapist plan recount practice for a child. You only use the facts "
    "you are given, and you never add anything about the child that is not in them."
)


def choose_goals(facts: Dict[str, Any], checked: Dict[str, Any], labelled: bool) -> List[str]:
    """Practice goals, taken from the verified gaps in code, so none is set for
    something the child already did. Phrased for any event."""
    goals = [f"Say {PART_NAMES[k]}." for k in STORY_PARTS if not checked[k]["given"]]
    if labelled:
        if not facts["feelings"]:
            goals.append("Name how they felt.")
        elif not facts["feeling_reasons"]:
            goals.append("Say why they felt that way.")
        if not facts["reasons"]:
            goals.append("Give a reason, using 'because' or 'so'.")
        if facts["vague_words"]:
            goals.append("Use the exact word instead of vague words like 'stuff' or 'thing'.")
        if not facts["sequence_words"]:
            goals.append("Put events in order with words like 'first' and 'then'.")
    return goals[:4] or ["Add more detail to each part of the recount."]


def write_summary(facts: Dict[str, Any], checked: Dict[str, Any], model: str, transcript: str) -> str:
    source = (f"What the child said, in order: {' / '.join(facts['child_text'])}" if facts["child_text"] else
              "Transcript (speakers not labelled, so describe only the child's account):\n"
              f"<<<\n{transcript}\n>>>")
    user = (f"Event: {checked['event'] or 'not clear'}\n{source}\n\n"
            "Write 2-3 plain sentences saying what the child told, using only what the child said. Call them "
            "'the child'. No quotation marks. Do not add feelings, reasons or details the child did not give. "
            'Return JSON: {"summary": "..."}')
    raw = _chat(model, WRITER_SYSTEM, user, temperature=0.2)
    return str(raw.get("summary", "")).replace('"', "").replace("“", "").replace("”", "").strip()


def write_goals(goals: List[str], model: str) -> Dict[str, List[str]]:
    """Phrase the goals and write one prompt for each. This call never sees the
    transcript, so neither can mention the event."""
    user = ("Practice goals for a child's recounts:\n" + "\n".join(f"{i}. {g}" for i, g in enumerate(goals, 1))
            + "\n\nFor each goal, write:\n"
            '- "focus": the goal as one short sentence for the speech therapist.\n'
            '- "prompts": one question a robot could ask a child about anything they did, to practise that goal. '
            "One short, simple question in child-friendly words. Say 'it' or 'that', not 'the event'.\n"
            'Return JSON: {"focus": ["..."], "prompts": ["..."]}, in the same order as the goals.')
    raw = _chat(model, WRITER_SYSTEM, user, temperature=0.2)
    focus = [str(x).strip() for x in raw.get("focus", []) if str(x).strip()][:len(goals)]
    prompts = [str(x).strip() for x in raw.get("prompts", [])
               if str(x).strip().endswith("?") and str(x).count("?") == 1][:len(goals)]
    return {"focus": focus or goals, "prompts": prompts}


# ── Putting it together ──────────────────────────────────────────────────────

def analyse_transcript(transcript: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """Every intermediate result, for checking and testing."""
    turns = split_turns(transcript)
    speakers = "given" if turns else "none"
    auto = auto_label(transcript, model) if turns is None else None
    if auto:
        turns = to_turns(auto["sentences"])
        transcript = " ".join(f"{speaker.capitalize()}. {words}" for speaker, words in turns)
        speakers = "auto"
    labelled = turns is not None
    child_turns = [w for s, w in turns if s == "child"] if labelled else [transcript]
    facts = count_facts(child_turns) if labelled else count_facts([])
    facts["child_text"] = child_turns if labelled else []
    checked = check_story_parts(child_turns, transcript, turns, model)
    goals = choose_goals(facts, checked, labelled)
    written = {"summary": write_summary(facts, checked, model, transcript), "goals": goals,
               **write_goals(goals, model)}
    return {"labelled": labelled, "speakers": speakers, "auto_labels": auto,
            "labelled_transcript": transcript if auto else None,
            "facts": facts, "checked": checked, "written": written}


def render_plan(analysis: Dict[str, Any]) -> str:
    facts, checked, written = analysis["facts"], analysis["checked"], analysis["written"]
    labelled = analysis["labelled"]
    lines = []
    if analysis.get("speakers") == "auto":
        lines += ["Note: this transcript had no speaker labels, so they were added automatically. A few sentences "
                  "may be credited to the wrong speaker, most often where the therapist repeats the child's words.",
                  ""]
    if not labelled:
        lines += ["Note: this transcript has no speaker labels, and they could not be added automatically, so "
                  "the child's words could not be separated from the therapist's. The checks below may include "
                  "the therapist's words, and linking words and feelings were not counted.", ""]

    lines += ["1. **Narrative Summary**", f"   - {written['summary'] or 'No summary could be written.'}"]
    if labelled:
        lines.append(f"   - The child spoke {facts['child_turns']} times, averaging "
                     f"{facts['mean_words_per_turn']} words.")

    strengths = [f'Said {PART_NAMES[k]}: "{checked[k]["child_words"]}"' for k in STORY_PARTS if checked[k]["given"]]
    if labelled:
        strengths += [f'Gave a reason: "{t}"' for t in facts["reasons"]]
        if facts["sequence_words"]:
            strengths.append("Used sequencing words: " + ", ".join(f'"{w}"' for w in facts["sequence_words"]))
        if facts["feelings"]:
            strengths.append("Named feelings: " + ", ".join(f["word"] for f in facts["feelings"]))
    lines += ["", "2. **Communication Strengths**"] + [f"   - {s}" for s in strengths or ["None identified."]]

    gaps = [f"Did not say {PART_NAMES[k]}." for k in STORY_PARTS if not checked[k]["given"]]
    if labelled:
        if not facts["reasons"]:
            gaps.append('Did not give any reasons (no "because" or "so").')
        if not facts["feelings"]:
            gaps.append("Did not name any feelings.")
        if facts["vague_words"]:
            gaps.append("Used vague words: " + ", ".join(f'"{w}"' for w in facts["vague_words"]))
    lines += ["", "3. **Communication Gaps**"] + [f"   - {g}" for g in gaps or ["None identified."]]

    emotional = []
    if labelled:
        emotional += [f'Named "{f["word"]}": "{f["child_words"]}"' for f in facts["feelings"]]
        if not facts["feelings"]:
            emotional.append("Did not name any feelings.")
        elif facts["feeling_reasons"]:
            emotional += [f'Explained a feeling: "{t}"' for t in facts["feeling_reasons"]]
        else:
            emotional.append("Did not say why they felt that way.")
    lines += ["", "4. **Emotional Understanding**"] + [f"   - {e}" for e in emotional or ["Not checked."]]

    lines += ["", "5. **Recommended Future Lesson Focus**"] + [f"   - {f}" for f in written["focus"] or ["None."]]
    lines += ["", "6. **Suggested Reachy Prompts**"] + [f'   - "{p}"' for p in written["prompts"] or ["None."]]
    return "\n".join(lines)


def generate_lesson_plan_from_transcript(transcript: str, model: str = DEFAULT_MODEL) -> str:
    """Drop-in replacement for lesson_planner.generate_lesson_plan_from_transcript."""
    return render_plan(analyse_transcript(transcript, model))
