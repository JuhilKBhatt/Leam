# ./utilities/comment_generator.py
from utilities.gpt_handler import gpt_request

def generate_video_comment(transcript: str) -> str:
    """Generate a GPT-powered intelligent comment about the video."""
    prompt = f"""
You are writing a natural YouTube comment for a video.

• Write in a casual, human tone (not robotic).
• Sound like an actual person commenting, not AI.
• DO NOT use bullet points, dashes, lists, or any kind of item formatting.
• Mention the main idea or vibe of the transcript.
• Keep it positive or appreciative.
• Maximum: 1 to 2 short sentences.
• No hashtags or emojis unless they fit naturally.

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

def generate_reply_comment(top_comment: str, transcript: str) -> str:
    """Generate a GPT-based reply to a viewer's comment."""
    prompt = f"""
Write a friendly, human sounding reply to a YouTube comment. 
This is the transcript: "{transcript}"

• Keep the tone warm, conversational, and respectful.
• Sound like an actual person replying, not AI.
• DO NOT use bullet points, dashes, lists, or any kind of item formatting.
• Add a tiny bit of personality, but stay brief.
• Limit reply to 1 to 2 short sentences.

Viewer commented: "{top_comment}"
"""

    try:
        reply = gpt_request(prompt)
        if reply:
            return reply.strip()
    except:
        pass

    # fallback
    return f"Thanks for the comment! Really appreciate your thoughts: '{top_comment}'"