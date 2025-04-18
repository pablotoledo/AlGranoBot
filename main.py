import os
import tempfile
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from faster_whisper import WhisperModel

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Whisper Model - select an appropriate size:
# "tiny", "base", "small", "medium", "large"
MODEL_SIZE = "small"
# Set to True if you have a GPU available
USE_GPU = False

# Load the Whisper model
if USE_GPU:
    model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
else:
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

# Read allowed user IDs from environment variable (comma-separated)
ALLOWED_USERS = os.environ.get("ALLOWED_USERS")
if ALLOWED_USERS:
    ALLOWED_USERS = set(int(uid.strip()) for uid in ALLOWED_USERS.split(",") if uid.strip().isdigit())
else:
    ALLOWED_USERS = None

def is_authorized(update: Update) -> bool:
    """Check if the user or chat is authorized to interact with the bot."""
    user = update.effective_user
    chat = update.effective_chat

    # Print details about the received message
    logger.info(f"Received message from user: id={user.id if user else 'None'}, username={user.username if user else 'None'}, chat_id={chat.id if chat else 'None'}, chat_type={chat.type if chat else 'None'}")

    if ALLOWED_USERS is None:
        # No restriction if ALLOWED_USERS is not set
        logger.info("No ALLOWED_USERS set, allowing all users.")
        return True

    if user and user.id in ALLOWED_USERS:
        logger.info(f"User {user.id} is authorized.")
        return True

    if chat and chat.id in ALLOWED_USERS:
        logger.info(f"Chat {chat.id} is authorized.")
        return True

    logger.info(f"User {user.id if user else 'None'} or chat {chat.id if chat else 'None'} is NOT authorized.")
    return False

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the /start command is issued."""
    if not is_authorized(update):
        return
    await update.message.reply_text('Hello! Send me a voice message or audio file and I will transcribe it for you using local Whisper.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the /help command is issued."""
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "This bot transcribes voice messages and audio files using local Whisper.\n\n"
        "Simply send or forward a voice message or audio file, and I will reply with the transcription."
    )

async def transcribe_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Transcribes the voice message or audio file."""
    if not is_authorized(update):
        return
    # Inform the user that processing has started
    processing_message = await update.message.reply_text("Received your audio. Transcribing now...")
    
    # Get the voice or audio file
    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("Please send an audio file or voice message.")
        return
    
    file = await context.bot.get_file(voice.file_id)
    
    # Create a temporary file to save the audio
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_audio:
        await file.download_to_drive(temp_audio.name)
        temp_audio_path = temp_audio.name
    
    try:
        # Transcribe using local Whisper
        logger.info(f"Transcribing file: {temp_audio_path}")
        segments, info = model.transcribe(temp_audio_path, beam_size=5)
        
        # Join all segments into a single text
        transcription = ""
        for segment in segments:
            transcription += segment.text + " "
        
        # Send the transcription
        await update.message.reply_text(f"Transcription:\n\n{transcription.strip()}")
    
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        await update.message.reply_text(f"Error during transcription: {str(e)}")
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_audio_path)
        except Exception as e:
            logger.error(f"Error deleting temporary file: {str(e)}")
        
        # Delete the processing message
        await processing_message.delete()

def main() -> None:
    """Start the bot."""
    # Get the token from an environment variable
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Bot token not configured. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    # Create the application
    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add handler for voice messages and audio files
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, transcribe_audio))

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot started. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
