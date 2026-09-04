import os
import sys
import json
import random
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import re

# Add project root to sys.path so we can import core
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from core.utils.common import load_module_config
from core.api.llm import gpt_request
from core.api.serpapi import get_google_image_from_serpapi

MODULE_DIR = Path(__file__).parent
DATA_DIR = MODULE_DIR / "output"
LOG_DIR = MODULE_DIR / "logs"

def get_random_companies(count=2):
    """Picks random companies from the local sp500.json file."""
    sp500_file = project_root / "data" / "sp500.json"
    if not sp500_file.exists():
        print("sp500.json not found, falling back to Apple and Microsoft")
        return [{"name": "Apple Inc.", "ticker": "AAPL"}, {"name": "Microsoft Corporation", "ticker": "MSFT"}]
        
    with open(sp500_file, 'r') as f:
        companies = json.load(f)
    return random.sample(companies, count)

def fetch_stock_data(ticker, years_back):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365)
    print(f"Fetching data for {ticker}...")
    stock = yf.Ticker(ticker)
    # Explicitly use auto_adjust=True to guarantee dividend reinvestment and split adjustments
    hist = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), auto_adjust=True)
    return hist

def run():
    print("Starting stock industry comparison generation...")
    config = load_module_config(MODULE_DIR)
    settings = config.get("settings", {})
    
    initial_investment = float(settings.get("Initial_Investment-integerNE") or 1000)
    years_back = int(settings.get("Years_Back-integerNE") or 5)
    
    # Get 2 companies
    companies = get_random_companies(2)
    comp_a = companies[0]
    comp_b = companies[1]
    
    print(f"Selected {comp_a['name']} ({comp_a['ticker']}) VS {comp_b['name']} ({comp_b['ticker']})")

    hist_a = fetch_stock_data(comp_a['ticker'], years_back)
    hist_b = fetch_stock_data(comp_b['ticker'], years_back)
    
    if hist_a.empty or hist_b.empty:
        print("Failed to find historical data for one or both companies. Exiting.")
        return

    import pandas as pd
    df = pd.DataFrame({'a': hist_a['Close'], 'b': hist_b['Close']}).dropna()
    
    if df.empty:
        print("Failed to align historical data for both companies. Exiting.")
        return

    first_price_a = float(df['a'].iloc[0])
    last_price_a = float(df['a'].iloc[-1])
    final_a = float((initial_investment / first_price_a) * last_price_a)

    first_price_b = float(df['b'].iloc[0])
    last_price_b = float(df['b'].iloc[-1])
    final_b = float((initial_investment / first_price_b) * last_price_b)
    
    print(f"Final values: {comp_a['ticker']} = ${final_a:.2f}, {comp_b['ticker']} = ${final_b:.2f}")

    # Fetch logos
    print("Fetching logos via SerpApi...")
    logo_a_path = get_google_image_from_serpapi(f"{comp_a['name']} logo icon transparent png", str(DATA_DIR), num_images=1)
    logo_b_path = get_google_image_from_serpapi(f"{comp_b['name']} logo icon transparent png", str(DATA_DIR), num_images=1)
    
    logo_a_rel = f"modules/stock_comparison_generator/output/{Path(logo_a_path).name}" if logo_a_path else None
    logo_b_rel = f"modules/stock_comparison_generator/output/{Path(logo_b_path).name}" if logo_b_path else None

    # Process prices for chart
    prices = []
    for date, row in df.iterrows():
        prices.append({
            "date": date.strftime('%Y-%m-%d'),
            "price_a": row['a'],
            "price_b": row['b']
        })

    # Ask AI to generate a script
    script_prompt_template = settings.get("AI_Script_Prompt-stringLE", "")
    
    script_prompt = script_prompt_template.replace("{investment}", f"{initial_investment:.2f}") \
                                          .replace("{company_a}", comp_a['name']) \
                                          .replace("{company_b}", comp_b['name']) \
                                          .replace("{years}", str(years_back)) \
                                          .replace("{final_a}", f"${final_a:.2f}") \
                                          .replace("{final_b}", f"${final_b:.2f}")
                                          
    print("Asking AI to generate script...")
    video_script = gpt_request(script_prompt).strip()
    print(f"Script: {video_script}")

    # Generate TTS
    from core.engine.audio import generate_tts
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    tts_output = DATA_DIR / f"vs_{run_id}_voiceover.mp3"
    
    # Remove commas to avoid TTS pause
    tts_script = re.sub(r'(?<=\d),(?=\d)', '', video_script)
    generate_tts(tts_script, tts_output, ["Aoede", "Charon", "Fenrir"], 150000, MODULE_DIR / "module.json")
    
    from mutagen.mp3 import MP3
    audio = MP3(str(tts_output))
    durationInFrames = max(300, int((audio.info.length) * 30))

    # Sync audio for transition (part1 ends after 2 seconds to show logos then graph)
    part1EndFrame = 60 # 2 seconds of logos

    # Save output JSON
    summary = {
        "company_a": comp_a['name'],
        "ticker_a": comp_a['ticker'],
        "company_b": comp_b['name'],
        "ticker_b": comp_b['ticker'],
        "years": years_back,
        "initial_investment": initial_investment,
        "final_a": final_a,
        "final_b": final_b,
        "logo_a": logo_a_rel,
        "logo_b": logo_b_rel,
        "script": video_script,
        "voiceover_audio": f"modules/stock_comparison_generator/output/{tts_output.name}",
        "durationInFrames": durationInFrames,
        "part1EndFrame": part1EndFrame,
        "prices": prices
    }
    
    os.makedirs(DATA_DIR, exist_ok=True)
    out_file = DATA_DIR / f"vs_{run_id}.json"
    with open(out_file, 'w') as f:
        json.dump(summary, f, indent=4)
        
    # Render video
    import subprocess
    remotion_dir = project_root / "remotion"
    out_video = DATA_DIR / f"vs_{run_id}.mp4"
    
    try:
        subprocess.run([
            "npx", "remotion", "render", "src/index.ts", "StockComparison",
            str(out_video),
            f"--props={out_file}"
        ], cwd=remotion_dir, check=True)
        print(f"Video rendered: {out_video}")
        
        # YouTube upload logic
        TEST_MODE = settings.get("Test_Mode-booleanME", True)
        if not TEST_MODE:
            print("Uploading to YouTube...")
            yt_title = f"{comp_a['ticker']} vs {comp_b['ticker']} - Which was the better investment? 📈"
            from core.api.google import upload_video
            channel_name = settings.get("YouTube_Channel_Name-selectYT", "Default")
            upload_video(
                file_path=str(out_video),
                title=yt_title,
                description=video_script,
                tags=[comp_a['ticker'], comp_b['ticker'], "stocks", "finance", "investing", "comparison"],
                category=24,
                privacy="public",
                channel_name=channel_name
            )
            
    except Exception as e:
        print(f"Failed to render video: {e}")

if __name__ == "__main__":
    run()
