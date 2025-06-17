# app/gpt_logic.py
import os
import requests
import subprocess
from openai import OpenAI
from dotenv import load_dotenv

# 🔐 .env laden
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("ELEVEN_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL"  # Nicole

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY fehlt")
if not ELEVEN_API_KEY:
    raise RuntimeError("❌ ELEVEN_API_KEY fehlt")

client = OpenAI(api_key=OPENAI_API_KEY)

async def process_transcript(transcript: str):
    print(f"📩 Anfrage an GPT: {transcript}")

    try:
        # GPT-4-Antwort generieren
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Du bist ein deutschsprachiger, natürlicher Telefonassistent. Antworte höflich, freundlich und kurz."},
                {"role": "user", "content": transcript}
            ],
            temperature=0.6,
            max_tokens=200
        )

        reply = completion.choices[0].message.content.strip()
        print(f"🤖 GPT-Antwort: {reply}")

        # TTS von ElevenLabs als MP3
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
            }
        )

        if tts_response.status_code == 200:
            # MP3 speichern
            mp3_path = os.path.join("static", "output.mp3")
            with open(mp3_path, "wb") as f:
                f.write(tts_response.content)
            print("💾 TTS-Audio gespeichert als output.mp3")

            # Mit ffmpeg konvertieren in korrektes PCM-Format
            wav_path = os.path.join("static", "output.wav")
            result = subprocess.run([
                "ffmpeg", "-y",
                "-i", mp3_path,
                "-ar", "16000",  # 16kHz
                "-ac", "1",      # Mono
                "-f", "wav",
                wav_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode == 0:
                print("🔁 WAV konvertiert zu PCM 16bit 16kHz Mono")
            else:
                print("❌ Fehler bei ffmpeg-Konvertierung:")
                print(result.stderr.decode())

        else:
            print("❌ TTS-Fehler:", tts_response.status_code, tts_response.text)

    except Exception as e:
        print("❌ Fehler in process_transcript():", e)
