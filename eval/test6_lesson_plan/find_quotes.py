"""Pull every quoted example out of each plan and search for it in its transcript.

Quotes are text in double quotation marks ("..." or curly quotes) in sections
1-5. Section 6, the Suggested Reachy Prompts, is left out: those are proposals,
not quotes. "exact" means the quote appears word for word, ignoring case and
punctuation. Anything else gets the closest turn in the transcript, with its
speaker, so it can be judged as reworded or not there. Writes quotes_auto.tsv.
"""

import re
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


rows = ["transcript_id\tquote\tauto_match\tspeaker\tclosest_turn\tsimilarity"]
for plan_path in sorted((HERE / "plans").glob("T*.txt")):
    tid = plan_path.stem
    plan = plan_path.read_text(encoding="utf-8")
    plan = re.split(r"(?im)^.*suggested reachy prompts.*$", plan)[0]
    transcript = (HERE / "transcripts" / plan_path.name).read_text(encoding="utf-8")
    parts = re.split(r"\b(Therapist|Child)\.\s*", transcript)
    turns = [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]
    for quote in re.findall(r"[\"“]([^\"”]{2,200})[\"”]", plan):
        q = norm(quote)
        exact = [(s, t) for s, t in turns if q and q in norm(t)]
        if exact:
            speakers = "/".join(sorted({s for s, _ in exact}))
            rows.append(f"{tid}\t{quote}\texact\t{speakers}\t{exact[0][1]}\t1.00")
            continue
        best = max(turns, key=lambda st: SequenceMatcher(None, q, norm(st[1])).ratio())
        ratio = SequenceMatcher(None, q, norm(best[1])).ratio()
        rows.append(f"{tid}\t{quote}\tcheck\t{best[0]}\t{best[1]}\t{ratio:.2f}")

(HERE / "quotes_auto.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
print("\n".join(rows))
