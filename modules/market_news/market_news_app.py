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

def generate_graph(ticker, save_path):
    try:
        import matplotlib.pyplot as plt
        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty: return False
        
        # Style the plot for a modern finance video
        plt.style.use('dark_background')
        plt.figure(figsize=(12, 7))
        plt.plot(hist.index, hist['Close'], color='#00ff99', linewidth=3)
        plt.fill_between(hist.index, hist['Close'], color='#00ff99', alpha=0.1)
        plt.title(f"{ticker} - 1 Year Performance", fontsize=24, fontweight='bold', color='white')
        plt.xlabel("Date", fontsize=14, color='gray')
        plt.ylabel("Price (USD)", fontsize=14, color='gray')
        plt.grid(True, linestyle='--', alpha=0.2)
        plt.tight_layout()
        plt.savefig(save_path, transparent=True)
        plt.close()
        return True
    except Exception as e:
        print(f"Error generating graph for {ticker}: {e}")
        return False

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
            for item in news[:3]:
                content = item.get('content', {})
                title = content.get('title', '')
                summary = content.get('summary', '')
                pub_date = content.get('pubDate', '')
                news_material += f"Title: {title}\nDate: {pub_date}\nSummary: {summary}\n\n"
    
    script_prompt_template = settings.get("AI_Script_Prompt-stringLE", "")
    script_prompt = script_prompt_template.replace("{companies}", company_names).replace("{news_material}", news_material)
    
    print("Asking AI to generate voiceover script...")
    full_voiceover = gpt_request(script_prompt).strip()
    
    if not full_voiceover:
        print("Failed to generate voiceover script. Exiting.")
        return

    print("Generating TTS...")
    from core.engine.audio import generate_tts
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    tts_output = DATA_DIR / f"market_news_{run_id}_voiceover.mp3"
    
    tts_script = re.sub(r'(?<=\d),(?=\d)', '', full_voiceover)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    generate_tts(tts_script, tts_output, ["Aoede", "Charon", "Fenrir"], 150000, MODULE_DIR / "module.json")
    
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(tts_output))
        durationInFrames = max(300, int((audio.info.length) * 30))
    except Exception as e:
        print(f"Failed to get audio duration: {e}")
        durationInFrames = 300

    print("Syncing audio timing with faster-whisper...")
    from faster_whisper import WhisperModel
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(tts_output), word_timestamps=True)
    
    timestamped_script = ""
    for segment in segments:
        timestamped_script += f"[{segment.start:.2f}s - {segment.end:.2f}s]: {segment.text}\n"

    print("Asking AI for visuals and timestamps...")
    visuals_prompt_template = settings.get("AI_Visuals_Prompt-stringLE", "")
    visuals_prompt = visuals_prompt_template.replace("{timestamped_script}", timestamped_script)
    
    visuals_response = gpt_request(visuals_prompt).strip()
    
    try:
        if visuals_response.startswith("```json"):
            visuals_response = visuals_response.replace("```json", "", 1)
        if visuals_response.startswith("```"):
            visuals_response = visuals_response.replace("```", "", 1)
        if visuals_response.endswith("```"):
            visuals_response = visuals_response.rsplit("```", 1)[0]
            
        video_script_json = json.loads(visuals_response.strip())
    except Exception as e:
        print(f"Failed to parse visuals AI output as JSON: {e}")
        print(f"Raw output: {visuals_response}")
        return

    from dotenv import load_dotenv
    import requests
    load_dotenv(project_root / ".env")
    pexels_key = os.getenv("PEXELS_API_KEY")
    
    # 1. Fetch Background B-Rolls
    background_videos = []
    if pexels_key:
        print("Fetching Background B-Roll from Pexels...")
        headers = {"Authorization": pexels_key}
        queries = video_script_json.get("background_b_roll_queries", ["stock market"])
        for i, query in enumerate(queries):
            try:
                resp = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page=1", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('videos'):
                        video = data['videos'][0]
                        files = video.get('video_files', [])
                        files.sort(key=lambda x: x.get('width', 0), reverse=True)
                        link = files[0]['link']
                        
                        vid_resp = requests.get(link, stream=True)
                        if vid_resp.status_code == 200:
                            vid_path = DATA_DIR / f"market_news_{run_id}_bg_{i}.mp4"
                            with open(vid_path, 'wb') as vf:
                                for chunk in vid_resp.iter_content(chunk_size=8192):
                                    vf.write(chunk)
                            background_videos.append(f"modules/market_news/output/{vid_path.name}")
            except Exception as e:
                print(f"Error fetching from Pexels: {e}")
    
    # 2. Process Info Layer Elements (Images & Graphs)
    info_layer = video_script_json.get("info_layer", [])
    
    sys.path.append(str(project_root / "core" / "utils" / "graph_templates"))
    from graph_animator import generate_animated_graph

    for i, element in enumerate(info_layer):
        elem_type = element.get("type")
        
        # Fetch Images for Figures/Objects
        if elem_type in ["FigureShow", "FigureQuote", "ObjectShow", "NewsClipping"] and pexels_key:
            img_query = element.get("image_query")
            if img_query:
                try:
                    resp = requests.get(f"https://api.pexels.com/v1/search?query={img_query}&per_page=1", headers=headers)
                    if resp.status_code == 200 and resp.json().get('photos'):
                        photo_url = resp.json()['photos'][0]['src']['large2x']
                        img_resp = requests.get(photo_url)
                        if img_resp.status_code == 200:
                            img_path = DATA_DIR / f"market_news_{run_id}_img_{i}.jpg"
                            with open(img_path, 'wb') as f:
                                f.write(img_resp.content)
                            element["image_url"] = f"modules/market_news/output/{img_path.name}"
                except Exception as e:
                    print(f"Failed to fetch image: {e}")
                    
        # Generate Animated Graphs
        if elem_type == "AnimatedGraph":
            ticker = element.get("ticker", "").strip()
            if ticker:
                graph_path = DATA_DIR / f"market_news_{run_id}_graph_{i}.mp4"
                if generate_animated_graph(ticker, str(graph_path)):
                    element['graph_video'] = f"modules/market_news/output/{graph_path.name}"

    summary = {
        "companies": [c['name'] for c in companies],
        "background_videos": background_videos,
        "info_layer": info_layer,
        "voiceover_audio": f"modules/market_news/output/{tts_output.name}",
        "durationInFrames": durationInFrames
    }
    
    out_file = DATA_DIR / f"market_news_{run_id}.json"
    with open(out_file, 'w') as f:
        json.dump(summary, f, indent=4)
        
    import subprocess
    remotion_dir = project_root / "remotion"
    out_video = DATA_DIR / f"market_news_{run_id}.mp4"
    
    try:
        subprocess.run([
            "npx", "remotion", "render", "src/index.ts", "MarketNews",
            str(out_video),
            f"--props={out_file}",
            "--concurrency=1",
            "--timeout=1200000",
            "--gl=angle",
            "--scale=2",
            "--crf=14"
        ], cwd=remotion_dir, check=True)
        print(f"Video rendered: {out_video}")
        
    except Exception as e:
        print(f"Failed to render video: {e}")

if __name__ == "__main__":
    run()
