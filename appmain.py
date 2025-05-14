from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI()

@app.get("/")
def root():
    return {"status": "VoiceBot läuft"}

@app.post("/twilio/voice")
async def twilio_voice():
    twiml = """
    <Response>
        <Say>Willkommen bei LimaBravo Solutions. Wie kann ich Ihnen helfen?</Say>
    </Response>
    """
    return Response(content=twiml.strip(), media_type="text/xml")
