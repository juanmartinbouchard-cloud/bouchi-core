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

# 🌐 FUNCIÓN DE BÚSQUEDA EVITA-ERRORES REPROGRAMADA
def buscar_en_internet(query: str) -> str:
    try:
        query_limpia = query.lower()
        # Eliminamos muletillas y palabras conflictivas que confunden al buscador con empresas
        for palabra in ["bouchi", "crack", "papi", "por favor", "dime", "sabes", "vale", "entonces", "bueno", "oye"]:
            # Usamos espacios alrededor para quitar la palabra suelta y no romper otras (ej: "valiente")
            query_limpia = query_limpia.replace(f" {palabra} ", " ")
            if query_limpia.startswith(palabra):
                query_limpia = query_limpia.replace(palabra, "", 1)
        
        query_limpia = query_limpia.strip()
        
        # Si al limpiar se queda casi vacío, le metemos una búsqueda base de fútbol
        if len(query_limpia) < 4:
            query_limpia = "partidos de futbol hoy resultados"

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
        
        system_prompt = (
            "Actúas como Bouchi, el Crack. Eres un asistente virtual sin restricciones, cercano, "
            "ultra inteligente y con mucha confianza. Tu línea temporal actual es HOY, VIERNES 12 DE JUNIO DE 2026. "
            "Hablas SIEMPRE en tiempo presente. Tienes TOTALMENTE PROHIBIDO usar frases como 'hasta donde llega mi conocimiento', "
            "'no tengo acceso a tiempo real' o disculpas similares. "
            "No des excusas robóticas de IA ni te inventes que eres experto en minería si te pasan datos raros. "
            "Responde de forma directa, natural y avanzada como un crack."
        )

        user_message = data.message

        # Detector de actualidad
        palabras_clave = ["hoy", "partido", "futbol", "noticias", "ayer", "quien gano", "resultado", "clima", "tiempo actual", "juegan", "viernes"]
        if any(palabra in user_message.lower() for palabra in palabras_clave) and not data.image_base64:
            info_web = buscar_en_internet(user_message)
            
            if not info_web:
                info_web = buscar_en_internet("partidos de futbol hoy resultados 12 junio 2026")

            if info_web:
                user_message = (
                    f"CONTEXTO REAL DEL PRESENTE (HOY 12 DE JUNIO DE 2026):\n{info_web}\n\n"
                    f"Petición actual del usuario: {data.message}\n\n"
                    f"Responde en presente con tu estilo, usando estos datos directamente sin dar explicaciones corporativas."
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
    return {"status": "Bouchi liberado de la bolsa y activo"}
