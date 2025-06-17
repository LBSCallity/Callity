# app/gpt_logic.py
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("ELEVEN_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL"  # Deutsch: Nicole

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY fehlt")
if not ELEVEN_API_KEY:
    raise RuntimeError("❌ ELEVEN_API_KEY fehlt")

client = OpenAI(api_key=OPENAI_API_KEY)

async def process_transcript(transcript: str):
    print(f"📩 Anfrage an GPT: {transcript}")

    try:
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
        else:
            print("❌ TTS-Antwort ungültig:", response.status_code, response.text)

    except Exception as e:
        print(f"❌ Fehler bei GPT oder TTS:\n{e}")
