# ./app.py
from flask import Flask, render_template, request, redirect, url_for
from dotenv import set_key, load_dotenv
import os
from livereload import Server

app = Flask(__name__)
ENV_FILE = ".env"

def get_env(key):
    return os.getenv(key, "")

@app.route("/", methods=["GET", "POST"])
def index():
    
    return render_template(
        "index.html",
    )

if __name__ == "__main__":
    server = Server(app.wsgi_app)
    server.watch("**/*.*")
    server.serve(port=5000, debug=True)