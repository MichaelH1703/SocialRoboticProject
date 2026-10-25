"""A simulated child for evaluation runs, who answers what Reachy actually asked.

Fixed scripts made the conversations incoherent: the child's next line ignored
Reachy's question, so replies were being judged against non-sequiturs. Here a
separate local model plays the child. It sees only what Reachy said and a fact
sheet about the day. It is never shown the client's profile, notes or lesson
plan, or which condition a session belongs to, so it cannot tell the conditions
apart except through Reachy's own words.

Every candidate line is passed to a `reject` check supplied by the caller
(the robot's own safety and goodbye rules, length, banned topics). Rejected
lines are regenerated with the next seed, so a run is reproducible from its
seed.
"""

import json
import re
import urllib.request
from typing import Callable, List, Optional, Tuple

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"


def clean(text: str) -> str:
    """First line only, without speaker labels, quotes, stage directions or emoji."""
    line = text.strip().splitlines()[0] if text.strip() else ""
    line = re.sub(r"^\s*(?:april|child|me)\s*:\s*", "", line, flags=re.I)
    line = re.sub(r"\*[^*]*\*|\([^)]*\)", "", line)
    line = line.strip().strip('"“”').strip()
    line = re.sub(r"[^\x20-\x7E’‘]", "", line)
    return re.sub(r"\s+", " ", line).strip()


class SimulatedChild:
    def __init__(self, system_prompt: str, model: str, seed: int, temperature: float,
                 fallback: str, max_attempts: int = 6) -> None:
        self.model = model
        self.seed = seed
        self.temperature = temperature
        self.fallback = fallback
        self.max_attempts = max_attempts
        self.messages: List[dict] = [{"role": "system", "content": system_prompt}]

    def hear(self, text: str) -> None:
        """Something Reachy said aloud. Consecutive lines are joined into one turn."""
        if not text:
            return
        if self.messages[-1]["role"] == "user":
            self.messages[-1]["content"] += " " + text
        else:
            self.messages.append({"role": "user", "content": text})

    def say(self, text: str) -> None:
        """Record a line the child said, generated or fixed (opening, "I don't know", goodbye)."""
        self.messages.append({"role": "assistant", "content": text})

    def _generate(self, seed: int) -> str:
        body = {
            "model": self.model,
            "messages": self.messages,
            "stream": False,
            "options": {"temperature": self.temperature, "seed": seed, "num_predict": 40},
        }
        request = urllib.request.Request(
            OLLAMA_CHAT_URL, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120) as resp:
            return json.load(resp)["message"]["content"]

    def respond(self, turn: int, reject: Callable[[str], Optional[str]]) -> Tuple[str, List[str]]:
        """The child's next line, and a note for every rejected attempt."""
        notes = []
        for attempt in range(self.max_attempts):
            raw = self._generate(self.seed * 1000 + turn * 10 + attempt)
            line = clean(raw)
            problem = reject(line)
            if problem is None:
                self.say(line)
                return line, notes
            notes.append(f"attempt {attempt + 1} rejected ({problem}): {raw.strip()!r}")
        notes.append(f"all attempts rejected; used fallback {self.fallback!r}")
        self.say(self.fallback)
        return self.fallback, notes
