# ./utilities/comment_generator.py
from utilities.gpt_handler import gpt_request

def generate_video_comment(transcript: str) -> str:
    """Generate a GPT-powered intelligent comment about the video."""
    prompt = f"""
You are generating a YouTube comment about a video. 
Summarize the transcript in a natural, casual, positive tone. 
Keep it under 2 short sentences.

Transcript:
{transcript}
"""

    try:
        reply = gpt_request(prompt)
        if reply:
            return reply.strip()
    except:
        pass

    # fallback
    short = transcript[:300] + "..."
    return f"Great video! Key takeaway: {short}"

def generate_reply_comment(top_comment: str) -> str:
    """Generate a GPT-based reply to a viewer's comment."""
    prompt = f"""
Write a friendly, thoughtful reply to this YouTube comment:

Comment: "{top_comment}"

Keep it conversational, respectful, short (1–2 sentences).
"""

    try:
        reply = gpt_request(prompt)
        if reply:
            return reply.strip()
    except:
        pass

    # fallback
    return f"Interesting point! Thanks for sharing your thoughts: '{top_comment}'"