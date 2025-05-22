import os
from openai import OpenAI
from dotenv import load_dotenv
import requests

# 🔐 API-Keys laden
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY fehlt in .env")
if not ELEVEN_API_KEY:
    raise RuntimeError("❌ ELEVEN_API_KEY fehlt in .env")

# GPT-Client initialisieren
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔊 ElevenLabs Voice ID (Deutsch: z. B. Nicole)
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Du kannst auch andere IDs verwenden

# 🎤 Hauptfunktion: Transkript → GPT → Audio
async def process_transcript(transcript: str):
    print(f"📩 Eingehender Text an GPT: {transcript}")

    try:
        # 🧠 GPT-Antwort erzeugen
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du bist ein freundlicher deutschsprachiger Telefonassistent."},
                {"role": "user", "content": transcript}
            ],
            temperature=0.7,
            max_tokens=200
        )

        reply = response.choices[0].message.content.strip()
        print(f"🤖 GPT-Antwort: {reply}")

        # 🎧 TTS mit ElevenLabs
        tts_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVEN_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": reply,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
        )

        if tts_response.status_code == 200:
            with open("output.wav", "wb") as f:
                f.write(tts_response.content)
            print("🔉 TTS-Audio gespeichert als output.wav")

            # Optional: direkt abspielen
            try:
                import platform
                system = platform.system()
                if system == "Darwin":
                    os.system("afplay output.wav")       # macOS
                elif system == "Linux":
                    os.system("aplay output.wav")         # Linux
                elif system == "Windows":
                    import winsound
                    winsound.PlaySound("output.wav", winsound.SND_FILENAME)
            except Exception as e:
                print(f"🎧 Wiedergabe fehlgeschlagen: {e}")
        else:
            print("❌ TTS-Fehler:", tts_response.status_code, tts_response.text)

    except Exception as e:
        print(f"❌ GPT- oder TTS-Fehler:\n{e}")
