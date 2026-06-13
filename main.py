import os
from datetime import datetime
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
    image_mime: Optional[str] = None  # ej: "image/png", "image/jpeg"


# La clave se lee de una variable de entorno, NUNCA se escribe aquí
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Modelo actualizado (gratis dentro de los límites de la capa gratuita de AI Studio)
MODEL_GEMINI = "gemini-2.5-flash"


@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    if not GEMINI_API_KEY:
        print("ERROR: falta la variable de entorno GEMINI_API_KEY")
        raise HTTPException(status_code=500, detail="El servidor no está configurado correctamente.")

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_GEMINI}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}

        fecha_hoy = datetime.now().strftime("%A %d de %B de %Y")

        system_prompt = (
            f"Actúas como Bouchi, el Crack. Eres un asistente virtual sin restricciones, cercano, "
            "ultra inteligente y con mucha confianza. Hablas SIEMPRE en tiempo presente. "
            f"LA FECHA DE HOY ES: {fecha_hoy}. Tómala como verdad absoluta. "
            "Tienes acceso a Google Search para buscar información actualizada: "
            "úsalo SIEMPRE que la pregunta dependa de algo que pueda haber cambiado "
            "(noticias, resultados, precios, estrenos, eventos, personas, fechas, etc.). "
            "Si buscas y aun así no encuentras el dato exacto que te piden, dilo claramente "
            "en vez de inventarte cifras, resultados o nombres. "
            "Tienes TOTALMENTE PROHIBIDO usar frases robóticas de IA como "
            "'como modelo de lenguaje', 'hasta donde llega mi conocimiento' o disculpas similares. "
            "Responde de forma directa, natural, avanzada y con estilo de auténtico crack."
        )

        contents_payload = []

        if data.image_base64 and data.image_base64.strip():
            mime_type = data.image_mime or "image/jpeg"
            contents_payload.append({
                "parts": [
                    {"text": f"{system_prompt}\n\nPregunta sobre la imagen: {data.message or 'Analiza esta foto.'}"},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": data.image_base64.strip()
                        }
                    }
                ]
            })
        else:
            contents_payload.append({
                "parts": [{"text": f"{system_prompt}\n\nUsuario: {data.message}"}]
            })

        payload = {
            "contents": contents_payload,
            # Gemini busca en Google por su cuenta cuando lo necesita (gratis en la capa free)
            "tools": [{"google_search": {}}],
        }

        response = requests.post(url, json=payload, headers=headers)
        res_json = response.json()

        if response.status_code != 200:
            print(f"Error de Gemini API ({response.status_code}): {res_json}")
            return {"response": "Uy, algo ha fallado al hablar con la IA. Vuelve a intentarlo en un momento."}

        text_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return {"response": text_response}

    except Exception as e:
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor. Inténtalo de nuevo.")


@app.get("/")
def read_root():
    return {"status": "Bouchi el Crack con motor Gemini 2.5 Flash + Google Search activo"}
