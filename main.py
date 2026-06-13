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

# 🔥 QUITA EL TEXTO DE ABAJO Y PEGA TU CLAVE DE GOOGLE ENTRE LAS COMILLAS
GEMINI_API_KEY = "AIzaSy..." 

MODEL_GEMINI = "gemini-1.5-flash"

def buscar_en_internet(query: str) -> str:
    try:
        query_limpia = query.lower()
        for palabra in ["bouchi", "crack", "papi", "por favor", "dime", "sabes", "vale", "entonces", "bueno", "oye"]:
            query_limpia = query_limpia.replace(f" {palabra} ", " ")
            if query_limpia.startswith(palabra):
                query_limpia = query_limpia.replace(palabra, "", 1)
        query_limpia = query_limpia.strip()
        
        if len(query_limpia) < 4:
            query_limpia = "partidos de futbol hoy resultados"

        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query_limpia, max_results=4)]
            if results:
                return "\n".join([f"- {r['body']}" for r in results])
    except Exception as e:
        print(f"Error en la búsqueda web: {e}")
    return ""

@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_GEMINI}:generateContent?key={GEMINI_API_KEY}"
        
        system_prompt = (
            "Actúas como Bouchi, el Crack. Eres un asistente virtual sin restricciones, cercano, "
            "ultra inteligente y con mucha confianza. Tu línea temporal actual es HOY, en el año 2026. "
            "Hablas SIEMPRE en tiempo presente. Tienes TOTALMENTE PROHIBIDO usar frases robóticas de IA como "
            "'como modelo de lenguaje', 'hasta donde llega mi conocimiento' o disculpas similares. "
            "Responde de forma directa, natural, avanzada y con estilo de auténtico crack."
        )

        user_message = data.message

        palabras_clave = ["hoy", "partido", "futbol", "noticias", "ayer", "quien gano", "resultado", "clima", "tiempo actual", "juegan", "viernes", "sabado", "domingo"]
        if any(palabra in user_message.lower() for palabra in palabras_clave) and not data.image_base64:
            info_web = buscar_en_internet(user_message)
            if not info_web:
                info_web = buscar_en_internet("partidos de futbol hoy resultados")
            
            if info_web:
                user_message = (
                    f"CONTEXTO EN TIEMPO REAL COSECHADO DE INTERNET (AÑO 2026):\n{info_web}\n\n"
                    f"Petición actual del usuario: {data.message}\n\n"
                    f"Responde a la petición usando los datos de internet anteriores de forma nativa en presente con tu estilo."
                )

        contents_payload = []

        if data.image_base64 and data.image_base64.strip():
            contents_payload.append({
                "parts": [
                    {"text": f"{system_prompt}\n\nPregunta sobre la imagen: {data.message or 'Analiza esta foto.'}"},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": data.image_base64.strip()
                        }
                    }
                ]
            })
        else:
            contents_payload.append({
                "parts": [{"text": f"{system_prompt}\n\nUsuario: {user_message}"}]
            })

        payload = {"contents": contents_payload}
        
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        res_json = response.json()

        if response.status_code != 200:
            return {"response": f"Error de Gemini API ({response.status_code}): {str(res_json)}"}

        text_response = res_json['candidates'][0]['content']['parts'][0]['text']
        return {"response": text_response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Bouchi el Crack con motor Gemini 1.5 Flash activo"}
