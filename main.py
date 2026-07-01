import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# La API key NUNCA va hardcodeada en el código. Se configura como variable de
# entorno en Render (Settings -> Environment -> GEMINI_API_KEY).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY en Render")

# gemini-1.5-flash-latest está apagado por Google (404 en todas las peticiones).
# gemini-3.5-flash es el modelo más inteligente disponible ahora mismo.
MODEL_GEMINI = "gemini-3.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_GEMINI}:generateContent"

MADRID_TZ = ZoneInfo("Europe/Madrid")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


class ChatTurn(BaseModel):
    role: str  # "user" o "model"
    text: str


class ChatMessage(BaseModel):
    message: str
    image_base64: Optional[str] = None
    history: Optional[List[ChatTurn]] = None


def build_system_prompt() -> str:
    ahora = datetime.now(MADRID_TZ)
    fecha_str = (
        f"{DIAS[ahora.weekday()]} {ahora.day} de {MESES[ahora.month - 1]} de "
        f"{ahora.year}, {ahora.strftime('%H:%M')} (hora peninsular española)"
    )

    return (
        "Actúas como Bouchi, el porros. Eres un asistente virtual cercano, ultra "
        "inteligente y con mucha confianza, que habla en español de España con "
        "estilo natural y directo, sin frases robóticas de IA tipo 'como modelo "
        "de lenguaje' o disculpas innecesarias.\n\n"
        f"AHORA MISMO es: {fecha_str}. Usa siempre esta fecha/hora como referencia "
        "real, nunca la inventes ni la calcules tú mismo.\n\n"
        "Tienes activada la búsqueda de Google como herramienta. Úsala siempre que "
        "te pregunten por algo actual (noticias, resultados, precios, eventos, "
        "clima) o de lo que no estés 100% seguro. Si buscando no encuentras el "
        "dato exacto, dilo claramente en vez de inventarte información."
    )


@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    try:
        contents_payload = []

        if data.history:
            for turn in data.history[-20:]:
                role = "model" if turn.role == "model" else "user"
                contents_payload.append({
                    "role": role,
                    "parts": [{"text": turn.text}],
                })

        if data.image_base64 and data.image_base64.strip():
            contents_payload.append({
                "role": "user",
                "parts": [
                    {"text": data.message or "Analiza esta foto."},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": data.image_base64.strip(),
                        }
                    },
                ],
            })
        else:
            contents_payload.append({
                "role": "user",
                "parts": [{"text": data.message}],
            })

        payload = {
            "systemInstruction": {"parts": [{"text": build_system_prompt()}]},
            "contents": contents_payload,
            "tools": [{"google_search": {}}],
        }

        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        res_json = response.json()

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Error de Gemini API ({response.status_code}): {res_json}",
            )

        candidates = res_json.get("candidates")
        if not candidates:
            feedback = res_json.get("promptFeedback", {})
            raise HTTPException(
                status_code=502,
                detail=f"Gemini no devolvió respuesta (posible bloqueo de seguridad): {feedback}",
            )

        parts = candidates[0]["content"]["parts"]
        text_response = "".join(p.get("text", "") for p in parts if "text" in p)

        return {"response": text_response}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"status": f"Bouchi el Crack con motor {MODEL_GEMINI} activo"}
