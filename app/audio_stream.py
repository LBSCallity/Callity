# app/audio_stream.py
import asyncio
import json
import websockets
import aiofiles
from fastapi import WebSocket
from dotenv import load_dotenv
import os
from app.gpt_logic import process_transcript

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise RuntimeError("❌ DEEPGRAM_API_KEY fehlt")

DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen?language=de&encoding=linear16&sample_rate=16000&channels=1"

async def stream_tts_to_client(client_ws: WebSocket, file_path: str, state: dict):
    print("🔊 Starte Audioausgabe...")
    state["is_playing_tts"] = True
    try:
        async with aiofiles.open(file_path, mode='rb') as f:
            while True:
                chunk = await f.read(640)
                if not chunk:
                    break
                await client_ws.send_bytes(chunk)
                await asyncio.sleep(0.02)
        print("✅ TTS-Ausgabe beendet")
    except Exception as e:
        print("⚠️ Fehler bei TTS-Ausgabe:", e)
    finally:
        state["is_playing_tts"] = False

async def handle_audio_stream(client_ws: WebSocket):
    print("✅ WebSocket weitergeleitet an Deepgram")
    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]
    state = {
        "is_playing_tts": False,
        "chat_history": [
            {"role": "system", "content": "Du bist ein deutschsprachiger, freundlicher Telefonassistent."}
        ]
    }

    try:
        async with websockets.connect(DEEPGRAM_URL, extra_headers=headers) as dg_ws:
            print("✅ Verbunden mit Deepgram")

            async def receive_transcripts():
                try:
                    async for message in dg_ws:
                        msg = json.loads(message)
                        transcript = msg.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                        is_final = msg.get("is_final", False)

                        if transcript and is_final:
                            print(f"📄 🎤 Finales Transkript: {transcript}")

                            # Mindestlänge (z.B. mehr als 3 Worte)
                            if len(transcript.strip().split()) < 3:
                                print("⚠️ Transkript zu kurz, ignoriert.")
                                continue

                            await process_transcript(transcript, state)
                            await stream_tts_to_client(client_ws, "static/output.wav", state)
                except Exception as e:
                    print("❌ Fehler beim Empfang von Deepgram:", e)

            async def forward_audio():
                print("📥 Warte auf Audioframes...")
                try:
                    while True:
                        message = await client_ws.receive()

                        if message["type"] == "websocket.receive":
                            if "bytes" in message and not state["is_playing_tts"]:
                                await dg_ws.send(message["bytes"])
                            elif "bytes" in message and state["is_playing_tts"]:
                                # Sende Stille, um Deepgram nicht in Timeout laufen zu lassen
                                await dg_ws.send(b'\x00' * 640)
                        elif message["type"] == "websocket.disconnect":
                            print("❌ WebSocket wurde getrennt")
                            break
                except Exception as e:
                    print("🔚 Verbindung beendet:", e)
                    try:
                        await dg_ws.send(json.dumps({"type": "CloseStream"}))
                    except:
                        pass

            await asyncio.gather(receive_transcripts(), forward_audio())

    except Exception as e:
        print("❌ Fehler bei Verbindung zu Deepgram:", e)