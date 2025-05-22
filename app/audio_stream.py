import asyncio
import json
import base64
import websockets
from fastapi import WebSocket, APIRouter
from dotenv import load_dotenv
import os

from app.gpt_logic import process_transcript

# .env laden
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise RuntimeError("❌ DEEPGRAM_API_KEY fehlt")

DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen?language=de"

router = APIRouter()

@router.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await websocket.accept()
    await handle_audio_stream(websocket)

async def handle_audio_stream(client_ws: WebSocket):
    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]

    try:
        async with websockets.connect(DEEPGRAM_URL, extra_headers=headers) as dg_ws:
            print("✅ Verbunden mit Deepgram")

            async def receive_transcripts():
                async for message in dg_ws:
                    print("🧾 Deepgram-Rohantwort:", message)
                    try:
                        msg = json.loads(message)
                        transcript = msg.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                        is_final = msg.get("is_final", False)

                        if transcript:
                            print(f"📄 Transkript erkannt: {'(final)' if is_final else '(partial)'} → {transcript}")

                        if is_final and transcript:
                            await process_transcript(transcript)

                    except Exception as e:
                        print("⚠️ Fehler beim Verarbeiten der Deepgram-Antwort:", e)

            async def forward_audio():
                try:
                    while True:
                        audio_chunk = await client_ws.receive_bytes()
                        await dg_ws.send(audio_chunk)
                        print(f"➡️ Gesendet: {len(audio_chunk)} Bytes")
                except Exception as e:
                    print("🔚 Verbindung beendet:", e)
                    await dg_ws.send(json.dumps({"type": "CloseStream"}))

            await asyncio.gather(receive_transcripts(), forward_audio())

    except Exception as e:
        print("❌ Fehler bei Verbindung zu Deepgram:", e)
