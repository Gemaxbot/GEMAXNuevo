import os
import time
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

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

# Configurar la API de Gemini de forma clásica y estable
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def consultar_gemini(prompt_usuario):
    if not GEMINI_API_KEY:
        logger.error("La variable GEMINI_API_KEY no está configurada.")
        return "⚠️ Error de configuración: Falta la API Key de Gemini en Render."

    # Instrucción abierta para responder cualquier tipo de pregunta
    prompt_completo = (
        "Eres un asistente virtual inteligente, útil y versátil en Telegram. "
        "Responde a cualquier pregunta o consulta que te hagan de forma clara, precisa, profesional y amigable, "
        "asegurándote de entregar información completa y coherente sin exceder los 700 caracteres. "
        f"Consulta: {prompt_usuario}"
    )

    # Lista de modelos vigentes a probar para garantizar máxima compatibilidad
    modelos_a_probar = ['gemini-2.0-flash', 'gemini-flash']

    for modelo in modelos_a_probar:
        try:
            logger.info(f"Intentando generar contenido con el modelo: {modelo}")
            gen_model = genai.GenerativeModel(modelo)
            response = gen_model.generate_content(prompt_completo)
            
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
            continue

    return "⚠️ Error temporal generando la respuesta con la IA."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    bot_user = context.bot

    # 1. Ignorar chats privados
    if not chat or chat.type == "private":
        return

    # 2. Obtener el mensaje de forma segura
    message = update.effective_message
    if not message:
        return

    texto_mensaje = message.text or message.caption
    if not texto_mensaje:
        return

    # 3. Comprobar mención o respuesta directa al bot
    mencionado = False
    
    if BOT_USERNAME.lower() in texto_mensaje.lower():
        mencionado = True
        texto_mensaje = texto_mensaje.replace(f"@{BOT_USERNAME}", "").replace(BOT_USERNAME, "").strip()

    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot_user.id:
        mencionado = True

    if not mencionado:
        return

    logger.info(f"Mensaje atendido en grupo '{chat.title or chat.id}' de {user.first_name if user else 'Anónimo'}: {texto_mensaje}")

    prompt_final = texto_mensaje if texto_mensaje else "Hola, ¿en qué te puedo ayudar hoy?"
    respuesta_ia = consultar_gemini(prompt_final)

    await message.reply_text(respuesta_ia)

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
      
