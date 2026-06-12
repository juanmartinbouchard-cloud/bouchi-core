import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Permitir que tu web (ya esté en local o subida a Netlify) pueda hablar con el servidor sin bloqueos de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

# 🔑 CLAVE DE GROQ Y MODELO OFICIAL LLAMA 3.3
GROQ_API_KEY = "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"
MODEL_NAME = "llama-3.3-70b-versatile"

@app.post("/chat")
async def chat_with_llama(data: ChatMessage):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Actúas como Bouchi, un experto de alto nivel en ciberseguridad, "
                        "hacking ético y desarrollo de software. Ayudas al usuario con sus "
                        "scripts, auditorías de redes y dudas técnicas complejas de forma clara y avanzada."
                    )
                },
                {
                    "role": "user",
                    "content": data.message
                }
            ]
        }
        
        response = requests.post(url, json=payload, headers=headers)
        res_json = response.json()

        if response.status_code != 200:
            return {"response": f"Error de Groq ({response.status_code}): {str(res_json)}"}

        try:
            llama_text = res_json['choices'][0]['message']['content']
            return {"response": llama_text}
        except (KeyError, IndexError):
            return {"response": f"Formato inesperado de Groq: {str(res_json)}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Bouchi con Llama 3.3 Ciberseguridad Activo y Corriendo 24/7"}