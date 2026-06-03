#!/bin/bash

# Start the system monitor in the background
python core/monitor.py &

# Start the Flask application
python app.py
