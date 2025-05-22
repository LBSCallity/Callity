import os
import json
import base64
import asyncio
import websockets
from fastapi import WebSocket, APIRouter
from dotenv import load_dotenv
from app.gpt_logic import get_gpt_response

load_dotenv()
router = APIRouter()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

@router.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()

    uri = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=8000"

    try:
        async with websockets.connect(
            uri,
            extra_headers={"Authorization": ASSEMBLYAI_API_KEY}
        ) as aai_ws:

            async def sender():
                try:
                    while True:
                        msg = await websocket.receive_text()
                        data = json.loads(msg)

                        if data.get("event") == "media":
                            payload = data["media"]["payload"]
                            audio_data = base64.b64decode(payload)
                            await aai_ws.send(audio_data)

                        elif data.get("event") == "stop":
                            break
                except:
                    pass

            async def receiver():
                try:
                    async for message in aai_ws:
                        res = json.loads(message)
                        if res.get("message_type") == "FinalTranscript":
                            text = res.get("text", "").strip()
                            if text:
                                antwort = get_gpt_response(text)
                                # → GPT-Antwort ist verfügbar. Optional: Rückgabe als TTS.
                except:
                    pass

            await asyncio.gather(sender(), receiver())

    except:
        pass
