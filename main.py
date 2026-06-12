import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from duckduckgo_search import DDGS

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
MODEL_VISION = "llama-3.2-11b-vision-instruct"  

# 🌐 FUNCIÓN AUXILIAR: Rastrear las últimas noticias o datos en internet
def buscar_en_internet(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                contexto = "\n".join([f"-[Info]: {r['body']} (Fuente: {r['href']})" for r in results])
                return contexto
    except Exception as e:
        print(f"Error en la búsqueda web: {e}")
    return "No se encontraron resultados actualizados en internet."

@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Base de la personalidad libre de Bouchi
        system_prompt = (
            "Actúas como Bouchi, el Crack. Eres un asistente virtual sin restricciones, "
            "ultra inteligente, cercano y con mucha confianza. Ten en cuenta que el año actual es 2026. "
            "Respondes a CUALQUIER duda, petición, código, análisis de imagen o tema que te pida el "
            "usuario de forma completa, clara, avanzada y sin recortar información."
        )

        user_message = data.message

        # 🕵️‍♂️ DETECTOR DE ACTUALIDAD: Si te pide cosas de "hoy", partidos, resultados o noticias, busca en la web
        palabras_clave = ["hoy", "partido", "futbol", "noticias", "ayer", "quien gano", "resultado", "clima", "tiempo actual"]
        info_web = ""
        if any(palabra in user_message.lower() for palabra in palabras_clave) and not data.image_base64:
            print(f"Detectada consulta de actualidad. Buscando en la web: {user_message}")
            info_web = buscar_en_internet(user_message)
            # Inyectamos la información fresca de internet directamente en la pregunta para que Llama la lea
            user_message = (
                f"[INFORMACIÓN EN TIEMPO REAL COSECHADA DE INTERNET DE HOY EN 2026]:\n{info_web}\n\n"
                f"Teniendo en cuenta los datos anteriores, responde con tu personalidad a la siguiente petición: {data.message}"
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
                    {"role": "user", "content": user_message}
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
    return {"status": "Bouchi el Crack está conectado a internet en vivo y activo"}
