# app/gpt_logic.py

import os
import requests
import subprocess
import aiofiles
import asyncio
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("ELEVEN_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL"  # Nicole

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY fehlt")
if not ELEVEN_API_KEY:
    raise RuntimeError("❌ ELEVEN_API_KEY fehlt")

client = OpenAI(api_key=OPENAI_API_KEY)

# Hintergrundfunktion zur TTS-Synthese + WAV-Konvertierung
def run_tts_pipeline(reply: str):
    try:
        print("🧠 Starte TTS-Pipeline für: ", reply[:80])

        # ElevenLabs TTS abrufen (MP3)
        tts_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVEN_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            },
            json={
                "text": reply,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.4,
                    "similarity_boost": 0.75
                }
            },
            timeout=15
        )

        if tts_response.status_code == 200:
            mp3_path = os.path.join("static", "output.mp3")
            with open(mp3_path, "wb") as f:
                f.write(tts_response.content)
            print("💾 TTS-Audio gespeichert als output.mp3")

            # Konvertiere zu WAV (PCM 16bit, 16kHz, Mono)
            wav_path = os.path.join("static", "output.wav")
            result = subprocess.run([
                "ffmpeg", "-y",
                "-i", mp3_path,
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                wav_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode == 0:
                print("🔁 WAV erfolgreich konvertiert")
            else:
                print("❌ ffmpeg Fehler:", result.stderr.decode())

        else:
            print("❌ TTS-Fehler:", tts_response.status_code, tts_response.text)

    except Exception as e:
        print("❌ Fehler in TTS-Pipeline:", e)


# Hauptfunktion – GPT-Interaktion und Start der TTS-Verarbeitung
async def process_transcript(transcript: str, state: dict):
    print(f"📩 Nutzer sagt: {transcript}")

    if "chat_history" not in state:
        state["chat_history"] = [
            {"role": "system", "content": "Du bist ein deutschsprachiger, natürlicher Telefonassistent. Antworte höflich, freundlich und kurz."}
        ]

    state["chat_history"].append({"role": "user", "content": transcript})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=state["chat_history"],
            temperature=0.6,
            max_tokens=400
        )

        reply = completion.choices[0].message.content.strip()
        print(f"🤖 GPT: {reply}")

        state["chat_history"].append({"role": "assistant", "content": reply})

        # Starte TTS-Konvertierung als separaten Task (nicht-blockierend)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_tts_pipeline, reply)

        # Chatverlauf begrenzen
        MAX_TURNS = 6
        if len(state["chat_history"]) > MAX_TURNS * 2 + 1:
            state["chat_history"] = state["chat_history"][:1] + state["chat_history\][-MAX_TURNS*2:]

    except Exception as e:
        print("❌ Fehler bei GPT/TTS:", e)
