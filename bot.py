import os
import time
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from openai import OpenAI

# Configurar logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credenciales leídas de forma segura desde las variables de entorno de Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Nombre de usuario de tu bot en Telegram
BOT_USERNAME = "GemaxCrypto_bot"

# Configurar Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Configurar OpenRouter (utiliza la estructura de OpenAI)
openrouter_client = None
if OPENROUTER_API_KEY:
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

def consultar_ia(prompt_usuario):
    # Instrucción abierta para responder cualquier tipo de pregunta
    prompt_completo = (
        "Eres un asistente virtual inteligente, útil y versátil en Telegram. "
        "Responde a cualquier pregunta o consulta que te hagan de forma clara, precisa, profesional y amigable, "
        "asegurándote de entregar información completa y coherente sin exceder los 700 caracteres. "
        f"Consulta: {prompt_usuario}"
    )

    # 1. Intentar primero con Gemini
    if GEMINI_API_KEY:
        modelos_gemini = ['gemini-2.0-flash', 'gemini-flash']
        for modelo in modelos_gemini:
            try:
                logger.info(f"Intentando con Gemini ({modelo})...")
                gen_model = genai.GenerativeModel(modelo)
                response = gen_model.generate_content(prompt_completo)
                if response and response.text:
                    return procesar_respuesta(response.text.strip())
            except Exception as e:
                logger.warning(f"Gemini falló con el modelo {modelo}: {e}")
                continue

    # 2. Si Gemini falla o no está configurado, usar OpenRouter como respaldo
    if openrouter_client:
        try:
            logger.info("Intentando respaldo con OpenRouter...")
            completion = openrouter_client.chat.completions.create(
                model="deepseek/deepseek-chat",  # Puedes cambiarlo por otro modelo de OpenRouter si prefieres
                messages=[
                    {"role": "system", "content": "Eres un asistente virtual útil en Telegram de máximo 700 caracteres."},
                    {"role": "user", "content": prompt_usuario}
                ]
            )
            if completion.choices and completion.choices[0].message.content:
                return procesar_respuesta(completion.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"OpenRouter también falló: {e}")

    return "⚠️ Estoy experimentando alta demanda en este momento. Inténtame mencionar de nuevo en un segundito."

def procesar_respuesta(texto_respuesta):
    # Control de longitud por seguridad para Telegram
    if len(texto_respuesta) > 800:
        texto_cortado = texto_respuesta[:797]
        ultimo_punto = texto_cortado.rfind('.')
        if ultimo_punto != -1:
            texto_respuesta = texto_cortado[:ultimo_punto + 1]
        else:
            texto_respuesta = texto_cortado + "..."
    return texto_respuesta

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
    respuesta_ia = consultar_ia(prompt_final)

    await message.reply_text(respuesta_ia)

def main():
    if not TELEGRAM_TOKEN:
        logger.error("La variable TELEGRAM_TOKEN no está configurada.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"Bot @{BOT_USERNAME} iniciado correctamente con respaldo dual...")
    
    application.run_polling()

if __name__ == "__main__":
    main()
      
