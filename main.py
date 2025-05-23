import os
import tempfile
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from faster_whisper import WhisperModel
from pydub import AudioSegment
import mimetypes

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

def get_audio_file_extension(file_name: str, mime_type: str = None) -> str:
    """Determine the appropriate file extension for the audio file."""
    # Try to get extension from filename first
    if file_name:
        _, ext = os.path.splitext(file_name.lower())
        if ext in ['.ogg', '.mp3', '.m4a', '.wav', '.flac', '.aac']:
            return ext
    
    # Try to determine from mime type
    if mime_type:
        mime_to_ext = {
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/mp4': '.m4a',
            'audio/x-m4a': '.m4a',
            'audio/wav': '.wav',
            'audio/flac': '.flac',
            'audio/aac': '.aac'
        }
        return mime_to_ext.get(mime_type, '.ogg')
    
    # Default to .ogg for voice messages
    return '.ogg'

def convert_audio_to_wav(input_path: str, output_path: str) -> bool:
    """Convert audio file to WAV format for better Whisper compatibility."""
    try:
        logger.info(f"Converting audio file {input_path} to WAV format")
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="wav")
        logger.info(f"Successfully converted audio to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error converting audio file: {str(e)}")
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
        "Supported formats: OGG, MP3, M4A, WAV, FLAC, AAC\n\n"
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
        await processing_message.delete()
        return
    
    file = await context.bot.get_file(voice.file_id)
    
    # Determine the appropriate file extension
    file_name = getattr(voice, 'file_name', None)
    mime_type = getattr(voice, 'mime_type', None)
    original_ext = get_audio_file_extension(file_name, mime_type)
    
    logger.info(f"Processing audio file: name={file_name}, mime_type={mime_type}, extension={original_ext}")
    
    # Create temporary files for original and converted audio
    temp_original_path = None
    temp_converted_path = None
    
    try:
        # Download the original file
        with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as temp_original:
            await file.download_to_drive(temp_original.name)
            temp_original_path = temp_original.name
        
        # Determine if we need to convert the file
        transcription_file_path = temp_original_path
        
        # For M4A and other formats that might need conversion, convert to WAV
        if original_ext in ['.m4a', '.aac']:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_converted:
                temp_converted_path = temp_converted.name
            
            if convert_audio_to_wav(temp_original_path, temp_converted_path):
                transcription_file_path = temp_converted_path
            else:
                # If conversion fails, try with original file
                logger.warning("Audio conversion failed, attempting transcription with original file")
                transcription_file_path = temp_original_path
        
        # Transcribe using local Whisper
        logger.info(f"Transcribing file: {transcription_file_path}")
        segments, info = model.transcribe(transcription_file_path, beam_size=5)
        
        # Join all segments into a single text
        transcription = ""
        for segment in segments:
            transcription += segment.text + " "
        
        transcription = transcription.strip()
        
        if not transcription:
            await update.message.reply_text("No speech detected in the audio file. Please try with a different audio file.")
        else:
            # Send the transcription
            await update.message.reply_text(f"Transcription:\n\n{transcription}")
        
        logger.info(f"Successfully transcribed audio file. Language: {info.language}, Duration: {info.duration:.2f}s")
    
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        error_message = "Sorry, I couldn't transcribe this audio file. "
        
        # Provide more specific error messages
        if "format" in str(e).lower() or "codec" in str(e).lower():
            error_message += "The audio format might not be supported or the file might be corrupted."
        elif "duration" in str(e).lower():
            error_message += "The audio file might be too short or empty."
        else:
            error_message += f"Error: {str(e)}"
        
        await update.message.reply_text(error_message)
    
    finally:
        # Clean up temporary files
        for temp_path in [temp_original_path, temp_converted_path]:
            if temp_path:
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.error(f"Error deleting temporary file {temp_path}: {str(e)}")
        
        # Delete the processing message
        try:
            await processing_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete processing message: {str(e)}")

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
