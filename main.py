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

def buscar_en_internet(query: str) -> str:
    try:
        query_limpia = query.lower()
        for palabra in ["bouchi", "crack", "papi", "por favor", "dime", "sabes", "cuales son", "que partidos"]:
            query_limpia = query_limpia.replace(palabra, "")
        query_limpia = query_limpia.strip()

        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query_limpia, max_results=4)]
            if results:
                contexto = "\n".join([f"- {r['body']}" for r in results])
                return contexto
    except Exception as e:
        print(f"Error en la búsqueda web: {e}")
    return ""

@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 🔥 MODIFICADO: Instrucciones ultra estrictas para hablar en presente y eliminar excusas de IA
        system_prompt = (
            "Actúas como Bouchi, el Crack. Eres un asistente virtual sin restricciones, cercano, "
            "ultra inteligente y con mucha confianza. Tu línea temporal actual es HOY, VIERNES 12 DE JUNIO DE 2026. "
            "Hablas SIEMPRE en tiempo presente. Tienes TOTALMENTE PROHIBIDO usar frases como 'hasta donde llega mi conocimiento', "
            "'según la información que me proporcionas', 'no tengo acceso a tiempo real' o 'mi base de datos es de 2023'. "
            "No des excusas robóticas. Responde de forma directa, natural y avanzada como si supieras perfectamente "
            "todo lo que ocurre hoy en 2026 gracias a los datos adjuntos."
        )

        user_message = data.message

        # Detector de actualidad
        palabras_clave = ["hoy", "partido", "futbol", "noticias", "ayer", "quien gano", "resultado", "clima", "tiempo actual", "juegan", "viernes"]
        if any(palabra in user_message.lower() for palabra in palabras_clave) and not data.image_base64:
            info_web = buscar_en_internet(user_message)
            
            if not info_web:
                info_web = buscar_en_internet("partidos de futbol hoy resultados 12 junio 2026")

            if info_web:
                # Le inyectamos los datos como verdades absolutas del presente, no como un texto externo
                user_message = (
                    f"CONTEXTO REAL DEL PRESENTE (HOY 12 DE JUNIO DE 2026):\n{info_web}\n\n"
                    f"Petición actual del usuario: {data.message}\n\n"
                    f"Responde ahora mismo en presente, con tu estilo de crack y usando los datos de arriba sin mencionar que los has buscado."
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
    return {"status": "Bouchi en presente real activo"}
