from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import websockets
import os

# 🔐 Deepgram-Key laden
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen?language=de"

# WebSocket-URL für Vonage (Render-Host)
VONAGE_WS_URL = "wss://callity.onrender.com/ws/audio"

# App initialisieren
app = FastAPI()

# CORS erlauben
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Preflight-Check für Vonage (optional, hilft bei Debug)
@app.get("/ws/audio")
async def ws_preflight():
    return {"status": "WebSocket verfügbar"}

# Haupt-WebSocket-Handler
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await websocket.accept()
    print("🚀 WebSocket-Verbindung aufgebaut")

    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]
    async with websockets.connect(DEEPGRAM_URL, extra_headers=headers) as dg_ws:

        async def receive_from_deepgram():
            async for message in dg_ws:
                print("🧾 Deepgram:", message)

        async def forward_audio():
            try:
                while True:
                    chunk = await websocket.receive_bytes()
                    await dg_ws.send(chunk)
            except Exception as e:
                print("🔚 WebSocket beendet:", e)
                await dg_ws.send(json.dumps({"type": "CloseStream"}))

        await asyncio.gather(receive_from_deepgram(), forward_audio())

# NCCO-Endpoint für Vonage → WebSocket-Verbindung aufbauen
@app.api_route("/vonage/answer", methods=["GET", "POST"])
async def vonage_answer(request: Request):
    ncco = [
        {
            "action": "talk",
            "text": "Hallo! Hier spricht Callity. Einen Moment bitte, ich höre zu.",
            "language": "de-DE",
            "voiceName": "Marlene"
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


# Call-Status-Events von Vonage (optional für Logs)
@app.api_route("/vonage/event", methods=["GET", "POST"])
async def vonage_event(request: Request):
    try:
        data = await request.json() if request.method == "POST" else dict(request.query_params)
        print("📞 Vonage-Event:", data)
        return PlainTextResponse("OK")
    except Exception as e:
        return PlainTextResponse(f"error: {e}", status_code=500)

# Root-Endpoint für Health-Check
@app.get("/")
def root():
    return {"status": "Callity läuft auf Render (WebSocket-fähig)"}
