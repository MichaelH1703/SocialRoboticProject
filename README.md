# Reachy Voice Code

A Reachy Mini robot that helps children practise telling the story of their day,
with dashboards for the therapist and parents.

Built on [huggingface/speech-to-speech](https://github.com/huggingface/speech-to-speech) (Apache-2.0, see `LICENSE`).

## What each file does

| File | What it does |
|---|---|
| `test_reachy_conversation.py` | Starts the speech server (listening, speech-to-text, AI reply, text-to-speech). |
| `reachy_s2s_conversation.py` | The main robot conversation. Connects Reachy to the server and saves the session. |
| `reachy_wake_up.py` | Wakes the robot up and checks it is ready. Run it before a session. |
| `reachy_text_chat.py` | Typing version of the conversation, for testing without the robot. |
| `reachy_safety.py` | Safety rules that check what the child says and what Reachy replies. |
| `test_safety_rules.py` | Tests the safety rules. |
| `therapist_dashboard.py` | Website for the therapist: clients, conversation logs, lesson plans. |
| `parental_dashboard.py` | Website for parents to see their child's progress. |
| `lesson_planner_v3.py` | Makes lesson plans from a conversation (used by the therapist dashboard). |
| `lesson_planner.py`, `lesson_planner_v2.py` | Older lesson planners, kept for the evaluation. |
| `*.sql` | Database setup for Supabase. |
| `eval/`, `evaluation/` | Evaluation tests and results. |
| `src/` | The speech-to-speech server code from Hugging Face. |

## Setup

1. Make two Python environments:

   ```
   python -m venv venv
   venv\Scripts\pip install -e .

   python -m venv venv-client
   venv-client\Scripts\pip install -r requirements.txt
   ```

2. Install [Ollama](https://ollama.com) and get the model:

   ```
   ollama pull qwen2.5:3b
   ```

3. Start Supabase and run the SQL files, in this order:
   `schema.sql`, `roles.sql`, `storage_policies.sql`, `participants_migration.sql`,
   `safety_events.sql`, `conversation_logs_sessions.sql`.

4. Copy `.env.example` to `.env` and fill it in.
   Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill it in.

## How to run

Each command goes in its own terminal.

**Robot conversation**

```
ollama run qwen2.5:3b
venv\Scripts\python.exe test_reachy_conversation.py
venv-client\Scripts\python.exe reachy_wake_up.py
venv-client\Scripts\python.exe reachy_s2s_conversation.py
```

**Typing test (no robot)**

```
ollama run qwen2.5:3b
venv\Scripts\python.exe reachy_text_chat.py
```

**Dashboards**

```
venv-client\Scripts\streamlit run therapist_dashboard.py
venv-client\Scripts\streamlit run parental_dashboard.py
```

**Safety tests**

```
venv\Scripts\python.exe test_safety_rules.py
```
