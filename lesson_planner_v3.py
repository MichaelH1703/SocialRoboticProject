"""Lesson plan generator, version 3. Same interface as lesson_planner.py and lesson_planner_v2.py.

Version 2 (kept unchanged in lesson_planner_v2.py, the version Test 6
evaluated) separates the speakers, counts simple measures in code, and has the
model fill a recount checklist whose quotes are verified. On realistic
transcripts (Test 6, T21-T60) it had three weaknesses, which version 3 fixes:

1. Feelings came from a word list. "It was so fun", "I hated it" and "my
   stomach went all tight" were missed, and the plan said "Did not name any
   feelings". Feelings are now found by meaning. Each is checked like a story
   part: in code, that the quote is the child's own words; and by a yes/no
   question, that it shows how the child felt. Whether the child named the
   feeling with a feeling word is still checked in code, and is reported as
   its own point rather than as "no feelings".
2. Reasons came from linking words ("because", "so"), so a reason given
   without one ("I'd done the work. It was just the upload.") was missed.
   Reasons are now found by meaning and checked the same way. Whether the
   child linked them with "because" or "so" is reported separately.
3. Speakers were labelled a sentence at a time, and two things went wrong. A
   transcript with no punctuation became one long "sentence". And the labels
   drifted when the therapist told their own story straight after the
   child's first answer. Now text with little punctuation is first split into
   short pieces by the model, which copies the words; its copy is lined up
   with the original word by word, so the pieces are always the original
   words. The pieces (or sentences) are then labelled as before, and the
   labelling prompt describes the therapist's opening story.

Unchanged from version 2:
- the speaker split in code, and the echo rule for auto labels;
- the recount checklist (who, where, what happened, how it ended) with
  verified quotes, a second look, and the ending rule;
- sequencing and vague words counted in code;
- goals chosen in code from the verified gaps, then phrased by a separate
  model call that never sees the transcript.
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

# The parts of a recount checked by the checklist. Feelings are found separately.
STORY_PARTS = {
    "who": "who was there or took part (people or animals)",
    "where": "where it happened (the place)",
    "what_happened": "what happened: the main events, or what the child did",
    "ending": "how it ended: how the event finished, or what happened at the very end of it",
}
PART_NAMES = {"who": "who was there", "where": "where it happened",
              "what_happened": "what happened", "ending": "how it ended"}

# Feeling words. Used only to tell whether the child NAMED a feeling; the
# feelings themselves are found by meaning.
EMOTION_WORDS = {
    "happy", "sad", "angry", "cross", "mad", "scared", "afraid", "frightened", "worried", "nervous",
    "excited", "proud", "annoyed", "upset", "glad", "bored", "lonely", "jealous", "embarrassed",
    "surprised", "calm", "frustrated", "grumpy", "shy", "relieved", "disappointed", "cheerful",
    "thrilled", "delighted", "confused", "silly", "fed", "pleased", "anxious", "stressed", "terrified",
    "annoying", "embarrassing", "frustrating", "scary", "boring", "exciting",
}
# "fed" only as in "fed up".
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


def split_sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip()) if s]


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
    return {
        "child_turns": len(child_turns),
        "mean_words_per_turn": round(mean(len(t.split()) for t in child_turns), 1) if child_turns else 0,
        "sequence_words": sorted({m.lower() for t in child_turns for m in SEQUENCE_WORDS.findall(t)}),
        "vague_words": sorted({m.lower() for t in child_turns for m in VAGUE_WORDS.findall(t)}),
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


def exchange(turns: List[Tuple[str, str]]) -> Tuple[str, List[str]]:
    """The conversation with the child's turns numbered C1, C2, ..., each shown
    after the end of the therapist's line before it (the question often shows
    what a short answer is about), and the child's turns in order."""
    lines, child_turns = [], []
    for i, (speaker, text) in enumerate(turns):
        if speaker != "child":
            continue
        if i and turns[i - 1][0] == "therapist":
            lines.append("Therapist: " + " ".join(split_sentences(turns[i - 1][1])[-2:]))
        child_turns.append(text)
        lines.append(f"C{len(child_turns)}: {text}")
    return "\n".join(lines), child_turns


