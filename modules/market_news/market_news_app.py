import os
import sys
import json
import random
import yfinance as yf
from datetime import datetime
from pathlib import Path
import re

# Add project root to sys.path so we can import core
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from core.utils.common import load_module_config
from core.api.llm import gpt_request

MODULE_DIR = Path(__file__).parent
DATA_DIR = MODULE_DIR / "output"
LOG_DIR = MODULE_DIR / "logs"

def get_random_companies(count=3):
    sp500_file = project_root / "data" / "sp500.json"
    if not sp500_file.exists():
        return [{"name": "Apple Inc.", "ticker": "AAPL"}, {"name": "Microsoft Corporation", "ticker": "MSFT"}]
    with open(sp500_file, 'r') as f:
        companies = json.load(f)
    return random.sample(companies, count)

def run():
    print("Starting market news generation...")
    config = load_module_config(MODULE_DIR)
    settings = config.get("settings", {})
    
    companies_count = int(settings.get("Companies_Count-integerNE") or 3)
    companies = get_random_companies(companies_count)
    company_names = ", ".join([c["name"] for c in companies])
    print(f"Selected companies: {company_names}")
    
    news_material = ""
    for comp in companies:
        ticker = yf.Ticker(comp['ticker'])
        news = ticker.news
        if news:
            news_material += f"\n--- News for {comp['name']} ({comp['ticker']}) ---\n"
            for item in news[:3]: # Take top 3 news items per company
                content = item.get('content', {})
                title = content.get('title', '')
                summary = content.get('summary', '')
                pub_date = content.get('pubDate', '')
                news_material += f"Title: {title}\nDate: {pub_date}\nSummary: {summary}\n\n"
    
    script_prompt_template = settings.get("AI_Script_Prompt-stringLE", "")
    script_prompt = script_prompt_template.replace("{companies}", company_names).replace("{news_material}", news_material)
    
    print("Asking AI to generate script...")
    video_script_str = gpt_request(script_prompt).strip()
    
    # Try to parse the script to extract voiceovers
    try:
        # Strip codeblock wrappers if present
        if video_script_str.startswith("```json"):
            video_script_str = video_script_str.replace("```json", "", 1)
        if video_script_str.startswith("```"):
            video_script_str = video_script_str.replace("```", "", 1)
        if video_script_str.endswith("```"):
            # A bit tricky to replace the last occurrence, doing it manually
            video_script_str = video_script_str.rsplit("```", 1)[0]
            
        video_script_json = json.loads(video_script_str.strip())
        voiceovers = []
        for scene in video_script_json:
            voiceovers.append(scene.get("voiceover", ""))
        full_voiceover = " ".join(voiceovers)
    except Exception as e:
        print(f"Failed to parse AI output as JSON: {e}")
        print(f"Raw output: {video_script_str}")
        return
        
    print("Generating TTS...")
    from core.engine.audio import generate_tts
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    tts_output = DATA_DIR / f"market_news_{run_id}_voiceover.mp3"
    
    # Clean commas for TTS
    tts_script = re.sub(r'(?<=\d),(?=\d)', '', full_voiceover)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    generate_tts(tts_script, tts_output, ["Aoede", "Charon", "Fenrir"], 150000, MODULE_DIR / "module.json")
    
    # Calculate audio duration
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(tts_output))
        durationInFrames = max(300, int((audio.info.length) * 30))
    except Exception as e:
        print(f"Failed to get audio duration: {e}")
        durationInFrames = 300
    
    summary = {
        "companies": [c['name'] for c in companies],
        "script_json": video_script_json,
        "voiceover_audio": f"modules/market_news/output/{tts_output.name}",
        "durationInFrames": durationInFrames
    }
    
    out_file = DATA_DIR / f"market_news_{run_id}.json"
    with open(out_file, 'w') as f:
        json.dump(summary, f, indent=4)
        
    # Render video
    import subprocess
    remotion_dir = project_root / "remotion"
    out_video = DATA_DIR / f"market_news_{run_id}.mp4"
    
    try:
        subprocess.run([
            "npx", "remotion", "render", "src/index.ts", "MarketNews",
            str(out_video),
            f"--props={out_file}",
            "--concurrency=1",
            "--timeout=120000",
            "--scale=2",
            "--crf=14"
        ], cwd=remotion_dir, check=True)
        print(f"Video rendered: {out_video}")
        
    except Exception as e:
        print(f"Failed to render video: {e}")
        print("Note: Make sure to implement a MarketNews Remotion composition in remotion/src/Root.tsx and remotion/src/MarketNews.tsx")

if __name__ == "__main__":
    run()
