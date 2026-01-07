# ./utilities/safe_filename.py

def safe_filename(text: str, max_length: int = 50) -> str:
    # Remove bad filename characters and shorten
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in text)[:max_length]