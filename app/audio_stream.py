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
                print("📡 Warte auf Deepgram-Transkript...")
                try:
                    async for message in dg_ws:
                        print("🧾 Deepgram-Rohantwort:", message)
                        try:
                            msg = json.loads(message)
                            transcript = msg.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                            is_final = msg.get("is_final", False)

                            if transcript:
                                print(f"📄 Transkript erkannt: {'(final)' if is_final else '(partial)'} → {transcript}")

                            if is_final and transcript:
                                await process_transcript(transcript, state)
                                await stream_tts_to_client(client_ws, "static/output.wav", state)

                        except Exception as e:
                            print("⚠️ Fehler beim Verarbeiten der Deepgram-Antwort:", e)
                except Exception as e:
                    print("❌ Fehler beim Empfang von Deepgram:", e)

            async def forward_audio():
                print("📥 Warte auf Audioframes...")
                frame_count = 0
                try:
                    while True:
                        message = await client_ws.receive()

                        if message["type"] == "websocket.receive":
                            if "bytes" in message:
                                if not state["is_playing_tts"]:
                                    frame_count += 1
                                    await dg_ws.send(message["bytes"])
                                    print(f"➡️ Frame {frame_count}: {len(message['bytes'])} Bytes")
                                else:
                                    print("🔇 Audio ignoriert – TTS läuft")

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
