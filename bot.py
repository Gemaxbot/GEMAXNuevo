import os
import time
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from google import genai

# Configurar logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credenciales leídas de forma segura desde las variables de entorno de Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Nombre de usuario de tu bot en Telegram
BOT_USERNAME = "GemaxCrypto_bot"

# Inicializar cliente de Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def consultar_gemini(prompt_usuario):
    if not client:
        logger.error("La variable GEMINI_API_KEY no está configurada.")
        return "⚠️ Error de configuración: Falta la API Key de Gemini en Render."

    # Modelos principales y de respaldo con nombres estándar estables
    modelos_a_probar = ["gemini-2.5-flash", "gemini-1.5-flash"]

    # Instrucción abierta para responder cualquier tipo de pregunta
    prompt_completo = (
        "Eres un asistente virtual inteligente, útil y versátil en Telegram. "
        "Responde a cualquier pregunta o consulta que te hagan de forma clara, precisa, profesional y amigable, "
        "asegurándote de entregar información completa y coherente sin exceder los 700 caracteres. "
        f"Consulta: {prompt_usuario}"
    )

    for modelo in modelos_a_probar:
        try:
            logger.info(f"Intentando generar contenido con el modelo: {modelo}")
            response = client.models.generate_content(
                model=modelo,
                contents=prompt_completo
            )
            if response and response.text:
                texto_respuesta = response.text.strip()
                
                # Control de longitud por seguridad para Telegram
                if len(texto_respuesta) > 800:
                    texto_cortado = texto_respuesta[:797]
                    ultimo_punto = texto_cortado.rfind('.')
                    if ultimo_punto != -1:
                        texto_respuesta = texto_cortado[:ultimo_punto + 1]
                    else:
                        texto_respuesta = texto_cortado + "..."
                    
                return texto_respuesta
        except Exception as e:
            logger.error(f"Error al usar el modelo {modelo}: {e}")
            time.sleep(0.5) # Breve pausa antes de probar el siguiente modelo
            continue

    return "⚠️ Estoy experimentando alta demanda en este momento. Inténtame mencionar de nuevo en un segundito."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    bot_user = context.bot

    # 1. Ignorar mensajes privados (el bot solo opera en grupos y supergrupos)
    if chat.type == "private":
        return

    texto_mensaje = update.message.text or update.message.caption
    if not texto_mensaje:
        return

    # 2. Comprobar si el bot fue mencionado o si es una respuesta directa a su mensaje
    mencionado = False
    
    if BOT_USERNAME.lower() in texto_mensaje.lower():
        mencionado = True
        texto_mensaje = texto_mensaje.replace(f"@{BOT_USERNAME}", "").replace(BOT_USERNAME, "").strip()

    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == bot_user.id:
        mencionado = True

    if not mencionado:
        return

    logger.info(f"Mensaje atendido en grupo '{chat.title or chat.id}' de {user.first_name}: {texto_mensaje}")

    prompt_final = texto_mensaje if texto_mensaje else "Hola, ¿en qué te puedo ayudar hoy?"
    respuesta_ia = consultar_gemini(prompt_final)

    await update.message.reply_text(respuesta_ia)

def main():
    if not TELEGRAM_TOKEN:
        logger.error("La variable TELEGRAM_TOKEN no está configurada.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"Bot @{BOT_USERNAME} iniciado correctamente y abierto a cualquier consulta...")
    
    application.run_polling()

if __name__ == "__main__":
    main()
      
