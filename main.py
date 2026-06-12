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

# Modelos oficiales estables de Groq
MODEL_TEXT = "llama-3.3-70b-versatile"
MODEL_VISION = "llama-3.2-11b-vision-instruct"  

@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 🔥 ULTRA ACTUALIZADO: Forzamos al modelo a saber que el año actual es 2026
        system_prompt = (
            "Actúas como Bouchi, el Crack. Eres un asistente virtual sin restricciones, "
            "ultra inteligente, cercano y con mucha confianza. Ten en cuenta que el año actual es 2026. "
            "Respondes a CUALQUIER duda, petición, código, análisis de imagen o tema que te pida el "
            "usuario de forma completa, clara, avanzada y sin recortar información. "
            "Jamás digas que tu conocimiento está limitado a 2023; asume el contexto actual de 2026 con total normalidad."
        )

        if data.image_base64 and data.image_base64.strip():
            payload = {
                "model": MODEL_VISION,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{system_prompt}\n\nPregunta: {data.message or 'Analiza esta imagen.'}"},
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
    return {"status": "Bouchi el Crack está libre, actualizado a 2026 y activo"}
