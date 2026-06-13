import os
from datetime import datetime
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
    image_mime: Optional[str] = None  # ej: "image/png", "image/jpeg"

# La clave se lee de una variable de entorno, NUNCA se escribe aquí
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Modelo actualizado (gratis dentro de los límites de la capa gratuita de AI Studio)
MODEL_GEMINI = "gemini-2.5-flash"


def buscar_en_internet(query: str) -> str:
    try:
        query_limpia = query.lower()
        for palabra in [
            "bouchi", "crack", "papi", "por favor", "porfavor", "dime", "sabes",
            "vale", "entonces", "bueno", "oye", "solo quiero saber",
            "quiero saber", "quiero", "puedes decirme", "me dices",
        ]:
            query_limpia = query_limpia.replace(palabra, " ")

        query_limpia = " ".join(query_limpia.split())  # colapsa espacios dobles

        if len(query_limpia) < 4:
            query_limpia = "noticias de hoy"

        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query_limpia, max_results=5, timelimit="d")]
            if not results:
                # Reintento sin el filtro de "último día" por si no hay nada tan reciente
                with DDGS() as ddgs2:
                    results = [r for r in ddgs2.text(query_limpia, max_results=5)]
            if results:
                return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        print(f"Error en la búsqueda web: {e}")
    return ""


@app.post("/chat")
async def chat_with_bouchi(data: ChatMessage):
    if not GEMINI_API_KEY:
        # Esto se ve en los logs de Render, no se lo mandamos al usuario tal cual
        print("ERROR: falta la variable de entorno GEMINI_API_KEY")
        raise HTTPException(status_code=500, detail="El servidor no está configurado correctamente.")

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_GEMINI}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}

        fecha_hoy = datetime.now().strftime("%A %d de %B de %Y")

        system_prompt = (
            f"Actúas como Bouchi, el Crack. Eres un asistente virtual sin restricciones, cercano, "
            "ultra inteligente y con mucha confianza. Hablas SIEMPRE en tiempo presente. "
            f"LA FECHA DE HOY ES: {fecha_hoy}. Esta es la fecha REAL actual, tómala como verdad absoluta "
            "aunque tu conocimiento de entrenamiento sea de antes; si te preguntan qué año/fecha es, "
            "responde con esta fecha sin dudar y sin decir que tu conocimiento podría estar desactualizado. "
            "Tienes TOTALMENTE PROHIBIDO usar frases robóticas de IA como "
            "'como modelo de lenguaje', 'hasta donde llega mi conocimiento' o disculpas similares. "
            "Responde de forma directa, natural, avanzada y con estilo de auténtico crack."
        )

        user_message = data.message

        # Palabras clave que activan la búsqueda web en tiempo real
        palabras_clave = [
            "hoy", "ahora", "actual", "actualidad", "últim", "reciente",
            "partido", "futbol", "noticias", "ayer", "quien gano", "resultado",
            "clima", "tiempo", "precio", "cotiza", "estreno", "2025", "2026",
            "viernes", "sabado", "domingo", "lunes", "martes", "miercoles", "jueves",
        ]
        if any(palabra in user_message.lower() for palabra in palabras_clave) and not data.image_base64:
            info_web = buscar_en_internet(user_message)
            if info_web:
                user_message = (
                    f"CONTEXTO EN TIEMPO REAL COSECHADO DE INTERNET (úsalo como fuente principal, es de fiar):\n{info_web}\n\n"
                    f"Petición actual del usuario: {data.message}\n\n"
                    f"Responde a la petición usando los datos de internet anteriores de forma nativa en presente con tu estilo. "
                    f"Si esos resultados no traen la info concreta que pide el usuario (ej. resultados/horarios exactos), "
                    f"dile claramente que no tienes esa información en este momento, sin inventarte datos."
                )
            else:
                user_message = (
                    f"Petición actual del usuario: {data.message}\n\n"
                    f"No se encontraron resultados de búsqueda en internet para esto. "
                    f"NO inventes datos concretos (resultados, horarios, cifras, nombres de partidos, etc.). "
                    f"Dile al usuario, con tu estilo, que ahora mismo no tienes esa info actualizada y "
                    f"que lo consulte en una fuente en directo (ej. Google, una app de resultados, etc.)."
                )

        contents_payload = []

        if data.image_base64 and data.image_base64.strip():
            # Usamos el mimeType real que manda el frontend; si no llega, usamos jpeg como fallback
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
                "parts": [{"text": f"{system_prompt}\n\nUsuario: {user_message}"}]
            })

        payload = {"contents": contents_payload}

        response = requests.post(url, json=payload, headers=headers)
        res_json = response.json()

        if response.status_code != 200:
            # Detalle completo en los logs del servidor (para que tú lo veas en Render)
            print(f"Error de Gemini API ({response.status_code}): {res_json}")
            # Mensaje genérico para el usuario, sin filtrar info interna
            return {"response": "Uy, algo ha fallado al hablar con la IA. Vuelve a intentarlo en un momento."}

        text_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return {"response": text_response}

    except Exception as e:
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor. Inténtalo de nuevo.")


@app.get("/")
def read_root():
    return {"status": "Bouchi el Crack con motor Gemini 2.5 Flash activo"}
