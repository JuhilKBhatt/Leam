# ./utilities/gpt_handler.py

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

def format_story_with_gpt(ai_input: str) -> str:
    """Send story text to GPT for conversational narration formatting."""
    prompt = f"""
    {ai_input}
    """

    response = client.responses.create(
        input=[{"role": "user", "content": prompt}],
        model="openai/gpt-oss-120b",
    )

    return response.choices[0].message.content.strip()