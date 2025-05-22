from fastapi import FastAPI, Request
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

from app.audio_stream import router as audio_router

# 🔄 .env laden (API-Keys etc.)
load_dotenv()

# 🚀 FastAPI starten
app = FastAPI()

# 🌐 CORS (offen für lokale Tests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧩 WebSocket einbinden
app.include_router(audio_router)

# 🗂️ Statische Dateien (für HTML/Audio)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 📤 TTS-WAV-Datei als Download/Stream bereitstellen
@app.get("/tts")
async def get_tts():
    tts_path = "output.wav"
    if os.path.exists(tts_path):
        return FileResponse(
            path=tts_path,
            media_type="audio/wav",
            filename="antwort.wav"
        )
    return {"error": "Keine TTS-Datei vorhanden"}

# (Optional: Später aktivieren, wenn Telefonintegration läuft)
# @app.post("/twilio/voice")
# async def twilio_voice(request: Request):
#     ...
