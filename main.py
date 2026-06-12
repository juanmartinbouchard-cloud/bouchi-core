import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str
    image_base64: Optional[str] = None

GROQ_API_KEY = "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"

MODEL_TEXT = "llama-3.3-70b-versatile"
MODEL_VISION = "llama-3.2-90b-vision-preview"  

@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "Actúas como Bouchi, un experto de alto nivel en ciberseguridad, "
            "hacking ético y desarrollo de software. Ayudas al usuario con sus "
            "scripts, auditorías de redes, análisis de imágenes/errores y dudas técnicas de forma clara y avanzada."
        )

        if data.image_base64 and data.image_base64.strip():
            payload = {
                "model": MODEL_VISION,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{system_prompt}\n\nPregunta sobre la imagen: {data.message or 'Analiza esta imagen detalladamente.'}"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{data.image_base64.strip()}"
                                }
                            }
                        ]
                    }
                ]
            }
        else:
            payload = {
                "model": MODEL_TEXT,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data.message}
                ]
            }
        
        response = requests.post(url, json=payload, headers=headers)
        res_json = response.json()

        if response.status_code != 200:
            return {"response": f"Error de Groq ({response.status_code}): {str(res_json)}"}

        return {"response": res_json['choices'][0]['message']['content']}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Bouchi Core Multimodal Listo y Corregido"}
