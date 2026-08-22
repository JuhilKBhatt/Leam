# Leam

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey)
![SocketIO](https://img.shields.io/badge/SocketIO-Realtime-green)
![Docker](https://img.shields.io/badge/Docker-Supported-blue)
![Remotion](https://img.shields.io/badge/Remotion-Video%20Generation-blueviolet)

Leam is a powerful, modular automation platform designed for content generation and management. Whether you're generating Reddit story videos, analyzing stock timelines, or automating YouTube comments, Leam provides a unified, Flask-based web interface to monitor, configure, and control your automation modules in real-time.

## ✨ Features

- **Modular Architecture:** Self-contained modules that can be easily plugged in or removed (e.g., `reddit_story`, `youtube_commenter`, `stock_timeline`).
- **Real-time Web UI:** Monitor logs and control modules in real-time using Socket.IO.
- **Dynamic Configuration:** Automatically generates settings UI based on `module.json` and `module.local.json` schemas.
- **Extensible Core:** Built-in engines for audio (TTS, Whisper), video, LLMs (Google GenAI), and API integrations.
- **Programmatic Video Generation:** Integrates **Remotion** for dynamic, high-quality video rendering using React.
- **GPU Acceleration:** Automatic detection and utilization of GPU hardware (CUDA, MPS) for faster media processing and inference.
- **Docker Support:** Ready-to-use Docker compose setup for easy containerized deployment (with optional GPU support).

## 📂 Project Structure

- **`app.py`**: The main entry point for the Flask web server.
- **`core/`**: Backbone logic including supervisor and engines for media (audio, video, music), GPU management, and API interfaces (Google, YouTube).
- **`modules/`**: Directory containing independent automation modules.
- **`remotion/`**: React-based video generation pipeline using Remotion.
- **`web/`**: Backend logic for the web interface, routing, and Socket.IO real-time events.
- **`static/` & `templates/`**: Frontend assets and Jinja2 templates.
- **`data/` & `media/`**: Persistent data storage and media asset management.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- [Node.js](https://nodejs.org/) & npm (required for Remotion video generation)
- [Docker](https://www.docker.com/) (Optional, for containerized deployment)

### Local Setup

1. **Navigate to the project directory:**
   ```bash
   cd path/to/Leam
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Install Node dependencies for Remotion:**
   ```bash
   cd remotion
   npm install
   cd ..
   ```

5. **Set up your environment variables:**
   - Create a `.env` file or place your secrets in the `secrets/` directory. *(Ensure these are never committed to version control)*.

6. **Run the web application:**
   ```bash
   python3 app.py
   ```
   > The web UI will be accessible at `http://localhost:5000`.

### 🐳 Docker Deployment

To run Leam using Docker, you can use the standard or GPU-enabled docker-compose files:

**Standard CPU Deployment:**
```bash
docker-compose up --build
```

**GPU Accelerated Deployment (requires NVIDIA Container Toolkit):**
```bash
docker-compose -f docker-compose.gpu.yml up --build
```

## 🛠️ Creating a New Module

Adding a new module to Leam is straightforward:

1. **Create a Directory:** Add a new folder in the `modules/` directory (e.g., `modules/my_new_module`).
2. **Define Configuration:** Create a `module.json` file in the folder. This file defines the module's name, description, entry point (`run_file`), and dynamic settings schema. (Local overrides can be saved in `module.local.json`).
3. **Write the Logic:** Implement your automation script as defined by your entry point. Use `core/` utilities to access LLMs, Video generation, and API auth.
4. **Auto-Detection:** The Leam web server will automatically detect the new module and populate it in the UI.

## 🔒 Security Note

**Never commit API keys, OAuth tokens, or secrets.** 
Always verify that `.env` files and your `secrets/` directory are properly ignored via `.gitignore`.