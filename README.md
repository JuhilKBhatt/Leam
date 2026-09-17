# Leam - Autonomous Content Generation & Management Platform

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey)
![SocketIO](https://img.shields.io/badge/SocketIO-Realtime-green)
![Docker](https://img.shields.io/badge/Docker-Supported-blue)
![Revideo](https://img.shields.io/badge/Revideo-Video%20Generation-blueviolet)

Leam is a modular, agentic automation platform for generating and distributing content. It orchestrates LLMs, Text-To-Speech (TTS) engines, programmatic video generation (Revideo), and external APIs (YouTube, Reddit, SerpApi) through a unified Flask/SocketIO dashboard.

---

## 🏗️ Project Architecture

The codebase is split into distinct domains to keep automation logic decoupled from system resources.

### 1. The Core (`core/`)
The `core` directory is the backbone of Leam, providing high-level wrappers for APIs and engines so that modules don't have to rewrite boilerplate code.

* **API Integrations (`core/api/`)**:
  * `google.py`: Handles complex Google OAuth flows (headless Out-of-Band alternatives via `run_local_server`), YouTube Video Uploads with chunked resumption, YouTube Commenting/Replying, Trending fetching, and Transcript fetching.
  * `llm.py`: A wrapper for Google GenAI (Gemini) used across the app to generate video scripts, system prompts, and YouTube metadata.
  * `serpapi.py`: Queries Google Images via SerpApi and downloads image assets directly to module output folders.

* **Engines (`core/engine/`)**:
  * `audio.py`: Interfaces with Google Cloud Text-to-Speech (specifically `Chirp3-HD`). It handles text chunking (to avoid API length limits), usage tracking to prevent billing overruns, and merges audio chunks using `ffmpeg`.
  * `video.py` / `music.py`: Utilities for handling audio/video mixing and background music selection.
  * `gpu.py`: Detects system hardware (Nvidia CUDA or Apple Silicon MPS) and dynamically allocates it to models like `faster-whisper`.

* **Orchestration (`core/supervisor.py` & `monitor.py`)**:
  * `supervisor.py`: An independent daemon that wraps module scripts. It reads a module's `module.json` and runs it as a subprocess either finitely (once) or indefinitely (looping on an interval within a specified HH:MM time window).
  * `monitor.py`: A background daemon that polls system stats (CPU, RAM, Disk) and broadcasts them to the web UI.

### 2. The Modules (`modules/`)
Modules are completely independent scripts that leverage the `core/` to perform specific business logic. They are dynamically discovered by the web server.

* **`stock_timeline`**: Fetches historical stock data (using `yfinance`), calculates gains/losses, asks the LLM what luxury item could be bought with the profits, downloads images of that item via SerpApi, generates a voiceover via Google TTS, transcribes the voiceover for timing using `faster-whisper`, renders a portrait video via Revideo, and finally uploads it to YouTube.
* **`reddit_story`**: Scrapes Reddit (using `praw`), splits the text, generates a TTS voiceover, transcribes it for subtitle timing, and renders a Minecraft parkour-style portrait video using Revideo before uploading.
* **`youtube_commenter`**: Scrapes trending YouTube videos and uses an LLM to generate contextual, engaging comments or replies to grow channel presence.
* **`market_news`**: Uses `yfinance` to fetch news and feeds it to the LLM to generate a script. The script is then used to generate a TTS voiceover using Google TTS and using `faster-whisper` to get the timing of words and sentences. The `faster-whisper` output is again feed to LLM to get scene by scene description of the video and video elements. The B-roll is fetched and downloaded from pexel and graphs/video elements are graphed by LLM writing python code. The graph and video elements put to together using Revideo to generate a landscape video.
* **`stock_comparison_generator`**: Fetches historical stock data of two stocks (using `yfinance`), calculates gains/losses, asks the LLM to generate a script comparing the two stocks, generates a TTS voiceover using Google TTS, generates a graph comparing the two stocks using LLM writing python code, fetches logos of the two companies using SerpApi and put to gether using Revideo to generate a portrait video.

Each module contains:
* `module.json`: Base configuration schema and settings structure.
* `module.local.json`: The user's specific saved configuration and API limits (ignored by git).
* `output/` & `logs/`: Localized storage for artifacts and execution logs.

### 3. Video Generation Pipeline (`revideo/`)
Instead of using complex `ffmpeg` filters, Leam uses **Revideo** to generate dynamic videos programmatically. 
When a Python module finishes preparing assets (audio, images, timings), it dumps a JSON file into its `output/` folder. It then calls the Revideo rendering script, passing the JSON file as props. 
* `StockTimeline.tsx`, `RedditStory.tsx`, and `MarketNews.tsx` read these props to construct the timeline, transitions, cards, and subtitles on the fly.
* In `MarketNews.tsx`, embedded animated stock charts are rendered frame-by-frame using high-speed `<Img src={frameSignal} />` sequences rather than nested video seeking, guaranteeing zero frame-drop or seeking stalls in headless Puppeteer.
* **Reusable Video Templates (`revideo/src/utils/`)**: Includes `disclaimer.tsx` for animated "Not Financial Advice" warnings (circular icon pop-in, message sliding out from the icon, 5-second hold, and slide-in retract) used exclusively in financial market videos, and `outro.tsx` for call-to-action overlays.

### 4. Web Dashboard (`web/` & `app.py`)
A Flask web application running on `gevent` and `flask-socketio`.
* **Dynamic Settings**: `web/manager.py` reads the JSON schemas of each module and automatically renders HTML form inputs for them.
* **Real-time Logs**: Modules write to `logs/runtime.log`. The UI connects via SocketIO and tails these logs in real-time.
* **Hot Reloading**: `app.py` has `use_reloader=True`, meaning any changes to Python files instantly restart the server.

---

## 🚀 How to Run

### 1. Prerequisites & Environment Setup
Create your environment file in `secrets/.env`:
```bash
mkdir -p secrets
touch secrets/.env
```

Add your required API keys to `secrets/.env`:
* **Gemini API:** `GEMINI_API_KEY`
* **SerpApi:** `SERPAPI_KEY_1`, `SERPAPI_KEY_2` (optional additional key)
* **Pexels API:** `PEXELS_API_KEY`
* **Reddit API:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
* **Google / YouTube OAuth:** Place `client_secrets.json` inside the `secrets/` directory if you plan to upload to YouTube or use Google Cloud TTS.

---

### 2. Running with Docker Compose (Recommended)

Leam is built for seamless local development via Docker Compose with volume-mounted live code sync.

#### Standard Run
```bash
docker compose up --build
```
Or run in detached mode in the background:
```bash
docker compose up -d
```

#### NVIDIA GPU Accelerated Run
For host machines with an NVIDIA GPU and `nvidia-container-toolkit` installed:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

#### Dashboard & Monitoring
* **Web Dashboard:** Open [http://localhost:5000](http://localhost:5000) in your browser.
* **View Logs:** `docker compose logs -f`
* **Stop Container:** `docker compose down`

* **Live File Sync**: `docker-compose.yml` mounts the entire project root (`./:/app`) into the container. You never need to rebuild the Docker image (`docker compose build`) when modifying code. The Flask server auto-reloads (`use_reloader=True`), and the Supervisor automatically executes the latest code.
* **Headless Authentication**: Because Docker has no GUI, modules that require Google OAuth login (like TTS or YouTube Uploads) will print an authorization URL to the terminal logs. Opening the URL on the host machine routes the OAuth callback directly into the container (via mapped port `8080` or `8081`).

---

### 3. Running Locally (Without Docker)

If you prefer running natively on your host machine:

#### Prerequisites
* **Python 3.12**
* **Node.js 20+** & **npm**
* **FFmpeg** installed on your system PATH
* **Chromium** (required by Revideo for rendering)

#### Setup & Execution
1. **Set Up Python Virtual Environment:**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Revideo Dependencies:**
   ```bash
   cd revideo && npm install && cd ..
   ```

3. **Start Platform:**
   ```bash
   bash start.sh
   ```
   *(Or start `python core/monitor.py &` followed by `python app.py`)*

4. Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📊 API Rate Limits & Quota Configuration

Leam features built-in autonomous rate limiting, usage tracking, and quota telemetry. Limits are configured and persisted in gitignored JSON files in `data/` and reported in real-time on the web dashboard:

| Service / API | Quota File | Limit | Reset Mechanism | Features |
|---|---|---|---|---|
| **Google Cloud TTS** | `data/tts_quota.json` | `1,000,000` chars/month | Monthly (`YYYY-MM`) | Global limit enforcement + per-module breakdown |
| **Pexels Video API** | `data/pexels_quota.json` | `200` reqs/hour<br>`20,000` reqs/month | Sliding 3600s window & monthly reset | Upstream header sync (`x-ratelimit-*`), countdown timer |
| **Reddit Data API** | `data/reddit_quota.json` | `100` QPM (OAuth) | Sliding 60s window | Automatic backoff/sleep when near limit, upstream sync |
| **SerpApi (Google Images)** | `data/google_search_quota.json` | `250` reqs/month per key | Key-specific billing cycle day | Multi-key rotation, automatic fallback on error/exhaustion |

---

### Quota Tracking Files (`data/*.json`)

#### 1. Text-To-Speech (`data/tts_quota.json`)
Tracks global character consumption against Google Cloud Text-to-Speech (Chirp3-HD) limits and breaks down usage across individual modules:
```json
{
  "month": "",
  "limit": ,
  "total_used": ,
  "remaining": ,
  "percent_used": ,
  "modules": {
    "market_news": ,
    "reddit_story": ,
    "stock_timeline": 
  },
  "last_updated": ""
}
```
* **`limit`**: Monthly character ceiling.
* **`total_used`**: Total characters requested this calendar month across all modules.
* **`remaining`**: Characters remaining before the request is blocked.
* **`modules`**: Per-module character breakdown.
* **Dashboard Endpoint**: `GET /api/tts/quota`

#### 2. Pexels API (`data/pexels_quota.json`)
Tracks hourly sliding-window rate limits and monthly request quotas for landscape B-roll video downloads:
```json
{
  "month": "",
  "hourly_limit": ,
  "monthly_limit": ,
  "hourly_used": ,
  "monthly_used": ,
  "modules": {
    "market_news": 
  },
  "recent_timestamps": [],
  "upstream_limit": ,
  "upstream_remaining": ,
  "upstream_reset": ,
  "last_updated": ""
}
```
* **`hourly_limit`** & **`monthly_limit`**: Configured caps from Pexels API rate tiers.
* **`hourly_used`** / **`monthly_used`**: Requests made in the current sliding 3600-second window and calendar month.
* **`recent_timestamps`**: UNIX timestamps of requests in the last hour to calculate exact second-level roll-off resets.
* **`upstream_*`**: Synchronized response headers directly from Pexels servers (`x-ratelimit-*`).
* **Dashboard Endpoint**: `GET /api/pexels/quota`

#### 3. Reddit API (`data/reddit_quota.json`)
Tracks the 100 Queries Per Minute (QPM) OAuth rate limit and overall monthly usage:
```json
{
  "month": "",
  "qpm_limit": ,
  "qpm_used": ,
  "monthly_used": ,
  "modules": {
    "reddit_story": 
  },
  "recent_timestamps": [],
  "upstream_remaining": ,
  "last_updated": ""
}
```
* **`qpm_limit`**: Maximum queries allowed per 60-second rolling window.
* **`recent_timestamps`**: UNIX timestamps of queries within the last 60 seconds. If limit is approached, the API pauses automatically until timestamps roll off.
* **`upstream_remaining`**: Reddit internal rate limit remaining queries reported by PRAW.
* **Dashboard Endpoint**: `GET /api/reddit/quota`

#### 4. SerpApi (`data/google_search_quota.json`)
Stores billing cycle reset dates and request counts per configured key:
```json
{
  "SERPAPI_KEY_1": {
    "cycle_start": "",
    "count": ,
    "limit": ,
    "reset_day": 3,
    "next_reset": ""
  },
  "SERPAPI_KEY_2": {
    "cycle_start": "",
    "count": ,
    "limit": ,
    "reset_day": ,
    "next_reset": ""
  }
}
```
* **`reset_day`**: The day of the month when that specific key's billing cycle resets.
* **`cycle_start`** & **`next_reset`**: Calculated dates of current and upcoming billing cycles.
* **`limit`**: Monthly search request cap for that key.
* **`count`**: Current usage within the active billing cycle.

---

### Module JSON Variables (`module.json` & `module.local.json`)

Each module in `modules/<module_name>/` defines its schema and stores user settings:

* **`module.json` (Base Schema)**:
  - Defines the module entrypoint (`"run_file": "main.py"`).
  - Specifies UI settings schema rendered dynamically on the web dashboard (types: `STRING`, `INTEGER`, `BOOLEAN`, `SELECT`, `TEXTAREA`).
  - Defines default values and execution modes (`"continuous"` loop or `"once"`).
* **`module.local.json` (Local Overrides)**:
  - Generated and updated when saving module settings via the web dashboard.
  - Stores user-specific values, active schedules (HH:MM windows), and configuration overrides.
  - Ignored by git (`.gitignore`) to keep user-specific configurations private.

### sp500.json

Contants information of S&P 500 companies for yfinance:

```json
[
  {
    "name": "NVIDIA Corporation",
    "ticker": "NVDA",
    "industry": "Information Technology"
  },
  {
    "name": "Apple Inc.",
    "ticker": "AAPL",
    "industry": "Information Technology"
  },
  {
    "name": "Microsoft Corporation",
    "ticker": "MSFT",
    "industry": "Information Technology"
  }
]
```

---

## 🛠️ Creating a New Module

1. **Create Directory**: Make `modules/your_module_name/`.
2. **Define Schema**: Add `module.json` defining `"run_file"`, `"settings"`, and `"run_options"`.
3. **Write Script**: Create your entry point (e.g. `main.py`). Use `from core.api.llm import gpt_request` or `from core.engine.audio import generate_tts` to build your pipeline.
4. **Run**: The web UI will instantly detect your new module, build the settings page, and allow you to toggle the Supervisor to start running it.