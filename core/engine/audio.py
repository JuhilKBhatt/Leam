# ./utilities/tts_generator.py

import json
import random
import re
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
    """Returns a TTS client using OAuth credentials."""
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
        
        data['settings']['Reddit_TTS_USAGE-integerNS'] = new_usage
        data['settings']['Reddit_TTS_Month-stringNS'] = current_month
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error updating config usage: {e}")

def chunk_text(text: str, max_chars: int = 600) -> list[str]:
    """
    Splits text into chunks respecting sentence boundaries to avoid 
    Google TTS 'Sentence too long' errors.
    """
    # Split by sentence endings (. ? ! or newlines)
    # The regex keeps the punctuation with the sentence
    sentences = re.split(r'(?<=[.?!])\s+|\n+', text)
    
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if not sentence.strip():
            continue
            
        # If adding this sentence exceeds max_chars, push current_chunk and start new
        if len(current_chunk) + len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence

    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def generate_tts(text: str, output_file: Path, TTS_VOICES: list, TTS_CHARACTER_LIMIT: int, config_path: Path) -> Path:
    """
    Generate TTS using Google's Chirp 3 models.
    Handles Usage logic and Chunks text to avoid API errors.
    """
    
    # 1. Load current usage
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        settings = config_data.get('settings', {})
    
    used = settings.get("Reddit_TTS_USAGE-integerNS", 0)
    saved_month = settings.get("Reddit_TTS_Month-stringNS", "")
    current_month = datetime.now().strftime("%Y-%m")
    
    # Safety fallback for limit if None
    if TTS_CHARACTER_LIMIT is None:
        TTS_CHARACTER_LIMIT = 150000

    if saved_month != current_month:
        print(f"New month detected ({current_month}). Resetting TTS usage.")
        used = 0

    text_len = len(text)

    # 2. Check Limits
    if used + text_len > TTS_CHARACTER_LIMIT:
        raise RuntimeError(
            f"❌ TTS request blocked.\n"
            f"Used this month: {used:,} chars\n"
            f"Request size: {text_len:,} chars\n"
            f"Monthly limit: {TTS_CHARACTER_LIMIT:,} chars"
        )

    # 3. Setup Client & Voice
    client = get_tts_client()
    
    if isinstance(TTS_VOICES, list) and len(TTS_VOICES) > 0:
        selected_voice = random.choice(TTS_VOICES).strip()
    else:
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

    # 4. Process Chunks (The Fix for "Sentence too long")
    chunks = chunk_text(text, max_chars=800)
    combined_audio = b""
    
    print(f"Generating voiceover in {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
            
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        
        try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            combined_audio += response.audio_content
        except Exception as e:
            print(f"⚠️ Error generating chunk {i+1}: {e}")
            raise e

    # 5. Save and Update
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(combined_audio)

    new_usage = used + text_len
    update_json_usage(config_path, new_usage, current_month)

    print(f"TTS generated → {output_file}")
    print(f"Characters consumed: {text_len:,}")
    return output_file