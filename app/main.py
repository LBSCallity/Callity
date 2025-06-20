# app/main.py

import os
import json
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response, PlainTextResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.audio_stream import audio_stream

# Setup FastAPI App
app = FastAPI()

# CORS aktivieren (für WebSocket & lokale Tests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files (z. B. TTS-Audio-Dateien)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health-Check
@app.get("/")
def root():
    return {"status": "Callity läuft auf Render (WebSocket-fähig)"}

# TTS-Download-Endpunkte
@app.get("/tts")
def get_tts():
    return FileResponse("static/output.wav", media_type="audio/wav")

@app.get("/debug-audio")
def get_debug_audio():
    file_path = "debug_capture.raw"
    return FileResponse(path=file_path, filename="debug_capture.raw", media_type="application/octet-stream")

# WebSocket-Preflight
@app.get("/ws/audio")
async def ws_preflight():
    return {"status": "WebSocket verfügbar"}

# WebSocket-Handler
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    async def on_final_transcript(transcript: str):
        print(f"📩 Nutzer sagt: {transcript}")
        # Hier könntest du GPT/Response/TTS einbauen

    await audio_stream(websocket, on_final_transcript)

# Vonage NCCO
@app.api_route("/vonage/answer", methods=["GET", "POST"])
async def vonage_answer(request: Request):
    ncco = [
        {
            "action": "talk",
            "text": "Hallo, hier ist Callity. Wie kann ich Ihnen helfen?",
            "language": "de-DE",
            "voiceName": "Marlene",
            "style": 0
        },
        {
            "action": "connect",
            "endpoint": [
                {
                    "type": "websocket",
                    "uri": "wss://callity.onrender.com/ws/audio",
                    "content-type": "audio/l16;rate=16000",
                    "headers": {
                        "X-Session-ID": "callity-inbound"
                    }
                }
            ]
        }
    ]
    return Response(content=json.dumps(ncco), media_type="application/json")

# Vonage Events loggen
@app.api_route("/vonage/event", methods=["GET", "POST"])
async def vonage_event(request: Request):
    try:
        data = await request.json() if request.method == "POST" else dict(request.query_params)
        print("📞 Vonage-Event:", data)
        return PlainTextResponse("OK")
    except Exception as e:
        return PlainTextResponse(f"error: {e}", status_code=500)
