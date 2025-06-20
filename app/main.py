# app/main.py
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response, PlainTextResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.audio_stream import handle_audio_stream
import json

app = FastAPI()

# CORS freigeben
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statische Dateien (z.B. TTS-Ausgabe)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/tts")
def get_tts():
    return FileResponse("static/output.wav", media_type="audio/wav")

@app.get("/debug-audio")
def get_debug_audio():
    return FileResponse(path="debug_capture.raw", filename="debug_capture.raw", media_type="application/octet-stream")

# WebSocket-Preflight (Test)
@app.get("/ws/audio")
async def ws_preflight():
    return {"status": "WebSocket bereit"}

# WebSocket-Audioverarbeitung
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket verbunden")
    await handle_audio_stream(websocket)
    print("❌ WebSocket getrennt")

# Vonage: Begrüßung + Weiterleitung an WebSocket
@app.api_route("/vonage/answer", methods=["GET", "POST"])
async def vonage_answer(request: Request):
    ncco = [
        {
            "action": "talk",
            "text": "Hallo, hier ist Callity. Wie kann ich dir helfen?",
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

# Health-Check
@app.get("/")
def root():
    return {"status": "Callity läuft", "websocket": "/ws/audio"}
