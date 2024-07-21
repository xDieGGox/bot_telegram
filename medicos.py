from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import psycopg2
import os

# Function to connect to the database and retrieve data
def get_medic_data():
    conn = psycopg2.connect(
        dbname="obesidaddb",
        user="postgres",
        password="postgres",
        host="104.197.213.99",
        port="5432"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM medico")  # Adjust the query according to your table schema
    rows = cursor.fetchall()
    conn.close()
    return rows

# Function to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    medic_data = get_medic_data()
    keyboard = [[InlineKeyboardButton(m[1], callback_data=str(m[0]))] for m in medic_data]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Selecciona una opción:', reply_markup=reply_markup)

# Function to handle button selection
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"Seleccionaste la opción con ID: {query.data}")

def main():
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("7367523664:AAHBXabGHZV3DTG8Ko0ewLmv4Q8SZ5NR-mw").build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
