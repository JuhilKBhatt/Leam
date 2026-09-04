import os
import sys
import json
import random
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path so we can import core
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from core.utils.common import load_module_config
from core.api.llm import gpt_request
from core.api.serpapi import get_google_image_from_serpapi

MODULE_DIR = Path(__file__).parent
DATA_DIR = MODULE_DIR / "output"
LOG_DIR = MODULE_DIR / "logs"

def parse_price_range(price_range_str):
    """Parses a price range string like '100-1000', '1000,500,250', or '500' and returns a random price."""
    try:
        if '-' in price_range_str:
            parts = price_range_str.split('-')
            min_p = float(parts[0].strip())
            max_p = float(parts[1].strip())
            return round(random.uniform(min_p, max_p), 2)
        elif ',' in price_range_str:
            parts = price_range_str.split(',')
            choices = [float(p.strip()) for p in parts if p.strip()]
            return float(random.choice(choices))
        else:
            return float(price_range_str.strip())
    except Exception as e:
        print(f"Error parsing price range '{price_range_str}': {e}. Defaulting to 1000.")
        return 1000.0

def get_random_company():
    """Picks a random company from the local sp500.json file."""
    sp500_file = project_root / "data" / "sp500.json"
    if not sp500_file.exists():
        print("sp500.json not found, falling back to Apple (AAPL)")
        return {"name": "Apple Inc.", "ticker": "AAPL"}
        
    with open(sp500_file, 'r') as f:
        companies = json.load(f)
    return random.choice(companies)

