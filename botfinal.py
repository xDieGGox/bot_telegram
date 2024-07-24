import os
import logging
import psycopg2
from google.cloud import speech
from google.oauth2 import service_account
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
import re
import requests
import uuid

# Configurar el registro de errores
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Datos de la base de datos PostgreSQL
DB_HOST = '35.209.157.211' #104.197.213.99
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = 'postgres'

# Token del bot de Telegram
TELEGRAM_TOKEN = '7367523664:AAHBXabGHZV3DTG8Ko0ewLmv4Q8SZ5NR-mw'

# Ruta al archivo de credenciales JSON
CREDENTIALS_FILE = 'credencialesfinal.json'

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

# Function to connect to the database and retrieve data
def get_medic_data():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port="5432"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM medicos")  # Adjust the query according to your table schema
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_schedules_for_medic(medic_id):
    conn = connect_db()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, fecha, hora, estado FROM turnos WHERE estado = true AND id_medico = %s", (medic_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows



def send_to_api(edad, peso, historial_familiar, fav, caec):
    url = 'http://34.16.228.101:8001/predecirIOJson/'
    headers = {'Content-Type': 'application/json'}
    data = {
        "EDAD": edad,
        "PESO": peso,
        "HISTORIAL_FAMILIAR": historial_familiar,
        "FAV": fav,
        "CAEC": caec
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None


def update_schedule_status(schedule_id, user_id):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE turnos SET estado = %s, cedula = %s WHERE id = %s", (False,user_data[user_id]['cedula'], schedule_id))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error al actualizar el estado del horario en la base de datos: {e}")
        return False

# Variables para controlar el flujo de diálogo
pending_audio = {}
user_data = {}
medic_data = get_medic_data()
id_usuario = 1

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
        await update.message.reply_text('Ya has proporcionado tus datos. Por favor, envía un mensaje de audio para transcribir con el siguiente formato: Mi peso es 70, mi altura es 1.75, entre comidas es a veces, tengo historial familiar sí, consumo comidas calóricas no.')
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
                "INSERT INTO usuarios (cedula, nombres, apellidos, telefono, correo, edad) VALUES (%s, %s, %s, %s, %s, %s)",
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
    unique_id = str(uuid.uuid4())
    file_path = f'audio_{unique_id}.ogg'
    #file_path = f'audio_{user_id}.ogg'
    await file.download_to_drive(file_path)

    # Convertir el archivo OGG a WAV
    wav_path = f'audio_{unique_id}.wav'
    #wav_path = f'audio_{user_id}.wav'
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
    entre_comidas = None ## no -  A veces - Frecuentemente -- siempres 
    historial_familiar = None  ## si o no
    comidas_caloricas = None ## si o no

    # Analizar la transcripción para extraer los parámetros
    if 'peso' in transcription:
        peso_match = re.search(r'peso es (\d+)', transcription)
        if peso_match:
            peso = float(peso_match.group(1))

    if 'altura' in transcription:
        altura_match = re.search(r'altura es (\d+\.\d+)', transcription)
        if altura_match:
            altura = float(altura_match.group(1))

    if 'entre comidas' in transcription:
        entre_match = re.search(r'entre comidas es (\w+)', transcription)
        if entre_match:
            entre_comidas = entre_match.group(1).lower()
            if entre_comidas not in ['nunca', 'a veces', 'frecuentemente', 'siempre']:
                entre_comidas = None

    if 'historial familiar es sí' in transcription:                   
        historial_familiar = True
        hfapi = "yes"

    if 'historial familiar es no' in transcription:                   
        historial_familiar = False
        hfapi = "no"

    if 'comidas calóricas es sí' in transcription:
        comidas_caloricas = True
        ccapi = "yes"

    if 'comidas calóricas es no' in transcription:
        comidas_caloricas = False
        ccapi = "no"

    if any(param is None for param in [peso, altura, entre_comidas, historial_familiar, comidas_caloricas]):
        await update.message.reply_text(
            'No se pudieron extraer todos los datos. Asegúrate de decir los valores correctamente en el formato indicado.'
        )
        return

    #ecapi = "Sometimes"
    if entre_comidas == "nunca":
        ecapi = "no"

    if entre_comidas == "a veces":
        ecapi = "Sometimes"

    if entre_comidas == "frecuentemente":
        ecapi = "Frequently"

    if entre_comidas == "siempre":
        ecapi = "Always"

    
    # Enviar datos a la API y obtener la respuesta
    api_response = send_to_api(user_data[user_id]['edad'], peso, hfapi, ccapi, ecapi)

    if not api_response:
        await update.message.reply_text('Hubo un problema al comunicarse con la API.')
        return

    # Obtener la predicción y certeza de la respuesta de la API
    prediccion = api_response.get('Predicción', [None])[0]
    resultado = api_response.get('Resultado', [None])[0]
    certeza = api_response.get('Certeza', [None])[0]

    if not all([prediccion, resultado, certeza]):
        await update.message.reply_text('La respuesta de la API no contiene toda la información esperada.')
        return


    # Actualizar la base de datos
    connection = connect_db()
    if connection:
        try:
            cursor = connection.cursor() 
            cursor.execute(
                "UPDATE usuarios SET peso = %s, altura = %s, entrecomidas = %s, historialfamiliar = %s, comidascaloricas = %s, prediagnostico = %s  WHERE cedula = %s",
                (peso, altura, entre_comidas, historial_familiar, comidas_caloricas, resultado, user_data[user_id]['cedula'])
            )
            connection.commit()
            cursor.close()
            connection.close()

            await update.message.reply_text('Datos actualizados correctamente en la base de datos.')

            await start_doctor_selection(update, context)
        except Exception as e:
            logger.error(f"Error al actualizar datos en la base de datos: {e}")
            await update.message.reply_text('Hubo un error al actualizar los datos en la base de datos, por favor intenta nuevamente.')
    else:
        await update.message.reply_text('No se pudo conectar a la base de datos, por favor intenta más tarde.')

    pending_audio[user_id] = False

