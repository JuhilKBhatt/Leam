# ./utilities/tts_generator.py

import os
from pathlib import Path
import pickle
from google.cloud import texttospeech
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv, set_key
from datetime import datetime

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
OAUTH_SECRETS = Path("secrets/client_secrets.json")
OAUTH_TOKEN = Path("secrets/tts_token.pickle")
ENV_FILE = ".env"
MONTHLY_LIMIT = int(os.getenv("TTS_CHARACTER_LIMIT"))

# TTS character limit and reset date from environment variables
def load_usage():
    # Get stored values or defaults
    used = int(os.getenv("TTS_USAGE"))
    saved_month = os.getenv("TTS_MONTH")

    current_month = datetime.now().strftime("%Y-%m")

    # Reset usage if a new month started
    if saved_month != current_month:
        used = 0
        set_key(ENV_FILE, "TTS_USAGE", "0")
        set_key(ENV_FILE, "TTS_MONTH", current_month)

    return used, current_month

def update_usage(new_value):
    """Update usage in .env"""
    set_key(ENV_FILE, "TTS_USAGE", str(new_value))

def get_tts_client() -> texttospeech.TextToSpeechClient:
    """
    Returns a TTS client using OAuth credentials from client_secrets.json.
    Saves a pickle token for future use.
    """
    creds = None

    # Load saved token
    if OAUTH_TOKEN.exists():
        with open(OAUTH_TOKEN, "rb") as f:
            creds = pickle.load(f)

    # If token invalid or missing, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(OAUTH_SECRETS), SCOPES
            )
            creds = flow.run_local_server(port=8080)

        # Save token for next time
        with open(OAUTH_TOKEN, "wb") as f:
            pickle.dump(creds, f)

    return texttospeech.TextToSpeechClient(credentials=creds)

def generate_tts(text: str, output_file: Path) -> Path:
    """
    Generate TTS using Google's Chirp 3 models.
    Output format automatically determined by file extension.
    """

    # Load and validate usage
    used, month = load_usage()
    text_len = len(text)

    if used + text_len > MONTHLY_LIMIT:
        raise RuntimeError(
            f"❌ TTS request blocked.\n"
            f"Used this month: {used:,} chars\n"
            f"Request size: {text_len:,} chars\n"
            f"Monthly limit: {MONTHLY_LIMIT:,} chars\n\n"
            f"Wait until next month or upgrade Google quota."
        )

    client = get_tts_client()

    # Detect MP3 or WAV from file extension
    ext = output_file.suffix.lower()
    if ext not in [".mp3", ".wav"]:
        ext = ".mp3"
        output_file = output_file.with_suffix(".mp3")

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Chirp3-HD-Achernar",
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=(
            texttospeech.AudioEncoding.MP3 if ext == ".mp3"
            else texttospeech.AudioEncoding.LINEAR16
        )
    )

    synthesis_input = texttospeech.SynthesisInput(text=text)

    print("Generating voiceover using Google Chirp 3...")

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # Ensure output folder exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write audio file
    with open(output_file, "wb") as f:
        f.write(response.audio_content)

    # Update usage
    new_usage = used + text_len
    update_usage(new_usage)

    print(f"TTS generated → {output_file}")
    print(f"Characters consumed: {text_len:,}")
    print(f"Total used this month: {new_usage:,} / {MONTHLY_LIMIT:,}")
    return output_file