import os
import logging
from google.cloud import speech
from google.oauth2 import service_account
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

# Configurar el registro de errores
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ruta al archivo de credenciales JSON
CREDENTIALS_FILE = 'credencialesfinal.json'

# Configurar el cliente de Google Speech-to-Text con las credenciales
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
client = speech.SpeechClient(credentials=credentials)

# Token del bot de Telegram
TELEGRAM_TOKEN = '7367523664:AAHBXabGHZV3DTG8Ko0ewLmv4Q8SZ5NR-mw'

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Envía un mensaje de audio para transcribir.')

async def handle_audio(update: Update, context: CallbackContext) -> None:
    file = await context.bot.get_file(update.message.voice.file_id)
    file_path = 'audio.ogg'
    await file.download_to_drive(file_path)

    # Convertir el archivo OGG a WAV
    os.system('ffmpeg -i audio.ogg audio.wav')

    # Verificar si el archivo WAV se creó correctamente
    if not os.path.exists('audio.wav'):
        await update.message.reply_text('Hubo un problema al convertir el archivo de audio.')
        return

    # Leer el archivo de audio
    with open('audio.wav', 'rb') as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,  # Cambiado a 48000 para coincidir con la tasa de muestreo del archivo WAV
        language_code='es-ES'
    )

    response = client.recognize(config=config, audio=audio)

    # Obtener la transcripción
    for result in response.results:
        await update.message.reply_text(result.alternatives[0].transcript)

async def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text('Ocurrió un error, por favor intenta nuevamente.')

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.VOICE, handle_audio))
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
