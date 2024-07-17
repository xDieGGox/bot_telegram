import os
import logging
import psycopg2
from google.cloud import speech
from google.oauth2 import service_account
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
import re

# Configurar el registro de errores
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Datos de la base de datos PostgreSQL
DB_HOST = '35.212.182.178'
DB_NAME = 'obesidadbd'
DB_USER = 'postgres'
DB_PASS = 'postgres'

# Token del bot de Telegram
TELEGRAM_TOKEN = '7367523664:AAHBXabGHZV3DTG8Ko0ewLmv4Q8SZ5NR-mw'

# Ruta al archivo de credenciales JSON
CREDENTIALS_FILE = 'credenciales.json'

# Configurar el cliente de Google Speech-to-Text con las credenciales
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
client = speech.SpeechClient(credentials=credentials)

# Conectar a la base de datos PostgreSQL
def connect_db():
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return connection
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return None

# Variables para controlar el flujo de diálogo
pending_audio = {}
user_data = {}

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    pending_audio[user_id] = False
    await update.message.reply_text(
        'Por favor envía tus datos en el siguiente formato:\n'
        'Cédula, Nombres, Apellidos, Teléfono, Correo, Edad\n'
        '(por ejemplo: 12345678, Juan, Pérez, 1234567890, juan@example.com, 25).'
    )

async def handle_text(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    text = update.message.text

    if pending_audio.get(user_id, False):
        await update.message.reply_text('Ya has proporcionado tus datos. Por favor, envía un mensaje de audio para transcribir.')
        return

    try:
        cedula, nombres, apellidos, telefono, correo, edad = [x.strip() for x in text.split(',', 5)]
    except ValueError:
        await update.message.reply_text(
            'Por favor envía tus datos en el formato correcto:\n'
            'Cédula, Nombres, Apellidos, Teléfono, Correo, Edad\n'
            '(por ejemplo: 12345678, Juan, Pérez, 1234567890, juan@example.com, 25).'
        )
        return

    connection = connect_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO \"Usuario\" (cedula, nombres, apellidos, telefono, correo, edad) VALUES (%s, %s, %s, %s, %s, %s)",
                (cedula, nombres, apellidos, telefono, correo, edad)
            )
            connection.commit()
            cursor.close()
            connection.close()

            # Guardar datos del usuario en memoria
            user_data[user_id] = {
                'cedula': cedula,
                'nombres': nombres,
                'apellidos': apellidos,
                'telefono': telefono,
                'correo': correo,
                'edad': edad
            }

            pending_audio[user_id] = True
            await update.message.reply_text('Datos guardados exitosamente. Ahora, por favor, envía un mensaje de audio para transcribir.')
        except Exception as e:
            logger.error(f"Error al insertar datos en la base de datos: {e}")
            await update.message.reply_text('Hubo un error al guardar los datos, por favor intenta nuevamente.')
    else:
        await update.message.reply_text('No se pudo conectar a la base de datos, por favor intenta más tarde.')

async def handle_audio(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    if not pending_audio.get(user_id, False):
        await update.message.reply_text('Por favor, primero envía tus datos en el formato solicitado.')
        return

    file = await context.bot.get_file(update.message.voice.file_id)
    file_path = f'audio_{user_id}.ogg'
    await file.download_to_drive(file_path)

    # Convertir el archivo OGG a WAV
    wav_path = f'audio_{user_id}.wav'
    os.system(f'ffmpeg -i {file_path} {wav_path}')

    # Verificar si el archivo WAV se creó correctamente
    if not os.path.exists(wav_path):
        await update.message.reply_text('Hubo un problema al convertir el archivo de audio.')
        return

    # Leer el archivo de audio
    with open(wav_path, 'rb') as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,
        language_code='es-ES'
    )

    # Realizar la transcripción
    response = client.recognize(config=config, audio=audio)

    # Obtener la transcripción
    transcription = ""
    
    for result in response.results:
        transcription += result.alternatives[0].transcript.lower() + "\n"
    
    await update.message.reply_text(f'Transcripción: {transcription}')

    # Extraer parámetros
    peso = None
    altura = None
    entre_comidas = None
    historial_familiar = None
    comidas_caloricas = None

    # Analizar la transcripción para extraer los parámetros
    if 'peso' in transcription:
        peso_match = re.search(r'peso es (\d+)', transcription)
        if peso_match:
            peso = peso_match.group(1)

    if 'altura' in transcription:
        altura_match = re.search(r'altura es (\d+\.\d+)', transcription)
        if altura_match:
            altura = altura_match.group(1)

    if 'entre comidas' in transcription:
        entre_match = re.search(r'entre comidas es (\d+\.\d+)', transcription)
        if entre_match:
            entre_comidas = entre_match.group(1)

    if 'historial familiar' in transcription:
        if 'sí' in transcription:
            historial_familiar = 'si'
        else:
            historial_familiar = 'no'

    if 'comidas calóricas' in transcription:
        if 'sí' in transcription:
            comidas_caloricas = 'si'
        else:
            comidas_caloricas = 'no'

    # Actualizar la base de datos
    connection = connect_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE \"Usuario\" SET peso = %s, altura = %s, entrecomidas = %s, historialfamiliar = %s, comidascaloricas = %s WHERE cedula = %s",
                (peso, altura, entre_comidas, historial_familiar, comidas_caloricas, user_data[user_id]['cedula'])
            )
            connection.commit()
            cursor.close()
            connection.close()

            await update.message.reply_text('Datos actualizados correctamente en la base de datos.')
        except Exception as e:
            logger.error(f"Error al actualizar datos en la base de datos: {e}")
            await update.message.reply_text('Hubo un error al actualizar los datos en la base de datos, por favor intenta nuevamente.')
    else:
        await update.message.reply_text('No se pudo conectar a la base de datos, por favor intenta más tarde.')

    pending_audio[user_id] = False


async def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text('Ocurrió un error, por favor intenta nuevamente.')

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_audio))
    application.add_error_handler(error_handler)

    # Confirmar la conexión a la base de datos al iniciar el bot
    if connect_db():
        logger.info('Conexión a la base de datos exitosa.')
    else:
        logger.error('No se pudo conectar a la base de datos.')

    application.run_polling()

if __name__ == '__main__':
    main()
