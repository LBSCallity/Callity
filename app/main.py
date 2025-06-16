from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import aiofiles
import os
import json
import asyncio
import websockets

# Eigene Module
from app.audio_stream import router as audio_router
from app.gpt_logic import process_transcript

# 🔐 .env laden
load_dotenv()

# 🚀 FastAPI starten
app = FastAPI()

# 🌐 CORS aktivieren
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📡 WebSocket-Route einbinden
app.include_router(audio_router)

# 📂 Statische Dateien (z. B. HTML/TTS-Player)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🔎 Health Check
@app.get("/")
def root():
    return {"status": "Callity läuft ✅"}

# 🎧 TTS-Audio abrufen
@app.get("/tts")
async def get_tts():
    path = "output.wav"
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/wav", filename="antwort.wav")
    return {"error": "Keine TTS-Datei vorhanden"}

# 📤 WAV-Datei hochladen für Test
@app.post("/upload_wav")
async def upload_wav(file: UploadFile = File(...)):
    temp_path = "temp_upload.wav"

    async with aiofiles.open(temp_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    print(f"📂 Datei empfangen: {file.filename} ({len(content)} Bytes)")

    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen?language=de"

    async def send_to_deepgram():
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        async with websockets.connect(DEEPGRAM_URL, extra_headers=headers) as ws:
            print("🔗 Deepgram verbunden")

            async def receiver():
                async for msg in ws:
                    print("📡 Deepgram:", msg)
                    j = json.loads(msg)
                    transcript = j.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                    if j.get("is_final") and transcript:
                        print(f"📄 Transkript erkannt: {transcript}")
                        await process_transcript(transcript)
                        await ws.send(json.dumps({"type": "CloseStream"}))
                        break

            async def sender():
                with open(temp_path, "rb") as f:
                    while chunk := f.read(3200):
                        await ws.send(chunk)
                        await asyncio.sleep(0.1)

            await asyncio.gather(receiver(), sender())

    try:
        await send_to_deepgram()
        return {"status": "verarbeitet", "output": "/tts"}
    except Exception as e:
        print("❌ Fehler bei Deepgram:", e)
        return {"error": str(e)}

# 📞 Vonage → Antwort mit NCCO
@app.api_route("/vonage/answer", methods=["GET", "POST"])
async def vonage_answer(request: Request):
    ncco = [
        {
            "action": "talk",
            "text": "Hallo, Sie sprechen mit dem Callity Voicebot."
        },
        {
            "action": "stream",
            "streamUrl": ["wss://ws.dev.echo.voice.vonage.com"]
        }
    ]
    return Response(content=json.dumps(ncco), media_type="application/json")

# 📊 Vonage Events empfangen (Call status, Fehler etc.)
@app.api_route("/vonage/event", methods=["GET", "POST"])
async def vonage_event(request: Request):
    try:
        if request.method == "POST":
            data = await request.json()
        else:
            data = dict(request.query_params)

        print("📞 Vonage-Event:", data)
        return PlainTextResponse("OK", status_code=200)

    except Exception as e:
        print("❌ Fehler im Event-Webhook:", e)
        return PlainTextResponse("error", status_code=500)
