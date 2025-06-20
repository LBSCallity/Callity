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

async def stream_tts_to_client(client_ws: WebSocket, dg_ws, file_path: str, state: dict):
    print("🔊 Starte Audioausgabe...")
    state["is_playing_tts"] = True
    try:
        async with aiofiles.open(file_path, mode='rb') as f:
            chunk = await f.read(640)
            while chunk:
                await client_ws.send_bytes(chunk)
                await asyncio.sleep(0.02)
                chunk = await f.read(640)
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
            {"role": "system", "content": "Du bist ein deutschsprachiger, natürlicher Telefonassistent. Antworte höflich, freundlich und kurz."}
        ]
    }

    try:
        async with websockets.connect(DEEPGRAM_URL, extra_headers=headers) as dg_ws:
            print("✅ Verbunden mit Deepgram")

            async def receive_transcripts():
                print("📡 Warte auf Deepgram-Transkripte...")
                try:
                    async for message in dg_ws:
                        msg = json.loads(message)
                        transcript = msg.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                        is_final = msg.get("is_final", False)

                        if transcript:
                            print(f"📄 🎤 Finales Transkript: {'(final)' if is_final else '(partial)'} → {transcript}")

                        if is_final and transcript:
                            if len(transcript.strip().split()) < 3:
                                print("⚠️ Transkript zu kurz, ignoriert.")
                                continue

                            await process_transcript(transcript, state)

                            # 🧠 Warte auf TTS-Datei + Halte Deepgram/Vonage wach
                            silent_chunk = b'\x00' * 640
                            for _ in range(50):  # max 10 Sek
                                if os.path.exists("static/output.wav"):
                                    break
                                await client_ws.send_bytes(silent_chunk)
                                await dg_ws.send(silent_chunk)
                                await asyncio.sleep(0.2)

                            await stream_tts_to_client(client_ws, dg_ws, "static/output.wav", state)

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
                            elif "text" in message:
                                print(f"⚠️ Textframe ignoriert: {message['text']}")

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
