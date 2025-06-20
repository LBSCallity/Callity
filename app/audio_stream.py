import os
import json
import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.gpt_logic import process_transcript
from app.utils import save_temp_wav, convert_mulaw_to_wav

router = APIRouter()

@router.websocket("/ws/audio")
async def handle_audio_stream(websocket: WebSocket):
    await websocket.accept()
    print("🚀 WebSocket-Verbindung aufgebaut")

    # Deepgram-Stream verbinden
    dg_ws = await websockets.connect(
        "wss://api.deepgram.com/v1/listen",
        extra_headers={"Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
                       "Content-Type": "application/json"},
    )
    print("✅ Verbunden mit Deepgram")

    # Initiale Konfig senden
    await dg_ws.send(json.dumps({
        "type": "start",
        "encoding": "mulaw",
        "sample_rate": 8000,
        "channels": 1,
        "endpointing": True,
        "interim_results": False,
    }))

    state = {
        "chat_history": [],
        "is_playing_tts": False
    }

    try:
        async def receive_from_client():
            while True:
                data = await websocket.receive_bytes()
                if not state["is_playing_tts"]:
                    await dg_ws.send(data)

        async def receive_from_deepgram():
            async for msg in dg_ws:
                message = json.loads(msg)
                transcript = message.get("channel", {}).get("alternatives", [{}])[0].get("transcript")
                if transcript and len(transcript.strip()) > 3:
                    print(f"📄 🎤 Finales Transkript: {transcript}")
                    await process_transcript(transcript.strip(), state, websocket, dg_ws)
                else:
                    print(f"⚠️ Transkript zu kurz, ignoriert.")

        await asyncio.gather(
            receive_from_client(),
            receive_from_deepgram(),
        )

    except WebSocketDisconnect:
        print("🔌 WebSocket getrennt")
    except Exception as e:
        print(f"❌ Fehler im AudioStream: {e}")
    finally:
        await dg_ws.close()
        await websocket.close()
        print("🔚 Verbindung beendet")
