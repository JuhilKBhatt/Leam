import os
import sys
import json
import random
import re
import requests
import yfinance as yf
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path so we can import core
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from core.utils.common import load_module_config
from core.api.llm import gpt_request
from core.utils.graph_templates.graph_animator import generate_animated_graph

MODULE_DIR = Path(__file__).parent
DATA_DIR = MODULE_DIR / "output"
LOG_DIR = MODULE_DIR / "logs"

def get_selected_companies(count=3):
    """Retrieve companies from sp500.json or fallback list."""
    sp500_file = project_root / "data" / "sp500.json"
    if sp500_file.exists():
        try:
            with open(sp500_file, 'r') as f:
                companies = json.load(f)
            return random.sample(companies, min(count, len(companies)))
        except Exception as e:
            print(f"Warning: Could not read sp500.json: {e}")
    return [
        {"name": "Apple Inc.", "ticker": "AAPL"},
        {"name": "Microsoft Corporation", "ticker": "MSFT"},
        {"name": "NVIDIA Corporation", "ticker": "NVDA"}
    ][:count]

def fetch_company_market_data(companies):
    """Fetch news and recent price metrics for companies via yfinance."""
    news_material = ""
    for comp in companies:
        ticker_str = comp['ticker']
        comp_name = comp['name']
        try:
            t = yf.Ticker(ticker_str)
            # Price history
            hist = t.history(period="5d")
            price_info = ""
            if not hist.empty and len(hist) >= 2:
                curr_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                pct_change = ((curr_price - prev_price) / prev_price) * 100
                direction = "+" if pct_change >= 0 else ""
                price_info = f"Current Price: ${curr_price:,.2f} ({direction}{pct_change:.2f}% today)"

            news_material += f"\n=== {comp_name} ({ticker_str}) ===\n{price_info}\n"

            # News articles
            news = t.news
            if news:
                news_material += "Recent Headlines:\n"
                for item in news[:3]:
                    content = item.get('content') or item
                    title = content.get('title', '')
                    summary = content.get('summary', '') or content.get('description', '')
                    pub_date = content.get('pubDate', '')
                    provider = content.get('provider', {}).get('displayName', '') if isinstance(content.get('provider'), dict) else ''
                    news_material += f"- Title: {title}\n  Source: {provider} ({pub_date})\n  Summary: {summary}\n"
        except Exception as e:
            print(f"Error fetching news for {ticker_str}: {e}")
            news_material += f"\n=== {comp_name} ({ticker_str}) ===\nRecent Market Mover\n"
    return news_material

