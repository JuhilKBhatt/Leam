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
from core.utils.common import get_now

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
OAUTH_SECRETS = Path("secrets/client_secrets.json")
OAUTH_TOKEN = Path("secrets/tts_token.pickle")
TTS_AUTH_CODE_FILE = Path("secrets/tts_auth_code.txt")
TTS_AUTH_URL_FILE = Path("secrets/tts_auth_url.txt")

def is_tts_authenticated() -> bool:
    """Checks whether valid or refreshable TTS credentials exist."""
    if not OAUTH_TOKEN.exists():
        return False
    try:
        with open(OAUTH_TOKEN, "rb") as f:
            creds = pickle.load(f)
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            return True
    except Exception:
        return False
    return False

def start_tts_auth() -> Credentials:
    """
    Executes the out-of-band OAuth flow for TTS:
    Generates authorization URL, writes to secrets/tts_auth_url.txt,
    polls secrets/tts_auth_code.txt for verification code, exchanges it,
    and stores credentials in secrets/tts_token.pickle.
    """
    import time
    if not OAUTH_SECRETS.exists():
        raise FileNotFoundError(f"Missing Google client secrets at {OAUTH_SECRETS}")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_SECRETS), SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob"
    )
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )

    with open(TTS_AUTH_URL_FILE, "w") as f:
        f.write(auth_url)

    print("=" * 60)
    print("🔐 GOOGLE CLOUD TTS AUTHENTICATION REQUIRED")
    print("=" * 60)
    print("1. Open this URL on ANY device:\n")
    print(f"   {auth_url}\n")
    print("2. Sign in and grant Text-to-Speech / Cloud Platform access.")
    print("3. Copy the authorization code shown on screen.")
    print(f"4. Paste it into {TTS_AUTH_CODE_FILE} or submit via Settings UI.")
    print("=" * 60)
    print(f"⏳ Waiting for auth code in {TTS_AUTH_CODE_FILE} ...")

    if TTS_AUTH_CODE_FILE.exists():
        try:
            TTS_AUTH_CODE_FILE.unlink()
        except Exception:
            pass

    code = None
    for _ in range(200):  # Wait up to 10 minutes (200 * 3s)
        time.sleep(3)
        if TTS_AUTH_CODE_FILE.exists():
            try:
                with open(TTS_AUTH_CODE_FILE, "r") as f:
                    code = f.read().strip()
            except Exception:
                code = None
            if code:
                print("✅ TTS Auth code received! Exchanging for token...")
                break

    if not code:
        raise TimeoutError("TTS authentication timed out waiting for auth code.")

    flow.fetch_token(code=code)
    creds = flow.credentials

    if TTS_AUTH_CODE_FILE.exists():
        try:
            TTS_AUTH_CODE_FILE.unlink()
        except Exception:
            pass

    if TTS_AUTH_URL_FILE.exists():
        try:
            TTS_AUTH_URL_FILE.unlink()
        except Exception:
            pass

    with open(OAUTH_TOKEN, "wb") as f:
        pickle.dump(creds, f)

    print("🎉 TTS authentication completed successfully!")
    return creds

def get_tts_client() -> texttospeech.TextToSpeechClient:
    """Returns a TTS client using OAuth credentials."""
    creds = None
    if OAUTH_TOKEN.exists():
        try:
            with open(OAUTH_TOKEN, "rb") as f:
                creds = pickle.load(f)
        except Exception:
            creds = None

    # If no valid credentials, try to refresh or log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired TTS token...")
                creds.refresh(Request())
                with open(OAUTH_TOKEN, "wb") as f:
                    pickle.dump(creds, f)
            except Exception:
                print("❌ TTS Token refresh failed. Re-authenticating...")
                creds = None

        if not creds:
            creds = start_tts_auth()

    return texttospeech.TextToSpeechClient(credentials=creds)

TTS_QUOTA_FILE = Path("data/tts_quota.json")

def load_tts_quota_data() -> dict:
    if not TTS_QUOTA_FILE.exists():
        return {}
    try:
        with open(TTS_QUOTA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_tts_quota_data(data: dict):
    try:
        TTS_QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TTS_QUOTA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[TTS] Warning: Could not save TTS quota data: {e}")

def get_tts_quota_status() -> dict:
    """
    Returns the global and per-module TTS quota tracking data.
    Automatically resets monthly usage if the calendar month has changed.
    Limits are read directly from data/tts_quota.json.
    """
    current_month = get_now().strftime("%Y-%m")
    quota_data = load_tts_quota_data()
    global_limit = quota_data["limit"]

    modules_dir = Path("modules")
    discovered_modules = [d.name for d in modules_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))] if modules_dir.exists() else []

    needs_save = False
    stored_month = quota_data.get("month")

    if stored_month != current_month:
        modules_usage = {mod: 0 for mod in discovered_modules}
        quota_data = {
            "month": current_month,
            "limit": global_limit,
            "total_used": 0,
            "remaining": global_limit,
            "percent_used": 0.0,
            "modules": modules_usage,
            "last_updated": get_now().isoformat()
        }
        needs_save = True
    else:
        modules_usage = quota_data.get("modules", {})
        for mod in discovered_modules:
            if mod not in modules_usage:
                modules_usage[mod] = 0
                needs_save = True

        total_used = sum(modules_usage.values())
        quota_data["total_used"] = total_used
        quota_data["remaining"] = max(0, global_limit - total_used)
        quota_data["percent_used"] = round((total_used / global_limit) * 100, 2) if global_limit > 0 else 0
        quota_data["modules"] = modules_usage

    if needs_save:
        save_tts_quota_data(quota_data)

    return quota_data

