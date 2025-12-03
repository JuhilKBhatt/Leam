def generate_video_comment(transcript: str) -> str:
    """Generate a comment summarizing the video."""
    if len(transcript) > 400:
        summary = transcript[:400] + "..."
    else:
        summary = transcript

    return "Great video! Here's what I found interesting: " + summary


def generate_reply_comment(top_comment: str) -> str:
    """Generate a reply to someone’s comment."""
    return f"Interesting point! I agree with your insight: '{top_comment}'"