# Function to start the bot and provide options for doctors
async def start_doctor_selection(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton(m[1], callback_data=f"medic_{m[0]}")] for m in medic_data]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Selecciona una opción:', reply_markup=reply_markup)

async def handle_doctor_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    medic_id = query.data.split('_')[1]
    await query.answer()
    await query.edit_message_text(text=f"Seleccionaste el médico con ID: {medic_id}")
    
    schedules = get_schedules_for_medic(medic_id)
    if not schedules:
        await query.edit_message_text('No se encontraron horarios disponibles para el médico seleccionado.')
        return

    keyboard = [[InlineKeyboardButton(f"{schedule[1]} - {schedule[2]}", callback_data=f"schedule_{schedule[0]}")] for schedule in schedules]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('Selecciona un horario:', reply_markup=reply_markup)

async def handle_schedule_selection(update: Update, context: CallbackContext) -> None:
    
    query = update.callback_query
    schedule_id = query.data.split('_')[1]
    user_id = query.from_user.id
    
    # Actualizar el estado del horario en la base de datos
    if update_schedule_status(schedule_id,user_id): 
        await query.answer()
        await query.edit_message_text(text=f"Seleccionaste el horario con ID: {schedule_id}. El horario se te ha asignado.")
        await update.effective_message.reply_text('¡Gracias por usar nuestro bot!, presentate con el médico en el horario seleccionado para recibir tu diagnóstico.')

    else:
        await query.answer()
        await query.edit_message_text('Hubo un error al actualizar el estado del horario. Inténtalo de nuevo.')

# Function to handle button selection
#async def button(update: Update, context: CallbackContext) -> None:
#    query = update.callback_query
#    await query.answer()
#    await query.edit_message_text(text=f"Seleccionaste la opción con ID: {query.data}")

async def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text('Ocurrió un error, por favor intenta nuevamente.')

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('select_doctor', start_doctor_selection))
    #application.add_handler(CallbackQueryHandler(button))
    #application.add_handler(CallbackQueryHandler(handle_doctor_selection))
    #application.add_handler(CallbackQueryHandler(handle_schedule_selection))
    application.add_handler(CallbackQueryHandler(handle_doctor_selection, pattern=r'^medic_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_schedule_selection, pattern=r'^schedule_\d+$'))
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
