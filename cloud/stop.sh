#!/usr/bin/env bash
# Stops the app, the public link and the LLM server started by cloud/start.sh
pkill -f "streamlit run app.py" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
pkill -x ollama 2>/dev/null || true
echo "stopped"
