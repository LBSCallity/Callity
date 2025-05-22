# ✅ main.py
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.audio_stream import router as audio_router

# .env laden
load_dotenv()

# App starten
app = FastAPI()

# WebSocket-Route einbinden
app.include_router(audio_router)

# CORS für lokale Tests / ngrok
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dummy-Webhook für SignalWire / Twilio
@app.post("/signalwire/voice")
async def signalwire_voice(request: Request):
    stream_url = "wss://6033-2a01-599-b0d-2fb3-1424-9313-a560-f56f.ngrok-free.app/ws/audio"

    response_xml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Response>
    <Connect>
        <Stream url=\"{stream_url}\" />
    </Connect>
</Response>
"""
    return PlainTextResponse(content=response_xml.strip(), media_type="text/xml")