def download_pexels_landscape_broll(query, save_path, pexels_key):
    """Search and download a landscape B-roll clip from Pexels."""
    if not pexels_key:
        return False
    try:
        headers = {"Authorization": pexels_key}
        url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query)}&orientation=landscape&per_page=5"
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"Pexels search returned status {resp.status_code} for query: {query}")
            return False

        data = resp.json()
        videos = data.get('videos', [])
        if not videos:
            print(f"No Pexels videos found for: {query}")
            return False

        # Find best landscape file
        chosen_link = None
        for vid in videos:
            files = vid.get('video_files', [])
            landscape_files = [f for f in files if f.get('width', 0) >= f.get('height', 0)]
            if landscape_files:
                # Prefer 1920x1080 or closest high resolution
                landscape_files.sort(key=lambda x: abs(x.get('width', 0) - 1920))
                chosen_link = landscape_files[0].get('link')
                break

        if not chosen_link and videos[0].get('video_files'):
            chosen_link = videos[0]['video_files'][0].get('link')

        if not chosen_link:
            return False

        print(f"Downloading Pexels B-Roll: {query} -> {save_path.name}")
        vid_resp = requests.get(chosen_link, stream=True, timeout=60)
        if vid_resp.status_code == 200:
            temp_raw = save_path.parent / f"raw_{save_path.name}"
            with open(temp_raw, 'wb') as f:
                for chunk in vid_resp.iter_content(chunk_size=16384):
                    f.write(chunk)

            # Normalize to 30fps faststart H.264 MP4 for Revideo compatibility
            import subprocess
            from core.engine.gpu import detect_gpu_backend
            gpu_backend = detect_gpu_backend()

            codec_args = ["-c:v", "libx264", "-preset", "ultrafast"]
            if gpu_backend == "nvenc":
                codec_args = ["-c:v", "h264_nvenc", "-preset", "p4"]
            elif gpu_backend == "vaapi":
                from core.engine.gpu import _working_vaapi_device
                dev = _working_vaapi_device or "/dev/dri/renderD128"
                codec_args = ["-init_hw_device", f"vaapi=va:{dev}", "-filter_hw_device", "va", "-c:v", "h264_vaapi"]

            ff_cmd = [
                "ffmpeg", "-y", "-i", str(temp_raw),
                *codec_args, "-pix_fmt", "yuv420p",
                "-r", "30", "-movflags", "+faststart",
                str(save_path)
            ]
            result = subprocess.run(ff_cmd, capture_output=True, text=True, timeout=60)
            try:
                os.remove(temp_raw)
            except Exception:
                pass

            if result.returncode == 0 and os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
                print(f"Successfully normalized Pexels video on {gpu_backend.upper()} GPU: {save_path.name}")
                return True
            else:
                print(f"FFmpeg normalization note: {result.stderr}")
                if os.path.exists(temp_raw):
                    os.rename(temp_raw, save_path)
                return True
        return False
    except Exception as e:
        print(f"Error downloading Pexels video for '{query}': {e}")
        return False

