# Leam Project Instructions

Welcome to the Leam project. This document provides foundational guidance for developers and agents working on this codebase.

## Project Overview
Leam is a modular automation platform designed for content generation and management (e.g., Reddit story generation, YouTube commenting). It features a Flask-based web interface for monitoring and controlling these modules in real-time.

## Architecture & Structure

- **`app.py`**: The main entry point for the Flask web server.
- **`core/`**: Contains the backbone logic of the system.
    - `supervisor.py`: Manages the lifecycle of modules.
    - `engine/`: Handles core processing tasks like audio and video generation.
    - `api/`: Interfaces for external services (LLMs, Google APIs).
- **`modules/`**: Each directory here is a self-contained automation module.
    - `module.json`: Defines the module's name, description, entry point (`run_file`), and dynamic settings.
- **`web/`**: Backend logic for the web UI.
    - `sockets/`: SocketIO event handlers for logs, settings, and module execution.
- **`static/` & `templates/`**: Frontend assets and Jinja2 templates.
- **`data/`**: Stores persistent JSON data (e.g., system stats).

## Development Conventions

### Adding a New Module
1. Create a new directory in `modules/`.
2. Add a `module.json` file following the existing schema.
3. Implement the logic in the file specified by `run_file`.
4. The system will automatically detect the new module and display it in the UI.

### Settings Schema
Settings in `module.json` use a specific naming convention to dictate UI rendering:
- `-stringME`: Multi-select string (comma-separated).
- `-integerNE`: Non-editable integer (from UI perspective, often used for status).
- `-integerFE`: Floating point or specific integer field.
- `-stringLE`: Large text input (textarea).

### Coding Style
- **Python**: Use `pathlib` for file system operations. Follow PEP 8.
- **Async**: The web server uses `gevent` with `monkey.patch_all()`. Be mindful of blocking operations.
- **Communication**: Use `SocketIO` for real-time updates from modules to the UI.

## Common Workflows

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the App
```bash
python3 app.py
```

### Docker
```bash
docker-compose up --build
```

## Security Note
- Never commit API keys or secrets. Use the `secrets/` directory or `.env` files (ensure they are in `.gitignore`).
