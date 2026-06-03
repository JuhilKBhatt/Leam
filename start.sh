#!/bin/bash

# Start the system monitor in the background
python utilities/system_monitor.py &

# Start the Flask application
python app.py
