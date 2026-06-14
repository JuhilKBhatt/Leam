# modules/youtube_commenter/comment_generator.py
from core.api.llm import gpt_request

def generate_video_comment(transcript: str, prompt_template: str) -> str:
    """Generate a GPT-powered intelligent comment about the video using a template."""
    prompt = prompt_template.format(transcript=transcript)

    try:
        reply = gpt_request(prompt)
        if reply:
            return reply.strip()
    except:
        pass

    # fallback
    short = transcript[:300] + "..."
    return f"Great video! Key takeaway: {short}"

def generate_reply_comment(top_comment: str, transcript: str, prompt_template: str) -> str:
    """Generate a GPT-based reply to a viewer's comment using a template."""
    prompt = prompt_template.format(transcript=transcript, top_comment=top_comment)

    try:
        reply = gpt_request(prompt)
        if reply:
            return reply.strip()
    except:
        pass

    # fallback
    return f"Thanks for the comment! Really appreciate your thoughts: '{top_comment}'"
