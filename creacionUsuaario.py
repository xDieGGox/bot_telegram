import os
import logging
import psycopg2
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

# Configurar el registro de errores
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Datos de la base de datos PostgreSQL
DB_HOST = '35.212.144.181'
DB_NAME = 'obesidadbd'
DB_USER = 'postgres'
DB_PASS = 'postgres'

# Token del bot de Telegram
TELEGRAM_TOKEN = '7367523664:AAHBXabGHZV3DTG8Ko0ewLmv4Q8SZ5NR-mw'

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

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Por favor envía tus datos en el siguiente formato:\n'
        'Cédula, Nombres, Apellidos, Teléfono, Correo, Edad\n'
        '(por ejemplo: 12345678, Juan, Pérez, 1234567890, juan@example.com, 25).'
    )

async def handle_text(update: Update, context: CallbackContext) -> None:
    text = update.message.text
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
            await update.message.reply_text('Datos guardados exitosamente.')
        except Exception as e:
            logger.error(f"Error al insertar datos en la base de datos: {e}")
            await update.message.reply_text('Hubo un error al guardar los datos, por favor intenta nuevamente.')
    else:
        await update.message.reply_text('No se pudo conectar a la base de datos, por favor intenta más tarde.')

async def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text('Ocurrió un error, por favor intenta nuevamente.')

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)

    # Confirmar la conexión a la base de datos al iniciar el bot
    if connect_db():
        logger.info('Conexión a la base de datos exitosa.')
    else:
        logger.error('No se pudo conectar a la base de datos.')

    application.run_polling()

if __name__ == '__main__':
    main()