def fetch_stock_data(ticker, years_back):
    """Fetches historical stock data using yfinance."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365)
    
    print(f"Fetching data for {ticker} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({years_back} years)...")
    
    stock = yf.Ticker(ticker)
    # Explicitly use auto_adjust=True to guarantee dividend reinvestment and split adjustments
    hist = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), auto_adjust=True)
    return hist

def run():
    print("Starting stock timeline generation...")
    # 1. Load Config
    config = load_module_config(MODULE_DIR)
    settings = config.get("settings", {})
    
    # 2. Pick a random price from PRICE RANGE
    # Trying the configured Price_Range, if empty fallback to Initial_Investment or default
    price_range_str = settings.get("Price_Range-stringME", "")
    if not price_range_str:
        # Fallback to older settings format if Price_Range isn't set
        price_range_str = str(settings.get("Initial_Investment-integerFE", "100-1000"))
        
    initial_investment = parse_price_range(price_range_str)
    print(f"Selected Initial Investment: ${initial_investment:.2f}")

    # 3. Pick a random company and get valid stock market data (retry if delisted)
    max_retries = 5
    hist = None
    
    for attempt in range(max_retries):
        company = get_random_company()
        ticker = company["ticker"]
        company_name = company["name"]
        print(f"Attempt {attempt+1}: Selected Company: {company_name} ({ticker})")

        # 4. Get stock market data for 5 to 10 years
        years_back = random.randint(5, 10)
        hist = fetch_stock_data(ticker, years_back)
        
        if not hist.empty:
            break
        print(f"No historical data found for {ticker} (might be delisted). Retrying...")

    if hist is None or hist.empty:
        print("Failed to find historical data after multiple attempts. Exiting.")
        return

    first_price = hist['Close'].iloc[0]
    last_price = hist['Close'].iloc[-1]
    
    # Calculate gain/loss
    shares_bought = initial_investment / first_price
    final_value = shares_bought * last_price
    gain = final_value - initial_investment  # Actual profit or loss
    
    print(f"Initial Price: ${first_price:.2f}, Final Price: ${last_price:.2f}")
    print(f"Final Value: ${final_value:.2f}, Gain: ${gain:.2f}")

    # 5. Ask AI what people can buy with the initial investment
    prompt_product_template = settings.get("prompt_product-stringLE")
    if not prompt_product_template:
        prompt_product_template = "What is a popular consumer product, technology, or luxury item that someone could buy for exactly ${price}? Just name one specific product only. Do not give a long response or a description."
    prompt_product = prompt_product_template.replace("{price}", f"{initial_investment:.2f}")

    print("Asking AI for an equivalent product for the initial investment...")
    product_response = gpt_request(prompt_product).strip()
    print(f"Product for ${initial_investment:.2f}: {product_response}")

    # Download product image
    product_images_abs = get_google_image_from_serpapi(product_response, str(DATA_DIR), num_images=3)
    product_images_rel = [f"modules/stock_timeline/output/{Path(p).name}" for p in product_images_abs] if product_images_abs else []
    product_image_rel = product_images_rel[0] if product_images_rel else None

    # 6. Ask AI what people can buy with the final investment value
    if gain >= 0:
        prompt_gain_template = settings.get("prompt_gain-stringLE")
        if not prompt_gain_template:
            prompt_gain_template = "Someone's stock investment just grew to exactly ${price}. What is a luxury item, experience, or exciting thing they could buy with this exact amount? Just name one specific thing only. Do not give a long response or a description."
        prompt_gain = prompt_gain_template.replace("{price}", f"{final_value:.2f}")
        print("Asking AI for an equivalent purchase for the final value (gain)...")
    else:
        prompt_loss_template = settings.get("prompt_loss-stringLE")
        if not prompt_loss_template:
            prompt_loss_template = "Someone's stock investment just dropped to exactly ${price}. What is a smaller, cheaper item or experience they could buy with this exact amount? Just name one specific thing only. Do not give a long response or a description."
        prompt_gain = prompt_loss_template.replace("{price}", f"{final_value:.2f}")
        print("Asking AI for an equivalent purchase for the final value (loss)...")

    gain_response = gpt_request(prompt_gain).strip()
    print(f"What to buy with ${final_value:.2f} final value: {gain_response}")

    # Download gain image
    gain_images_abs = get_google_image_from_serpapi(gain_response, str(DATA_DIR), num_images=3)
    gain_images_rel = [f"modules/stock_timeline/output/{Path(p).name}" for p in gain_images_abs] if gain_images_abs else []
    gain_image_rel = gain_images_rel[0] if gain_images_rel else None

    # Extract historical prices for the chart
    prices = []
    for date, row in hist.iterrows():
        prices.append({
            "date": date.strftime('%Y-%m-%d'),
            "price": row['Close']
        })

    # 7. Ask AI to generate a script
    start_year = prices[0]["date"][:4]
    gain_or_loss_word = 'gain' if gain >= 0 else 'loss'
    
    default_script_prompt = "Write a short, engaging script for a video. Follow this exact structure: 'If you invested {initial_investment} into {company_name} in {start_year} instead of buying an {product_response}...'. Then, give a brief, real-world reason why {company_name} experienced a {gain_or_loss} over this period. End the script by saying that today, your investment would be worth {final_value}, which is enough to buy {gain_response}. Keep it conversational, punchy, and under 3-4 sentences total. Do not include any intro/outro text, just the script itself."
    
    script_prompt_template = settings.get("Stock_Timeline_AI_Script_Prompt-stringLE")
    if not script_prompt_template:
        script_prompt_template = default_script_prompt
        
    script_prompt = script_prompt_template.replace("{initial_investment}", f"${initial_investment:.2f}") \
                                          .replace("{company_name}", company_name) \
                                          .replace("{start_year}", start_year) \
                                          .replace("{product_response}", product_response) \
                                          .replace("{gain_or_loss}", gain_or_loss_word) \
                                          .replace("{final_value}", f"${final_value:.2f}") \
                                          .replace("{gain_response}", gain_response)

    print("Asking AI to generate the video script...")
    video_script = gpt_request(script_prompt).strip()
    print(f"Generated Script: {video_script}")

    # Generate Voiceover
    print("Generating voiceover audio...")
    from core.engine.audio import generate_tts
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    tts_output = DATA_DIR / f"{ticker}_{run_id}_voiceover.mp3"
    
    voices_list = ["Aoede", "Charon", "Fenrir", "Kore", "Leda", "Orus", "Puck", "Zephyr"]
    char_limit = settings.get("Stock_Timeline_TTS_Character_Limit-integerNE") or 150000
    generate_tts(video_script, tts_output, voices_list, char_limit, MODULE_DIR / "module.json")
    
    from mutagen.mp3 import MP3
    audio = MP3(str(tts_output))
    # Audio length determines the video duration
    durationInFrames = max(300, int((audio.info.length) * 30))
    
    print("Syncing audio timing with faster-whisper...")
    from faster_whisper import WhisperModel
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(tts_output), word_timestamps=True)
    
    words = []
    for segment in segments:
        for word in segment.words:
            words.append({"word": word.word.strip().lower(), "end": word.end})
    
    # Try to find logical split points
    part1_time = durationInFrames / 3 / 30
    part2_time = durationInFrames * 2 / 3 / 30
    
    # Phase 1 ends at 1.5 seconds max (45 frames) to hook the viewer instantly
    part1_time = 1.5
            
    # Phase 3 should start when the narrator introduces the final purchase.
    # The script says "...which is enough to buy {gain_response}."
    # So we trigger the transition at the word 'buy' or 'enough'.
    for w in reversed(words):
        if 'buy' in w['word'] or 'enough' in w['word']:
            part2_time = w['end'] - 0.5
            break
            
    part1EndFrame = int(part1_time * 30)
    part2EndFrame = int(part2_time * 30)
    
    # Ensure they are safely bounds checked so interpolate arrays are strictly increasing
    if part1EndFrame < 30: part1EndFrame = 30
    if part1EndFrame > durationInFrames - 90: part1EndFrame = int(durationInFrames / 3)
    
    if part2EndFrame <= part1EndFrame + 60: part2EndFrame = part1EndFrame + 60
    if part2EndFrame >= durationInFrames - 30: part2EndFrame = durationInFrames - 30
    
    # Pick Background Music
    music_dir = Path(__file__).parent.parent.parent / "media" / "audio" / "music"
    music_files = list(music_dir.glob("*.mp3"))
    bg_music_rel = None
    if music_files:
        chosen_music = random.choice(music_files)
        bg_music_rel = f"media/audio/music/{chosen_music.name}"

    # Use only the fade transition
    transition = "fade"

    # Save output for further processing (like video generation)
    summary = {
        "company": company_name,
        "ticker": ticker,
        "years": years_back,
        "initial_investment": initial_investment,
        "first_price": first_price,
        "last_price": last_price,
        "gain": gain,
        "initial_product_idea": product_response,
        "initial_product_image": product_image_rel,
        "initial_product_images": product_images_rel,
        "gain_purchase_idea": gain_response,
        "gain_purchase_image": gain_image_rel,
        "gain_purchase_images": gain_images_rel,
        "script": video_script,
        "voiceover_audio": f"modules/stock_timeline/output/{tts_output.name}",
        "durationInFrames": durationInFrames,
        "part1EndFrame": part1EndFrame,
        "part2EndFrame": part2EndFrame,
        "bg_music": bg_music_rel,
        "transition": transition,
        "prices": prices
    }
    
    os.makedirs(DATA_DIR, exist_ok=True)
    out_file = DATA_DIR / f"{ticker}_{run_id}.json"
    with open(out_file, 'w') as f:
        json.dump(summary, f, indent=4)
        
    print(f"Finished! JSON output saved to {out_file}")

    # 7. Render the video using Remotion
    import subprocess
    
    print("Triggering Remotion video render...")
    remotion_dir = project_root / "remotion"
    out_video = DATA_DIR / f"{ticker}_{run_id}.mp4"
    
    try:
        subprocess.run([
            "npx", "remotion", "render", "src/index.ts", "StockTimeline",
            str(out_video),
            f"--props={out_file}"
        ], cwd=remotion_dir, check=True)
        print(f"Video successfully rendered to: {out_video}")
        
        # --- YouTube Upload Section ---
        print("Generating YouTube metadata...")
        
        prompt = f"""
