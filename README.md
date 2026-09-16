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
* `StockTimeline.tsx` and `RedditStory.tsx` read these props to construct the timeline, transitions, and subtitles on the fly.

### 4. Web Dashboard (`web/` & `app.py`)
A Flask web application running on `gevent` and `flask-socketio`.
* **Dynamic Settings**: `web/manager.py` reads the JSON schemas of each module and automatically renders HTML form inputs for them.
* **Real-time Logs**: Modules write to `logs/runtime.log`. The UI connects via SocketIO and tails these logs in real-time.
* **Hot Reloading**: `app.py` has `use_reloader=True`, meaning any changes to Python files instantly restart the server.

---

## 🐳 Docker Setup

Leam is built for seamless local development via Docker Compose.

* **Live File Sync**: `docker-compose.yml` mounts the entire project root (`./:/app`) into the container. You never need to rebuild the Docker image (`docker compose build`) when you change code. The Flask server auto-reloads, and the `supervisor` automatically uses the latest script on its next execution.
* **Headless Authentication**: Because Docker has no GUI, modules that require Google OAuth login (like TTS or YouTube Uploads) will print a URL to the terminal logs. Clicking the URL on the host machine routes the callback directly into the container (via mapped port 8080).

---

## 🛠️ Creating a New Module

1. **Create Directory**: Make `modules/your_module_name/`.
2. **Define Schema**: Add `module.json` defining `"run_file"`, `"settings"`, and `"run_options"`.
3. **Write Script**: Create your entry point (e.g. `main.py`). Use `from core.api.llm import gpt_request` or `from core.engine.audio import generate_tts` to build your pipeline.
4. **Run**: The web UI will instantly detect your new module, build the settings page, and allow you to toggle the Supervisor to start running it.