def record_tts_usage(module_name: str, char_count: int):
    """
    Records TTS character usage for a specific module and updates the global total.
    """
    quota_status = get_tts_quota_status()
    global_limit = quota_status["limit"]
    modules_usage = quota_status.setdefault("modules", {})
    modules_usage[module_name] = modules_usage.get(module_name, 0) + char_count

    total_used = sum(modules_usage.values())
    quota_status["total_used"] = total_used
    quota_status["remaining"] = max(0, global_limit - total_used)
    quota_status["percent_used"] = round((total_used / global_limit) * 100, 2) if global_limit > 0 else 0
    quota_status["last_updated"] = get_now().isoformat()

    save_tts_quota_data(quota_status)

def update_json_usage(config_path: Path, new_usage: int, current_month: str):
    """Updates the JSON configuration file with new usage stats in module.local.json."""
    from core.utils.common import load_module_config, save_module_config
    try:
        module_dir = config_path.parent
        data = load_module_config(module_dir)
        settings = data.setdefault('settings', {})
        
        usage_key = next((k for k in settings if k.endswith("_TTS_USAGE-integerNS")), None)
        month_key = next((k for k in settings if k.endswith("_TTS_Month-stringNS")), None)
        
        if usage_key and month_key:
            settings[usage_key] = new_usage
            settings[month_key] = current_month
            save_module_config(module_dir, data)
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
    module_name = config_path.parent.name if config_path else "unknown"
    text_len = len(text)

    if text_len == 0:
        raise ValueError("TTS text is empty.")

    # 1. Check Global Quota Limit
    quota_status = get_tts_quota_status()
    global_limit = quota_status["limit"]
    total_used = quota_status.get("total_used", 0)
    remaining_global = max(0, global_limit - total_used)

    if total_used + text_len > global_limit:
        raise RuntimeError(
            f"❌ Global TTS character quota exceeded ({global_limit:,} chars/month).\n"
            f"Used this month: {total_used:,} chars\n"
            f"Request size: {text_len:,} chars\n"
            f"Remaining: {remaining_global:,} chars"
        )

    # 2. Check Module-level Limit (if set)
    from core.utils.common import load_module_config
    module_dir = config_path.parent
    config_data = load_module_config(module_dir)
    settings = config_data.get('settings', {})
    
    usage_key = next((k for k in settings if k.endswith("_TTS_USAGE-integerNS")), "TTS_USAGE-integerNS")
    month_key = next((k for k in settings if k.endswith("_TTS_Month-stringNS")), "TTS_Month-stringNS")
    
    used = settings.get(usage_key, 0)
    saved_month = settings.get(month_key, "")
    current_month = get_now().strftime("%Y-%m")

    if saved_month != current_month:
        used = 0

    if TTS_CHARACTER_LIMIT and (used + text_len > TTS_CHARACTER_LIMIT):
        raise RuntimeError(
            f"❌ Module TTS request blocked ({module_name}).\n"
            f"Module used this month: {used:,} chars\n"
            f"Request size: {text_len:,} chars\n"
            f"Module limit: {TTS_CHARACTER_LIMIT:,} chars"
        )

    # 3. Setup Client & Voice
    client = get_tts_client()
    
    if isinstance(TTS_VOICES, list) and len(TTS_VOICES) > 0:
        selected_voice = random.choice(TTS_VOICES).strip()
    else:
        selected_voice = "en-US-Chirp3-HD-Aoede"
        
    print(f"🎙️ Selected Voice: {selected_voice}")

    ext = output_file.suffix.lower()
    if ext not in [".mp3", ".wav"]:
        ext = ".mp3"
        output_file = output_file.with_suffix(".mp3")

    # If the voice name already contains the full identifier (region-model-HD-name), use it directly.
    # Otherwise, assume it's just the name and default to en-US Chirp3.
    if "-" in selected_voice:
        voice_name = selected_voice
    else:
        voice_name = f"en-US-Chirp3-HD-{selected_voice}"

    # Extract language code from voice name if possible
    lang_code = "en-US"
    if "-" in voice_name:
        parts = voice_name.split("-")
        if len(parts) >= 2:
            lang_code = f"{parts[0]}-{parts[1]}"

    voice = texttospeech.VoiceSelectionParams(
        language_code=lang_code,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )

    # 4. Process Chunks (The Fix for "Sentence too long" AND Audio Drift)
    chunks = chunk_text(text, max_chars=800)
    
    print(f"Generating voiceover in {len(chunks)} chunks...")
    
    import subprocess
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True)
    temp_files = []

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
            
            # Save as temporary WAV to avoid MP3 padding issues
            chunk_file = temp_dir / f"chunk_{i}.wav"
            with open(chunk_file, "wb") as f:
                f.write(response.audio_content)
                
            temp_files.append(chunk_file)
        except Exception as e:
            print(f"⚠️ Error generating chunk {i+1}: {e}")
            raise e

    # 5. Save and Update
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    if temp_files:
        concat_list = temp_dir / "concat_list.txt"
        with open(concat_list, "w") as f:
            for tf in temp_files:
                f.write(f"file '{tf.absolute()}'\n")
                
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:a", "libmp3lame", "-q:a", "2",
            str(output_file)
        ]
        subprocess.run(cmd, check=True)
        
        concat_list.unlink()
        for f in temp_files:
            try:
                f.unlink()
            except Exception:
                pass

    new_usage = used + text_len
    update_json_usage(config_path, new_usage, current_month)
    record_tts_usage(module_name, text_len)

    updated_status = get_tts_quota_status()
    active_limit = updated_status["limit"]
    print(f"TTS generated → {output_file}")
    print(f"Characters consumed: {text_len:,} (Module '{module_name}': {new_usage:,} | Global: {updated_status.get('total_used', 0):,}/{active_limit:,} [{updated_status.get('percent_used', 0)}%])")
    return output_file