# ── Model calls ──────────────────────────────────────────────────────────────

MAX_REPLY_TOKENS = 4096  # far above any real answer; stops a reply that repeats itself forever


def _chat(model: str, system: str, user: str, temperature: float) -> Dict[str, Any]:
    """The model's JSON reply, or {} if it was not valid JSON or took too long.

    A reply that gets stuck repeating itself is cut off at MAX_REPLY_TOKENS,
    and so is not valid JSON; the caller then treats it as finding nothing.
    """
    body = {
        "model": model, "stream": False, "format": "json", "think": False,
        "options": {"temperature": temperature, "seed": 0, "num_predict": MAX_REPLY_TOKENS},
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
    except TimeoutError:
        return {}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _confirm(words: str, question: str, ask: str, model: str) -> Dict[str, Any]:
    """A focused yes/no check on a few of the child's words, shown after the therapist's question."""
    exchange_ = (f'Therapist: "{question}"\n' if question else "") + f'Child: "{words}"'
    user = f"Part of a conversation between a speech therapist and a child:\n{exchange_}\n\n{ask}"
    return _chat(model, VERIFY_SYSTEM, user, temperature=0.0)


CHECKLIST_SYSTEM = (
    "You check a speech therapy transcript for what the CHILD said. "
    "You copy the child's words exactly. The therapist's words never count as the child's."
)
VERIFY_SYSTEM = "You check one detail of a child's recount. Answer only from the words given."


def confirm_part(part: str, words: str, question: str, model: str) -> bool:
    """A focused second check: do these words of the child's really state this part?"""
    ask = (f"Do the child's words tell us {STORY_PARTS[part]}? A short answer counts when it answers the "
           "therapist: for example, Therapist: \"Where did you go?\" Child: \"The beach.\" tells us where it "
           "happened. Answer false only if the child's words do not give this, for example because they talk "
           'about something else or say they do not know. Return JSON: {"states_it": true or false}')
    return bool(_confirm(words, question, ask, model).get("states_it"))


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
    """Ask about one part only: which of the child's turns, if any, states it?"""
    convo, child_turns = exchange(turns)
    user = (f"The conversation, with the child's turns numbered:\n{convo}\n\nWhich one of the child's turns, if "
            f"any, states {STORY_PARTS[part]}? It must say it in the child's own words; a \"yes\" or \"no\" on its "
            'own never counts. Return JSON: {"turn": <number of the C turn, or 0 if none>}')
    found = re.search(r"\d+", str(_chat(model, CHECKLIST_SYSTEM, user, temperature=0.0).get("turn", 0)))
    n = int(found.group()) if found else 0
    return child_turns[n - 1] if 1 <= n <= len(child_turns) else ""


# ── Feelings and reasons, found by meaning ───────────────────────────────────

def _items(raw: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    value = raw.get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def find_feelings(turns: List[Tuple[str, str]], child_turns: List[str], model: str) -> List[Dict[str, Any]]:
    """The child's feelings, in any words, each with the child's own words for it."""
    convo, _ = exchange(turns)
    user = (f"The conversation, with the child's turns numbered:\n{convo}\n\n"
            "List every feeling the CHILD shows about what happened, in any words: a feeling word (\"sad\", "
            "\"annoyed\"), another phrase (\"I hated it\", \"it was so fun\", \"I couldn't stop laughing\"), or a "
            "body reaction the child gives as how they felt (\"my stomach went all tight\"). For each one, copy the "
            "child's exact words and name the feeling in one word.\n"
            "Do not count: a feeling that only the therapist says, even if the child answers \"yes\"; a feeling the "
            "child says they did not have (\"I wasn't scared\"); another person's feeling; or a bare \"fine\", "
            "\"okay\" or \"good\" in reply to \"How are you?\".\n"
            'Return JSON: {"feelings": [{"feeling": "<one word>", "child_words": "<exact words>"}]}')
    found: List[Dict[str, Any]] = []
    for item in _items(_chat(model, CHECKLIST_SYSTEM, user, temperature=0.0), "feelings"):
        label = str(item.get("feeling", "")).strip().lower()
        words = childs_sentences(str(item.get("child_words", "")), child_turns)
        if not label or not words or any(f["word"] == label or f["child_words"] == words for f in found):
            continue
        ask = ("Do the child's words show how the child themself felt (any feeling, in any words, including a "
               "body reaction like \"my tummy went funny\")? Answer false if the words only give facts, if the "
               "feeling is someone else's, or if the child says they did not feel it. "
               'Return JSON: {"shows_feeling": true or false}')
        if _confirm(words, question_before(words, turns), ask, model).get("shows_feeling"):
            found.append({"word": label, "child_words": words, "named": bool(emotion_words_in(words))})
    return found


def find_reasons(turns: List[Tuple[str, str]], child_turns: List[str], model: str) -> List[Dict[str, Any]]:
    """The child's reasons, with or without a linking word, each with the child's own words."""
    convo, _ = exchange(turns)
    user = (f"The conversation, with the child's turns numbered:\n{convo}\n\n"
            "List every reason the CHILD gives: where they say why something happened, why someone did something, "
            "or why they felt something. A reason counts with a linking word (\"because\", \"so\", \"cos\") or "
            "without one, for example Therapist: \"Why did you go outside?\" Child: \"It was too loud.\" Copy the "
            "child's exact words that give the reason. Do not count a reason that only the therapist gives, even "
            "if the child answers \"yes\". Most of what a child says is not a reason, and many children give no "
            "reasons at all: return an empty list if there are none.\n"
            'Return JSON: {"reasons": [{"child_words": "<exact words>", "explains": "<what it explains>"}]}')
    candidates = [str(item.get("child_words", "")) for item in
                  _items(_chat(model, CHECKLIST_SYSTEM, user, temperature=0.0), "reasons")]
    # Sentences with a linking word are reasons almost by definition: always check them too.
    candidates += [s for t in child_turns for s in split_sentences(t) if REASON_WORDS.search(s)]
    found: List[Dict[str, Any]] = []
    for claim in candidates:
        words = childs_sentences(claim, child_turns)
        n = _norm(words)
        if not n or any(n in _norm(r["child_words"]) or _norm(r["child_words"]) in n for r in found):
            continue
        linked = bool(REASON_WORDS.search(words))
        if not linked and len(words.split()) < 3:
            continue  # a one- or two-word answer ("Home.", "Dad.") is not a reason on its own
        # Asked yes or no, the model said yes to almost anything, so it has to
        # say what the reason explains, or "nothing".
        ask = ("Most things a child says are not reasons: saying what happened, who was there, where it was, what "
               "something was like, or how they felt is not a reason. A reason tells us WHY something happened, why "
               "someone did something, or why someone felt something, with or without \"because\" (Therapist: \"Why "
               "did you go outside?\" Child: \"It was too loud.\"). The why must be in the child's words, not only "
               "in the therapist's. If the child's words give a reason, say in a few words what it explains; "
               "otherwise answer \"nothing\". Also say whether it explains a feeling of the child's. "
               'Return JSON: {"explains": "<what the reason explains, or nothing>", '
               '"explains_a_feeling": true or false}')
        verdict = _confirm(words, question_before(words, turns), ask, model)
        explains = str(verdict.get("explains", "")).strip().strip(".").lower()
        # "because" and "cos" mark a reason by themselves; anything else needs the check.
        if linked or explains not in ("", "nothing", "none", "n/a", "no reason"):
            found.append({"child_words": words, "linked": linked,
                          "about_feeling": bool(verdict.get("explains_a_feeling"))})
    return found


# ── Speaker labels for unlabelled transcripts ────────────────────────────────

LABEL_SYSTEM = "You label speakers in transcripts of speech therapy sessions."
SPEAKER_GUIDE = (
    "How to tell them apart:\n"
    "- The therapist usually starts, with a greeting and a question.\n"
    "- The therapist often tells a short story of their own near the start (\"I've got a story from my "
    "weekend. I went to ...\"), even straight after the child's first answer. Those sentences are the "
    "therapist's.\n"
    "- The therapist asks most of the questions, repeats or rephrases the child's words, praises, uses the "
    "child's name, and may say the child's story back to them. When the therapist repeats the child's words "
    "back, that is still the therapist speaking.\n"
    "- The child answers, often briefly, tells their own story, and sometimes asks the therapist a question, "
    "which the therapist then answers.\n"
    "For example: \"Hi Sam, how was your week?\" (T) \"Fine.\" (C) \"I've got a story from my weekend first.\" (T) "
    "\"I went to the shop and forgot my bag.\" (T) \"What about you?\" (T) \"We went bowling.\" (C)\n"
)
TURN_WINDOW = 250  # words per call when splitting into turns
LABEL_CHUNK = 80   # sentences per call in the sentence-at-a-time fallback
# Words a therapist adds when echoing a child's answer back ("You kicked the
# ball", "And then you jumped", "Really annoyed").
ECHO_EXTRA = {"and", "then", "so", "the", "a", "an", "you", "your", "really", "very", "oh", "ah", "wow",
              "great", "nice", "good", "well", "done", "okay", "ok", "yeah", "right"}


def _align(words: List[str], turns_out: List[Dict[str, Any]]) -> Optional[Tuple[List[str], List[int]]]:
    """Each original word's speaker and turn number, from the model's copy of the text.

    The copy is lined up with the original word by word, so a word the model
    changed or dropped still gets a speaker (from the word before it). Returns
    None if under 90% of the original words are found in the copy.
    """
    out_words, out_speakers, out_ids = [], [], []
    for n, turn in enumerate(turns_out):
        speaker = str(turn.get("speaker", "")).strip().upper()[:1]
        if speaker not in ("T", "C"):
            continue
        for w in str(turn.get("text", "")).split():
            out_words.append(_norm(w))
            out_speakers.append("therapist" if speaker == "T" else "child")
            out_ids.append(n)
    original = [_norm(w) for w in words]
    speakers: List[Optional[str]] = [None] * len(words)
    ids: List[int] = [-1] * len(words)
    for block in SequenceMatcher(None, original, out_words, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            speakers[block.a + k], ids[block.a + k] = out_speakers[block.b + k], out_ids[block.b + k]
    if not words or sum(s is not None for s in speakers) < 0.9 * len(words):
        return None
    last_speaker, last_id = next(((s, i) for s, i in zip(speakers, ids) if s), ("therapist", 0))
    for k in range(len(words)):
        if speakers[k] is None:
            speakers[k], ids[k] = last_speaker, last_id
        last_speaker, last_id = speakers[k], ids[k]
    return speakers, ids


def _segments(words: List[str], speakers: List[str], ids: List[int]) -> List[List[str]]:
    """Runs of words in the same turn of the model's copy: [[speaker, text], ...]."""
    segments: List[List[str]] = []
    for word, speaker, n in zip(words, speakers, ids):
        if segments and segments[-1][0] == speaker and segments[-1][2] == n:
            segments[-1][1] += " " + word
        else:
            segments.append([speaker, word, n])
    return [[speaker, text] for speaker, text, _ in segments]


def split_units(text: str, model: str) -> Tuple[List[str], str]:
    """The pieces to label: sentences, or for text with little punctuation,
    short pieces the model marks out.

    Raw speech recognition output can have no full stops at all, which made a
    whole session one "sentence". Then the model splits the text where a new
    sentence starts or the speaker changes, copying the words; its copy is
    lined up with the original word by word, so the pieces are always the
    original words. It is not asked who speaks: asked for both at once, it
    assumed the speakers strictly take turns, and one wrong split put every
    later label out by one.
    """
    sentences = split_sentences(text)
    if not sentences or max(len(s.split()) for s in sentences) <= 40:
        return sentences, "sentences"
    words, units = text.split(), []
    for start in range(0, len(words), TURN_WINDOW):
        chunk = words[start:start + TURN_WINDOW]
        user = ("This is part of a transcript of a speech therapy session between a therapist and a child. It has "
                "little or no punctuation, so the speaker can change in the middle of a line.\n\n"
                "Split it into short pieces, in order: start a new piece wherever a new sentence or question starts, "
                "and always where the speaker changes. Copy every word exactly as it is: do not add, drop, change "
                f"or correct any word.\n\nText:\n<<<\n{' '.join(chunk)}\n>>>\n\n"
                'Return JSON: {"pieces": ["<exact words>", "<exact words>", ...]}')
        raw = _chat(model, LABEL_SYSTEM, user, temperature=0.0)
        pieces = raw.get("pieces") if isinstance(raw.get("pieces"), list) else []
        aligned = _align(chunk, [{"speaker": "T", "text": str(p)} for p in pieces])
        if aligned is None:
            return sentences, "sentences"
        units += [piece for _, piece in _segments(chunk, *aligned)]
    return units, "pieces"


def label_speakers(sentences: List[str], model: str) -> Optional[List[str]]:
    """The model's "T"/"C" for each piece, keyed by piece number, or None if
    too many are missing. (Asked for a plain list, the model sometimes returns
    one label too many and every later label slips.)"""
    labels: List[str] = []
    for first in range(1, len(sentences) + 1, LABEL_CHUNK):
        last = min(first + LABEL_CHUNK - 1, len(sentences))
        context = ""
        if first > 1:
            context = ("Lines just before these, already labelled:\n" + "\n".join(
                f"{n}. [{labels[n - 1]}] {sentences[n - 1]}" for n in range(max(1, first - 6), first)) + "\n\n")
        user = ("This is a transcript of a speech therapy session between a therapist (an adult) and a child. The "
                "speaker labels are missing. Each numbered line is one sentence.\n\n"
                'Label who said each sentence: "T" for the therapist or "C" for the child.\n' + SPEAKER_GUIDE + "\n"
                + context + "\n".join(f"{n}. {sentences[n - 1]}" for n in range(first, last + 1))
                + f'\n\nReturn JSON with one entry per line number, {first} to {last}: '
                f'{{"{first}": "T" or "C", ...}}')
        raw = _chat(model, LABEL_SYSTEM, user, temperature=0.0)
        labels += [str(raw.get(str(n), "")).strip().upper()[:1] for n in range(first, last + 1)]
    if sum(label not in ("T", "C") for label in labels) > len(labels) / 10:
        return None
    # When unsure, never credit a sentence to the child.
    return [label if label in ("T", "C") else "T" for label in labels]


def is_echo(segment: str, child_before: List[str]) -> bool:
    """A short stretch made only of the child's words just before it."""
    words = _norm(segment).split()
    said = set(_norm(" ".join(child_before)).split())
    content = [w for w in words if w not in ECHO_EXTRA]
    return 0 < len(words) <= 6 and bool(content) and all(w in said for w in content)


def auto_label(transcript: str, model: str) -> Optional[Dict[str, Any]]:
    """Speaker labels for a transcript that has none, a piece at a time.

    A short "child" piece that only repeats the child's words just before it
    is relabelled as the therapist's echo; if the child really did repeat
    themselves, nothing is lost, as those words are already in their turn.
    Returns None if labelling failed or found no child.
    """
    text = re.sub(r"\s+", " ", LABEL.sub("", transcript)).strip()
    units, method = split_units(text, model)
    labels = label_speakers(units, model) if units else None
    if not labels:
        return None
    segments = [["therapist" if label == "T" else "child", unit] for label, unit in zip(labels, units)]
    echoes, run = [], []
    for i, (speaker, segment) in enumerate(segments):
        if speaker == "child" and run and is_echo(segment, run):
            segments[i][0] = "therapist"
            echoes.append(i)
        run = run + [segment] if segments[i][0] == "child" else []
    if not any(speaker == "child" for speaker, _ in segments):
        return None
    return {"method": method, "segments": segments, "echoes_relabelled": echoes}


def to_turns(segments: List[List[str]]) -> List[Tuple[str, str]]:
    """Join consecutive segments by the same speaker into turns."""
    turns: List[Tuple[str, str]] = []
    for speaker, text in segments:
        if turns and turns[-1][0] == speaker:
            turns[-1] = (speaker, f"{turns[-1][1]} {text}")
        else:
            turns.append((speaker, text))
    return turns


# ── Writing the plan ─────────────────────────────────────────────────────────

WRITER_SYSTEM = (
    "You help a speech and language therapist plan recount practice for a child. You only use the facts "
    "you are given, and you never add anything about the child that is not in them."
)


def choose_goals(facts: Dict[str, Any], checked: Dict[str, Any], labelled: bool) -> List[str]:
    """Practice goals, taken from the verified gaps in code, so none is set for
    something the child already did. Phrased for any event."""
    goals = [f"Say {PART_NAMES[k]}." for k in STORY_PARTS if not checked[k]["given"]]
    if labelled:
        feelings, reasons = facts["feelings"], facts["reasons"]
        if not feelings:
            goals.append("Say how they felt.")
        else:
            if not any(f["named"] for f in feelings):
                goals.append("Name the feeling with a feeling word.")
            if not facts["feeling_reasons"]:
                goals.append("Say why they felt that way.")
        if not reasons:
            goals.append("Give a reason, using 'because' or 'so'.")
        elif not any(r["linked"] for r in reasons):
            goals.append("Link a reason with 'because' or 'so'.")
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
        turns = to_turns(auto["segments"])
        transcript = " ".join(f"{speaker.capitalize()}. {words}" for speaker, words in turns)
        speakers = "auto"
    labelled = turns is not None
    child_turns = [w for s, w in turns if s == "child"] if labelled else [transcript]
    facts = count_facts(child_turns) if labelled else count_facts([])
    facts["child_text"] = child_turns if labelled else []
    facts["feelings"] = find_feelings(turns, child_turns, model) if labelled else []
    facts["reasons"] = find_reasons(turns, child_turns, model) if labelled else []
    facts["feeling_reasons"] = [r["child_words"] for r in facts["reasons"] if r["about_feeling"]]
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
                  "the therapist's words, and feelings and reasons were not checked.", ""]

    lines += ["1. **Narrative Summary**", f"   - {written['summary'] or 'No summary could be written.'}"]
    if labelled:
        lines.append(f"   - The child spoke {facts['child_turns']} times, averaging "
                     f"{facts['mean_words_per_turn']} words.")

    feelings, reasons = facts["feelings"], facts["reasons"]
    strengths = [f'Said {PART_NAMES[k]}: "{checked[k]["child_words"]}"' for k in STORY_PARTS if checked[k]["given"]]
    if labelled:
        strengths += [f'Gave a reason: "{r["child_words"]}"' for r in reasons]
        if facts["sequence_words"]:
            strengths.append("Used sequencing words: " + ", ".join(f'"{w}"' for w in facts["sequence_words"]))
        if feelings:
            strengths.append("Said how they felt: " + ", ".join(f["word"] for f in feelings))
    lines += ["", "2. **Communication Strengths**"] + [f"   - {s}" for s in strengths or ["None identified."]]

    gaps = [f"Did not say {PART_NAMES[k]}." for k in STORY_PARTS if not checked[k]["given"]]
    if labelled:
        if not reasons:
            gaps.append("Did not give any reasons.")
        elif not any(r["linked"] for r in reasons):
            gaps.append('Gave reasons, but did not link them with "because" or "so".')
        if not feelings:
            gaps.append("Did not say how they felt.")
        elif not any(f["named"] for f in feelings):
            gaps.append("Showed how they felt, but did not name the feeling with a feeling word.")
        if facts["vague_words"]:
            gaps.append("Used vague words: " + ", ".join(f'"{w}"' for w in facts["vague_words"]))
    lines += ["", "3. **Communication Gaps**"] + [f"   - {g}" for g in gaps or ["None identified."]]

    emotional = []
    if labelled:
        emotional += [f'{"Named" if f["named"] else "Showed"} "{f["word"]}": "{f["child_words"]}"' for f in feelings]
        if not feelings:
            emotional.append("Did not say how they felt.")
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