You are generating metadata for a YouTube Shorts video about a hypothetical stock market investment timeline.

Investment Details:
Company: {company_name} ({ticker})
Initial Investment: ${initial_investment:.2f}
Timeframe: {years_back} years
Final Value: ${final_value:.2f}
Product Skipped: {product_response}
Product Bought: {gain_response}

Video Script:
{video_script}

Respond in the EXACT format:

TITLE:
<Your engaging YouTube Shorts title, max 60 chars>

DESCRIPTION:
<2-3 sentence YouTube description>

TAGS:
<tag1, tag2, tag3, ... up to 10 tags, comma separated>
"""
        metadata_response = gpt_request(prompt)
        
        # Default metadata
        yt_title = f"What if you invested in {company_name}? 📈📉"
        yt_desc = video_script
        yt_tags = [ticker, "investing", "stocks", "finance", "wealth"]
        
        if metadata_response:
            try:
                from core.api.llm import extract_between
                parsed_title = extract_between(metadata_response, "TITLE:", "DESCRIPTION:").strip()
                parsed_desc = extract_between(metadata_response, "DESCRIPTION:", "TAGS:").strip()
                parsed_tags = metadata_response.split("TAGS:")[-1].strip()
                
                if parsed_title: yt_title = parsed_title
                if parsed_desc: yt_desc = parsed_desc
                if parsed_tags: yt_tags = [t.strip() for t in parsed_tags.split(',')]
            except Exception as e:
                print(f"Error parsing metadata: {e}")

        TEST_MODE = settings.get("Test_Mode-booleanME", True)
        
        if TEST_MODE:
            print("TEST MODE ON: Skipping YouTube upload.")
        else:
            # Upload to YouTube
            print("Uploading video to YouTube...")
            from core.api.google import upload_video
            VIDEO_UPLOAD_SPEED = settings.get("Video_Upload_Speed_MBs-integerNE")
            upload_speed_kb = int(VIDEO_UPLOAD_SPEED * 1024) if VIDEO_UPLOAD_SPEED else None
            channel_name = settings.get("YouTube_Channel_Name-selectYT", "Default")
            
            upload_video(
                file_path=str(out_video),
                title=yt_title,
                description=yt_desc,
                tags=yt_tags,
                category=24,
                privacy="public",
                max_speed=upload_speed_kb,
                channel_name=channel_name
            )
            print(f"Video uploaded successfully to {channel_name}.")
        # --- End YouTube Upload Section ---
        
        # --- Cleanup Section ---
        print("Cleaning up intermediate files...")
        try:
            if out_file.exists():
                out_file.unlink()
            if tts_output.exists():
                tts_output.unlink()
            for img_path in (product_images_abs or []):
                if Path(img_path).exists():
                    Path(img_path).unlink()
            for img_path in (gain_images_abs or []):
                if Path(img_path).exists():
                    Path(img_path).unlink()
            print("Cleanup complete.")
        except Exception as e:
            print(f"Error during cleanup: {e}")
            
    except subprocess.CalledProcessError as e:
        print(f"Failed to render video: {e}")

if __name__ == "__main__":
    run()
