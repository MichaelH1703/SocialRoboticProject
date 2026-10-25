import requests


def build_lesson_plan_prompt(transcript: str) -> str:
    return f"""
You are assisting a speech therapist by analysing a child’s spoken interaction.
Your output will also be used to guide a socially assistive robot (Reachy) in future sessions.

A child has described part of their day. Based on the transcript, analyse the child's communication and suggest what future lessons and interactions should focus on.

Transcript:
{transcript}

Return your answer in the following structure:

1. Narrative Summary
2. Communication Strengths
3. Communication Gaps
4. Emotional Understanding
5. Recommended Future Lesson Focus
6. Suggested Reachy Prompts (simple, natural, child-friendly)

Be specific, practical, and concise. Ensure suggestions are appropriate for guiding both therapist-led sessions and robot interactions.
"""


def generate_lesson_plan_from_transcript(transcript: str, model: str = "qwen2.5:3b") -> str:
    prompt = build_lesson_plan_prompt(transcript)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )
    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()