def run():
    print("=== Starting Market News Video Generation ===")
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    load_dotenv(project_root / "secrets" / ".env")

    config = load_module_config(MODULE_DIR)
    settings = config.get("settings", {})
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. Fetch Companies & News
    companies_count = int(settings.get("Companies_Count-integerNE") or 3)
    companies = get_selected_companies(companies_count)
    company_names = ", ".join([c["name"] for c in companies])
    print(f"Selected Companies ({len(companies)}): {company_names}")

    print("Fetching market news and trends from yfinance...")
    news_material = fetch_company_market_data(companies)

    # 2. LLM Script Generation
    script_prompt_template = settings.get("AI_Script_Prompt-stringLE", "")
    script_prompt = script_prompt_template.replace("{companies}", company_names).replace("{news_material}", news_material)

    print("Generating voiceover script with LLM...")
    full_voiceover = gpt_request(script_prompt).strip()
    if not full_voiceover:
        print("Error: Voiceover script generation failed. Exiting.")
        return

    # Clean script for TTS
    tts_script = re.sub(r'[\*#_`]', '', full_voiceover)
    tts_script = re.sub(r'(?<=\d),(?=\d)', '', tts_script)

    # 3. Google TTS Generation
    print("Generating TTS voiceover audio...")
    from core.engine.audio import generate_tts
    tts_output = DATA_DIR / f"market_news_{run_id}_voiceover.mp3"
    generate_tts(
        text=tts_script,
        output_file=tts_output,
        TTS_VOICES=["Aoede", "Charon", "Fenrir"],
        TTS_CHARACTER_LIMIT=150000,
        config_path=MODULE_DIR / "module.json"
    )

    # Duration calculation
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(tts_output))
        audio_duration_sec = audio.info.length
        durationInFrames = max(300, int(audio_duration_sec * 30))
    except Exception as e:
        print(f"Warning: Could not read audio length via mutagen: {e}")
        audio_duration_sec = 30.0
        durationInFrames = 900

    print(f"Voiceover Audio Duration: {audio_duration_sec:.2f}s ({durationInFrames} frames @ 30fps)")

    # 4. Sync Audio Timing with faster-whisper
    print("Transcribing audio with faster-whisper to extract timestamps...")
    from faster_whisper import WhisperModel
    import ctranslate2

    try:
        has_cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        has_cuda = False

    device = "cuda" if has_cuda else "cpu"
    compute_type = "float16" if has_cuda else "int8"
    print(f"Loading faster-whisper on {device.upper()} (compute_type={compute_type})...")
    try:
        model = WhisperModel("tiny.en", device=device, compute_type=compute_type)
    except Exception as e:
        print(f"Warning: Failed to initialize Whisper on {device} ({e}). Falling back to CPU...")
        model = WhisperModel("tiny.en", device="cpu", compute_type="int8")

    segments_gen, _ = model.transcribe(str(tts_output), word_timestamps=True)

    timestamped_script = ""
    segments_list = []
    for segment in segments_gen:
        segments_list.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        timestamped_script += f"[{segment.start:.2f}s - {segment.end:.2f}s]: {segment.text}\n"

    print("Timestamped transcript prepared.")

    # 5. LLM Visual Director (Scene-by-Scene Breakdown)
    visuals_prompt_template = settings.get("AI_Visuals_Prompt-stringLE", "")
    visuals_prompt = visuals_prompt_template.replace("{timestamped_script}", timestamped_script)

    print("Asking LLM Visual Director to generate scenes, b-roll queries, and animated elements...")
    visuals_response = gpt_request(visuals_prompt).strip()

    try:
        clean_json = visuals_response
        if clean_json.startswith("```json"):
            clean_json = clean_json.replace("```json", "", 1)
        if clean_json.startswith("```"):
            clean_json = clean_json.replace("```", "", 1)
        if clean_json.endswith("```"):
            clean_json = clean_json.rsplit("```", 1)[0]
        visuals_data = json.loads(clean_json.strip())
    except Exception as e:
        print(f"Failed to parse LLM visuals output as JSON: {e}")
        print(f"Raw response:\n{visuals_response}")
        # Build graceful fallback scene
        visuals_data = {
            "scenes": [
                {
                    "scene_index": 0,
                    "start_time": 0.0,
                    "end_time": audio_duration_sec,
                    "b_roll_query": "stock market trading floor",
                    "elements": [
                        {
                            "type": "Title",
                            "start_time": 0.5,
                            "end_time": min(6.0, audio_duration_sec),
                            "text": "Market News Update",
                            "subtext": company_names
                        }
                    ]
                }
            ]
        }

    # Normalize scenes structure
    scenes = visuals_data.get("scenes", [])
    if not scenes and visuals_data.get("info_layer"):
        # If model used legacy info_layer format
        scenes = [
            {
                "scene_index": 0,
                "start_time": 0.0,
                "end_time": audio_duration_sec,
                "b_roll_query": "stock market finance",
                "elements": visuals_data.get("info_layer", [])
            }
        ]

    # OVERLAP PROTECTION: Enforce strictly non-overlapping element timeline & minimum display durations
    last_el_end = 0.0
    for sc in scenes:
        clean_elems = []
        for el in sc.get("elements", []):
            el_type = el.get("type", "")
            start = float(el.get("start_time", last_el_end + 0.5))
            end = float(el.get("end_time", start + 4.0))

            if start < last_el_end + 0.5:
                start = last_el_end + 0.5

            min_dur = 5.5 if el_type == "AnimatedGraph" else 3.5
            if end - start < min_dur:
                end = start + min_dur

            if el_type == "NewsClipping" and "headline" in el:
                el["headline"] = " ".join(str(el["headline"]).split())

            el["start_time"] = round(start, 2)
            el["end_time"] = round(end, 2)
            last_el_end = end
            clean_elems.append(el)
        sc["elements"] = clean_elems

    # 6. Fetch Pexels Landscape B-Rolls
    pexels_key = os.getenv("PEXELS_API_KEY")
    serpapi_key = os.getenv("SERPAPI_KEY")
    downloaded_brolls = []

    print(f"Fetching {len(scenes)} landscape B-roll clips from Pexels...")
    for idx, scene in enumerate(scenes):
        b_roll_query = scene.get("b_roll_query", "stock market wall street")
        vid_path = DATA_DIR / f"market_news_{run_id}_bg_{idx}.mp4"

        success = download_pexels_landscape_broll(b_roll_query, vid_path, pexels_key)
        if not success and downloaded_brolls:
            # Fallback to existing downloaded clip
            scene["b_roll_video"] = downloaded_brolls[-1]
        elif success:
            rel_vid_path = f"modules/market_news/output/{vid_path.name}"
            scene["b_roll_video"] = rel_vid_path
            downloaded_brolls.append(rel_vid_path)

    # 7. Generate Animated Stock Graphs via LLM Python Code & Images
    graph_idx = 0
    img_idx = 0

    for scene in scenes:
        for element in scene.get("elements", []):
            elem_type = element.get("type")

            # Animated Stock Graph
            if elem_type == "AnimatedGraph":
                raw_ticker = element.get("ticker", "").strip().upper()
                tickers_found = re.findall(r'[A-Z]{1,5}', raw_ticker)
                ticker = tickers_found[0] if tickers_found else (companies[0]["ticker"] if companies else "AAPL")
                graph_type = element.get("graph_type", "line").strip()
                period = element.get("period", "6mo")
                title = element.get("title") or f"{ticker} Performance"
                start_t = float(element.get("start_time", 0.0))
                end_t = float(element.get("end_time", start_t + 5.5))

                graph_filename = f"market_news_{run_id}_graph_{graph_idx}.mp4"
                graph_path = DATA_DIR / graph_filename
                graph_idx += 1

                print(f"[MarketNews-Pipeline] [Graph #{graph_idx}] Initiating animated chart for {ticker}:")
                print(f"  * Title: '{title}' | Type: '{graph_type}' | Period: '{period}'")
                print(f"  * Target Output: {graph_path}")
                print(f"  * Spoken Timing Window: {start_t:.2f}s -> {end_t:.2f}s (duration: {end_t - start_t:.2f}s)")

                gen_success = generate_animated_graph(
                    ticker=ticker,
                    save_path=str(graph_path),
                    graph_type=graph_type,
                    period=period,
                    title=title
                )

                if gen_success and graph_path.exists() and graph_path.stat().st_size > 1000:
                    size_kb = graph_path.stat().st_size / 1024
                    rel_video_path = f"modules/market_news/output/{graph_filename}"
                    element['graph_video'] = rel_video_path

                    frames_dir = DATA_DIR / f"{graph_path.stem}_frames"
                    frame_files = list(frames_dir.glob("frame_*.jpg")) if frames_dir.exists() else []
                    if frame_files:
                        element['graph_frames_pattern'] = f"modules/market_news/output/{frames_dir.name}/frame_%04d.jpg"
                        element['graph_frames_count'] = len(frame_files)
                        print(f"[MarketNews-Pipeline] [Graph #{graph_idx}] SUCCESS: Generated graph MP4: {rel_video_path} ({size_kb:.1f} KB) & {len(frame_files)} frames in {frames_dir.name}")
                    else:
                        print(f"[MarketNews-Pipeline] [Graph #{graph_idx}] SUCCESS: Generated graph MP4: {rel_video_path} ({size_kb:.1f} KB)")
                else:
                    print(f"[MarketNews-Pipeline] [Graph #{graph_idx}] FAILED: Could not generate animated graph for {ticker} (exists={graph_path.exists()})")

            # Images via SerpAPI if configured
            if elem_type in ["FigureShow", "FigureQuote", "ObjectShow", "NewsClipping"] and serpapi_key:
                img_query = element.get("image_query") or element.get("name") or element.get("object_name")
                if img_query:
                    try:
                        serp_url = f"https://serpapi.com/search.json?engine=google_images&q={requests.utils.quote(img_query)}&api_key={serpapi_key}"
                        resp = requests.get(serp_url, timeout=10)
                        if resp.status_code == 200 and resp.json().get('images_results'):
                            photo_url = resp.json()['images_results'][0].get('original')
                            if photo_url:
                                img_resp = requests.get(photo_url, timeout=10)
                                if img_resp.status_code == 200:
                                    img_path = DATA_DIR / f"market_news_{run_id}_img_{img_idx}.jpg"
                                    img_idx += 1
                                    with open(img_path, 'wb') as f:
                                        f.write(img_resp.content)
                                    element["image_url"] = f"modules/market_news/output/{img_path.name}"
                    except Exception as e:
                        print(f"SerpAPI image fetch failed: {e}")

    # 8. Select Background Music
    music_dir = project_root / "media" / "audio" / "music"
    music_files = list(music_dir.glob("*.mp3"))
    chosen_bg_music = ""
    if music_files:
        chosen_track = random.choice(music_files)
        chosen_bg_music = f"media/audio/music/{chosen_track.name}"
        print(f"Selected background music: {chosen_bg_music}")

    # 9. Assemble Revideo Payload
    summary = {
        "companies": [c['name'] for c in companies],
        "scenes": scenes,
        "voiceover_audio": f"modules/market_news/output/{tts_output.name}",
        "bg_music": chosen_bg_music,
        "durationInFrames": durationInFrames
    }

    out_json = DATA_DIR / f"market_news_{run_id}.json"
    with open(out_json, 'w') as f:
        json.dump(summary, f, indent=4)
    print(f"Revideo render specs saved to: {out_json}")

    # Summary of graph assets included
    graph_elements = [el for sc in scenes for el in sc.get("elements", []) if el.get("type") == "AnimatedGraph"]
    print(f"[MarketNews-Pipeline] Ready to render: {len(graph_elements)} AnimatedGraph(s) in payload:")
    for g_i, g_el in enumerate(graph_elements):
        print(f"  * [{g_i + 1}] Ticker: '{g_el.get('ticker')}' | Video: '{g_el.get('graph_video')}' | Window: {g_el.get('start_time')}s - {g_el.get('end_time')}s")

    # 10. Render Landscape Video with Revideo
    import subprocess
    revideo_dir = project_root / "revideo"
    out_video = DATA_DIR / f"market_news_{run_id}.mp4"

    print("Rendering final 16:9 landscape video with Revideo...")
    try:
        render_cmd = [
            "npm", "run", "render", "--", "MarketNews",
            str(out_video),
            str(out_json)
        ]
        subprocess.run(render_cmd, cwd=revideo_dir, check=True)
        print(f"SUCCESS: Video rendered: {out_video}")

        # 11. YouTube Upload (Test Mode uploads as PRIVATE, Production as PUBLIC)
        print("Preparing for YouTube upload...")
        from core.api.google import generate_metadata_and_upload
        metadata_prompt = f"""
You are generating metadata for a YouTube video about market news.
Companies covered: {company_names}

Script:
{full_voiceover}

Respond in the EXACT format:
TITLE:
<Your YouTube title>

DESCRIPTION:
<Your description>

TAGS:
<tag1, tag2, tag3>
"""
        default_title = f"Market News: {company_names}"
        default_desc = "Latest updates on the stock market and corporate earnings."
        default_tags = ["market", "news", "stocks", "finance"] + [c["ticker"] for c in companies]

        generate_metadata_and_upload(
            video_path=str(out_video),
            metadata_prompt=metadata_prompt,
            default_title=default_title,
            default_desc=default_desc,
            default_tags=default_tags,
            settings=settings,
            category=25  # News & Politics
        )

    except Exception as e:
        print(f"Error rendering video: {e}")

if __name__ == "__main__":
    run()
