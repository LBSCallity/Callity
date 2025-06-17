# app/audio_stream.py
import asyncio
import json
import websockets
from fastapi import WebSocket
from dotenv import load_dotenv
import os
from app.gpt_logic import process_transcript

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise RuntimeError("❌ DEEPGRAM_API_KEY fehlt")

DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen?language=de"

async def handle_audio_stream(client_ws: WebSocket):
    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]

    try:
        await client_ws.accept()
        print("✅ WebSocket akzeptiert")

        async with websockets.connect(DEEPGRAM_URL, extra_headers=headers) as dg_ws:
            print("✅ Verbunden mit Deepgram")

            async def receive_transcripts():
                print("📡 Warte auf Deepgram-Transkript...")
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
                print("📥 Warte auf Audioframes...")
                try:
                    while True:
                        message = await client_ws.receive()
                        if message["type"] == "websocket.receive":
                            if "bytes" in message:
                                await dg_ws.send(message["bytes"])
                                print(f"➡️ Gesendet: {len(message['bytes'])} Bytes")
                            else:
                                print("⚠️ Kein bytes-Frame:", message)
                        elif message["type"] == "websocket.disconnect":
                            print("❌ WebSocket wurde getrennt")
                            break
                except Exception as e:
                    print("🔚 Verbindung beendet:", e)
                    await dg_ws.send(json.dumps({"type": "CloseStream"}))

            await asyncio.gather(receive_transcripts(), forward_audio())

    except Exception as e:
        print("❌ Fehler bei Verbindung zu Deepgram:", e)
