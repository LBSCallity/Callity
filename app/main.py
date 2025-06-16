from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import websockets
import os

# Config
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen?language=de"

# ✅ Nutze genau diese ngrok-URL oder eigene, falls konfiguriert
STREAM_URL = os.getenv("CALLITY_STREAM_URL", "wss://callity.onrender.com/ws/audio")

app = FastAPI()

# CORS freischalten
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📡 WebSocket-Preflight – wichtig für Vonage
@app.get("/ws/audio")
async def ws_preflight():
    return {"status": "WebSocket bereit"}

# 📶 WebSocket-Handler
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await websocket.accept()
    print("🚀 WebSocket verbunden")

    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]
    async with websockets.connect(DEEPGRAM_URL, extra_headers=headers) as dg_ws:

        async def receive_deepgram():
            async for message in dg_ws:
                print("🧾 Deepgram:", message)

        async def forward_audio():
            try:
                while True:
                    chunk = await websocket.receive_bytes()
                    await dg_ws.send(chunk)
            except:
                await dg_ws.send(json.dumps({"type": "CloseStream"}))

        await asyncio.gather(receive_deepgram(), forward_audio())

# 📞 Vonage Answer → NCCO ausliefern
@app.api_route("/vonage/answer", methods=["GET", "POST"])
async def vonage_answer(request: Request):
    ncco = [
        {"action": "talk", "text": "Hallo, hier ist Callity."},
        {"action": "stream", "streamUrl": [STREAM_URL]}
    ]
    print("✅ NCCO ausgeliefert:", STREAM_URL)
    return Response(content=json.dumps(ncco), media_type="application/json")

# 📊 Vonage Events loggen
@app.api_route("/vonage/event", methods=["GET", "POST"])
async def vonage_event(request: Request):
    try:
        data = await request.json() if request.method == "POST" else dict(request.query_params)
        print("📞 Event:", data)
        return PlainTextResponse("OK")
    except Exception as e:
        return PlainTextResponse(f"error: {e}", status_code=500)

# 🔍 Health Check
@app.get("/")
def root():
    return {"status": "Callity läuft lokal"}
