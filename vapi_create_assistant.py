import requests

# 🔐 Dein Vapi API Key
VAPI_API_KEY = "93bf49c0-b1ad-4269-a69b-e64cb4128514"

# 🌐 Dein Callity WebSocket-Server
CALLITY_WS_URL = "wss://callity.onrender.com/ws/audio"

# ✅ Assistant-Daten nach neuer API
assistant_data = {
    "name": "Callity WebSocket",
    "voice": "echo-openai",  # Gültige Stimme
    "websocketUrl": CALLITY_WS_URL  # Neue Schreibweise
}

# 📡 API-Aufruf
response = requests.post(
    "https://api.vapi.ai/assistant",  # Beachte: kein /v1!
    headers={
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    },
    json=assistant_data
)

print("Status:", response.status_code)
print("Antwort:", response.json())
