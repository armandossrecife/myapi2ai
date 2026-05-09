import os
from flask import Flask, render_template

app = Flask(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# Injeta a variável em todos os templates
@app.context_processor
def inject_config():
    return dict(api_base_url=API_BASE_URL)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/rag")
def rag():
    return render_template("rag.html")

if __name__ == "__main__":
    port = int(os.getenv("FRONTEND_PORT", 5001))
    host = os.getenv("FRONTEND_HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=True)
