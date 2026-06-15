import os
import time
from datetime import datetime
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryItem(BaseModel):
    role: str  # "user" o "bouchi"
    text: str


class ChatMessage(BaseModel):
    message: str
    image_base64: Optional[str] = None
    image_mime: Optional[str] = None  # ej: "image/png", "image/jpeg"
    history: Optional[List[HistoryItem]] = None


# La clave se lee de una variable de entorno, NUNCA se escribe aquí
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Modelo actualizado (gratis dentro de los límites de la capa gratuita de AI Studio)
MODEL_GEMINI = "gemini-2.5-flash"

# Cuántos mensajes anteriores del chat se mandan como contexto (user+bouchi cuentan por separado)
MAX_HISTORY_MESSAGES = 12


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
            "IMPORTANTE: cada respuesta que escribes es ÚNICA y COMPLETA, no hay un 'segundo mensaje' después. "
            "Por eso, si necesitas buscar algo, hazlo ANTES de responder y da el resultado YA en esta misma "
            "respuesta. Tienes TOTALMENTE PROHIBIDO decir frases como 'dame un segundo', 'espera que lo "
            "compruebo', 'ahora lo busco' o 'te confirmo en un momento', porque eso deja al usuario sin "
            "respuesta. Si buscas y aun así no encuentras el dato exacto que te piden, dilo claramente "
            "en esta misma respuesta, en vez de inventarte cifras, resultados o nombres, y en vez de "
            "decir que vas a comprobarlo después. "
            "Tienes en cuenta el historial de la conversación para mantener el contexto y no "
            "repetirte ni contradecirte, pero si el usuario cambia de tema, sigues el tema nuevo "
            "sin aferrarte al anterior. "
            "Tienes TOTALMENTE PROHIBIDO usar frases robóticas de IA como "
            "'como modelo de lenguaje', 'hasta donde llega mi conocimiento' o disculpas similares. "
            "Responde de forma directa, natural, avanzada y con estilo de auténtico crack."
        )

        contents_payload = []

        # 1) Historial previo de la conversación (texto), si lo hay
        if data.history:
            historial_recortado = data.history[-MAX_HISTORY_MESSAGES:]
            for item in historial_recortado:
                gemini_role = "user" if item.role == "user" else "model"
                if item.text and item.text.strip():
                    contents_payload.append({
                        "role": gemini_role,
                        "parts": [{"text": item.text}]
                    })

        # 2) Mensaje actual del usuario (con o sin imagen)
        if data.image_base64 and data.image_base64.strip():
            mime_type = data.image_mime or "image/jpeg"
            contents_payload.append({
                "role": "user",
                "parts": [
                    {"text": data.message or "Analiza esta foto."},
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
                "role": "user",
                "parts": [{"text": data.message}]
            })

        payload = {
            "contents": contents_payload,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            # Gemini busca en Google por su cuenta cuando lo necesita (gratis en la capa free)
            "tools": [{"google_search": {}}],
        }

        # Reintentos: Gemini a veces devuelve 503 "high demand", que suele
        # resolverse solo en 1-2 segundos. Probamos hasta 3 veces antes de rendirnos.
        max_intentos = 3
        for intento in range(1, max_intentos + 1):
            response = requests.post(url, json=payload, headers=headers)
            res_json = response.json()

            if response.status_code == 200:
                break

            print(f"Intento {intento}/{max_intentos} - Error de Gemini API ({response.status_code}): {res_json}")

            if response.status_code == 503 and intento < max_intentos:
                time.sleep(1.5)
                continue

            return {"response": "Uy, algo ha fallado al hablar con la IA. Vuelve a intentarlo en un momento."}

        text_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return {"response": text_response}

    except Exception as e:
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor. Inténtalo de nuevo.")


@app.get("/")
def read_root():
    return {"status": "Bouchi el Crack con motor Gemini 2.5 Flash + Google Search + memoria activo"}
