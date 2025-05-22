import os
from openai import OpenAI
from dotenv import load_dotenv

# 🔐 API-Key aus .env laden
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY fehlt in .env")

# 🧠 OpenAI-Client initialisieren
client = OpenAI(api_key=OPENAI_API_KEY)

# 📩 Eingehende Transkripte an GPT senden
async def process_transcript(transcript: str):
    print(f"📩 Eingehender Text an GPT: {transcript}")

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du bist ein freundlicher Telefonassistent."},
                {"role": "user", "content": transcript}
            ],
            temperature=0.7,
            max_tokens=200
        )

        reply = response.choices[0].message.content
        print(f"🤖 GPT-Antwort: {reply}")

    except Exception as e:
        print(f"❌ GPT-Fehler:\n{e}")
