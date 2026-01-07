# ./utilities/tts_generator.py

import json
import random
from pathlib import Path
import pickle
from google.cloud import texttospeech
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
OAUTH_SECRETS = Path("secrets/client_secrets.json")
OAUTH_TOKEN = Path("secrets/tts_token.pickle")

def get_tts_client() -> texttospeech.TextToSpeechClient:
    """
    Returns a TTS client using OAuth credentials from client_secrets.json.
    """
    creds = None
    if OAUTH_TOKEN.exists():
        with open(OAUTH_TOKEN, "rb") as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(OAUTH_SECRETS), SCOPES
            )
            creds = flow.run_local_server(port=8080)
        with open(OAUTH_TOKEN, "wb") as f:
            pickle.dump(creds, f)

    return texttospeech.TextToSpeechClient(credentials=creds)

def update_json_usage(config_path: Path, new_usage: int, current_month: str):
    """Updates the JSON configuration file with new usage stats."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Update settings
        data['settings']['Reddit_TTS_USAGE-integerNS'] = new_usage
        data['settings']['Reddit_TTS_Month-stringNS'] = current_month
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error updating config usage: {e}")

def generate_tts(text: str, output_file: Path, TTS_VOICES: list, TTS_CHARACTER_LIMIT: int, config_path: Path) -> Path:
    """
    Generate TTS using Google's Chirp 3 models.
    Handles Usage logic via module.json.
    Randomly selects a voice from the provided list.
    """
    
    # 1. Load current usage from JSON
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        settings = config_data.get('settings', {})
    
    used = settings.get("Reddit_TTS_USAGE-integerNS", 0)
    saved_month = settings.get("Reddit_TTS_Month-stringNS", "")
    current_month = datetime.now().strftime("%Y-%m")
    
    # 2. Reset usage if a new month started
    if saved_month != current_month:
        print(f"New month detected ({current_month}). Resetting TTS usage.")
        used = 0

    text_len = len(text)

    # 3. Check Limits
    if used + text_len > TTS_CHARACTER_LIMIT:
        raise RuntimeError(
            f"❌ TTS request blocked.\n"
            f"Used this month: {used:,} chars\n"
            f"Request size: {text_len:,} chars\n"
            f"Monthly limit: {TTS_CHARACTER_LIMIT:,} chars\n\n"
            f"Wait until next month or upgrade Google quota."
        )

    # 4. Generate Audio
    client = get_tts_client()
    
    # Randomly select a voice
    if isinstance(TTS_VOICES, list) and len(TTS_VOICES) > 0:
        selected_voice = random.choice(TTS_VOICES).strip()
    else:
        # Fallback if list is empty or invalid
        selected_voice = "Rachel" 
        
    print(f"🎙️ Selected Voice: {selected_voice}")

    ext = output_file.suffix.lower()
    if ext not in [".mp3", ".wav"]:
        ext = ".mp3"
        output_file = output_file.with_suffix(".mp3")

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-AU",
        name=f"en-AU-Chirp3-HD-{selected_voice}",
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

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(response.audio_content)

    # 5. Update Usage in JSON
    new_usage = used + text_len
    update_json_usage(config_path, new_usage, current_month)

    print(f"TTS generated → {output_file}")
    print(f"Characters consumed: {text_len:,}")
    print(f"Total used this month: {new_usage:,} / {TTS_CHARACTER_LIMIT:,}")
    return output_file