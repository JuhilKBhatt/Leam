# Leam

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey)
![SocketIO](https://img.shields.io/badge/SocketIO-Realtime-green)
![Docker](https://img.shields.io/badge/Docker-Supported-blue)

Leam is a powerful, modular automation platform designed for content generation and management. Whether you're generating Reddit stories or automating YouTube comments, Leam provides a unified, Flask-based web interface to monitor, configure, and control your automation modules in real-time.

## ✨ Features

- **Modular Architecture:** Self-contained modules that can be easily plugged in or removed.
- **Real-time Web UI:** Monitor logs and control modules in real-time using Socket.IO.
- **Dynamic Configuration:** Automatically generates settings UI based on `module.json` schemas.
- **Extensible Core:** Built-in engines for audio, video, LLMs, and Google APIs.
- **Docker Support:** Ready-to-use Docker compose setup for easy containerized deployment.

## 📂 Project Structure

- **`app.py`**: The main entry point for the Flask web server.
- **`core/`**: Backbone logic (supervisor, engines for media, API interfaces).
- **`modules/`**: Directory containing independent automation modules.
- **`web/`**: Backend logic for the web interface and Socket.IO events.
- **`static/` & `templates/`**: Frontend assets and Jinja2 templates.
- **`data/`**: Persistent JSON data storage (e.g., system stats).

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
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

3. **Install the dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Set up your environment variables:**
   - Create a `.env` file or place your secrets in the `secrets/` directory. *(Ensure these are never committed to version control)*.

5. **Run the web application:**
   ```bash
   python3 app.py
   ```
   > The web UI will be accessible at `http://localhost:5000`.

*Note: A standalone system monitor is also available:*
```bash
python3 ./utilities/system_monitor.py
```

### Legacy / Standalone Scripts

If you need to run specific older modules directly from the command line:

- **Reddit Story Generator:**
  ```bash
  python -m leam_modules.Reddit_Story_Generator.reddit_app
  ```
- **YouTube Commenter:**
  ```bash
  python -m comment_client.commenter
  ```

### 🐳 Docker Deployment

To run Leam using Docker, simply use docker-compose:

```bash
docker-compose up --build
```

## 🛠️ Creating a New Module

Adding a new module to Leam is straightforward:

1. **Create a Directory:** Add a new folder in the `modules/` directory.
2. **Define Configuration:** Create a `module.json` file in the folder. This file defines the module's name, description, entry point (`run_file`), and dynamic settings.
3. **Write the Logic:** Implement your automation script as defined by your entry point.
4. **Auto-Detection:** The Leam web server will automatically detect the new module and populate it in the UI.

## 🔒 Security Note

**Never commit API keys or secrets.** 
Always verify that `.env` files and your `secrets/` directory are properly ignored via `.gitignore`.