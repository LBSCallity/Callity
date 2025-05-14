from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Callity VoiceBot läuft"}

@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    twiml = """
    <Response>
        <Say>Willkommen bei Callity, Ihrem KI-gestützten Sprachassistenten.</Say>
    </Response>
    """
    return Response(content=twiml.strip(), media_type="text/xml")
