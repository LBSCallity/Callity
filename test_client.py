import asyncio
import websockets

async def send_audio():
    uri = "ws://localhost:8000/ws/audio"
    async with websockets.connect(uri) as ws:
        with open("test_dg.wav", "rb") as f:
            while chunk := f.read(3200):  # ca. 100ms Audio @16kHz
                await ws.send(chunk)
                await asyncio.sleep(0.1)  # simuliert Echtzeit
        print("✅ Audio erfolgreich gesendet")

asyncio.run(send_audio())
