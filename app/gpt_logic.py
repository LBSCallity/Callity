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
VOICE_ID = os.getenv("ELEVEN_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL"  # Deutsch: Nicole

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY fehlt")
if not ELEVEN_API_KEY:
    raise RuntimeError("❌ ELEVEN_API_KEY fehlt")

# GPT-Client
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔁 WAV konvertieren für Deepgram-Kompatibilität
async def convert_wav_to_pcm16():
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", "static/output.wav",
            "-ac", "1",
            "-ar", "16000",
            "-sample_fmt", "s16",
            "static/output_converted.wav"
        ], check=True)
        print("🔁 WAV konvertiert zu PCM 16bit 16kHz Mono")
    except subprocess.CalledProcessError as e:
        print("❌ Fehler bei ffmpeg-Konvertierung:", e)

# 🔁 Hauptfunktion: Text → GPT → TTS → WAV → konvertiert
async def process_transcript(transcript: str):
    print(f"📩 Anfrage an GPT: {transcript}")

    try:
        # 🧠 GPT-Antwort erzeugen
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

        # 🎧 ElevenLabs TTS
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVEN_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/wav"
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

        if response.status_code == 200:
            output_path = os.path.join("static", "output.wav")
            with open(output_path, "wb") as f:
                f.write(response.content)
            print("💾 TTS-Audio gespeichert unter static/output.wav")

            await convert_wav_to_pcm16()
        else:
            print("❌ TTS-Antwort ungültig:", response.status_code, response.text)

    except Exception as e:
        print(f"❌ Fehler bei GPT oder TTS:\n{e}")
