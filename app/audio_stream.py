import os
import json
import asyncio
import websockets
import aiohttp
import wave
import traceback
from fastapi import WebSocket

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

MIN_TRANSCRIPT_LENGTH = 4  # Mindestanzahl an Zeichen

async def forward_audio_to_deepgram(ws: WebSocket, dg_ws, state):
    try:
        while True:
            message = await ws.receive_bytes()
            if message:
                await dg_ws.send(message)
    except Exception as e:
        print("❌ Fehler beim Senden an Deepgram:", e)

async def receive_from_deepgram(dg_ws, state, on_final_transcript):
    try:
        async for msg in dg_ws:
            data = json.loads(msg)
            transcript_obj = data.get("channel", {}).get("alternatives", [{}])[0]
            transcript = transcript_obj.get("transcript", "")
            is_final = data.get("is_final", False)

            if transcript and is_final:
                print(f"📄 🎤 Finales Transkript: (final) → {transcript}")

                # Filter: zu kurz = ignorieren
                if len(transcript.strip()) < MIN_TRANSCRIPT_LENGTH:
                    print("⚠️ Transkript zu kurz, ignoriert.")
                    continue

                await on_final_transcript(transcript)

    except Exception as e:
        print("❌ Fehler beim Empfang von Deepgram:", e)
        traceback.print_exc()

async def audio_stream(ws: WebSocket, on_final_transcript):
    await ws.accept()
    print("🚀 WebSocket-Verbindung aufgebaut")

    try:
        deepgram_url = f"wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000"
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

        async with websockets.connect(deepgram_url, extra_headers=headers) as dg_ws:
            print("✅ Verbunden mit Deepgram")
            state = {}

            forward_task = asyncio.create_task(forward_audio_to_deepgram(ws, dg_ws, state))
            receive_task = asyncio.create_task(receive_from_deepgram(dg_ws, state, on_final_transcript))

            done, pending = await asyncio.wait(
                [forward_task, receive_task],
                return_when=asyncio.FIRST_EXCEPTION,
            )

            for task in pending:
                task.cancel()

    except Exception as e:
        print("❌ Deepgram-Verbindungsfehler:", e)
        traceback.print_exc()
    finally:
        await ws.close()
        print("🔚 Verbindung geschlossen")
