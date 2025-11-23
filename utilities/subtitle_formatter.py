# ./utilities/subtitle_formatter.py

import re
import unicodedata

def clean_subtitle_text(text: str) -> str:
    """
    Cleans TTS / Reddit text for subtitles.
    - Removes null characters (\x00)
    - Removes weird control characters
    - Normalizes Unicode
    - Collapses excessive whitespace
    - Fixes Reddit formatting leftovers
    """

    if not isinstance(text, str):
        return ""

    # Normalize to fix strange unicode encodings
    text = unicodedata.normalize("NFKC", text)

    # Remove null bytes and invisible control chars
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Remove weird zero-width chars
    text = re.sub(r"[\u200B-\u200F\uFEFF]", "", text)

    # Replace multiple newlines with one
    text = re.sub(r"\n{2,}", "\n", text)

    # Replace multiple spaces with one
    text = re.sub(r"[ ]{2,}", " ", text)

    # Strip common Reddit formatting symbols
    text = text.replace("&nbsp;", " ")
    text = text.replace("*", "")
    text = text.replace("•", "-")

    # Trim leading/trailing whitespace
    text = text.strip()

    return text


def format_for_subtitles(text: str, max_length: int = 20000) -> str:
    """
    Final formatting step:
    - Clean text
    - Enforce max length so TTS doesn’t explode
    - Ensure no empty output
    """
    text = clean_subtitle_text(text)

    # Safety length cap
    if len(text) > max_length:
        text = text[:max_length] + "…"

    # Guarantee something is returned
    return text if text else " "  # prevents MoviePy crash