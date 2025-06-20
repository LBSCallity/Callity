import os
import json
import asyncio
import websockets
import traceback
from fastapi import WebSocket

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
MIN_TRANSCRIPT_LENGTH = 4

async def forward_audio_to_deepgram(ws: WebSocket, dg_ws):
    try:
        while True:
            message = await ws.receive()

            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    await dg_ws.send(message["bytes"])
                elif "text" in message:
                    print("⚠️ Ungültige oder leere Audiodaten empfangen:", message["text"])
            elif message["type"] == "websocket.disconnect":
                print("❌ WebSocket vom Client getrennt")
                break
    except Exception as e:
        print("❌ Fehler beim Senden an Deepgram:", e)
        traceback.print_exc()

async def receive_from_deepgram(dg_ws, on_final_transcript):
    try:
        async for msg in dg_ws:
            data = json.loads(msg)
            transcript_obj = data.get("channel", {}).get("alternatives", [{}])[0]
            transcript = transcript_obj.get("transcript", "")
            is_final = data.get("is_final", False)

            if transcript and is_final:
                print(f"📄 🎤 Finales Transkript: → {transcript}")
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
        deepgram_url = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000"
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

        async with websockets.connect(deepgram_url, extra_headers=headers) as dg_ws:
            print("✅ Verbunden mit Deepgram")

            forward_task = asyncio.create_task(forward_audio_to_deepgram(ws, dg_ws))
            receive_task = asyncio.create_task(receive_from_deepgram(dg_ws, on_final_transcript))

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
