#!/usr/bin/env python3
"""
Simple demonstration of M4A transcription capability.
This script creates a test M4A file and shows how it would be processed by the bot.
"""

import os
import tempfile
import logging
from pydub import AudioSegment
from pydub.generators import Sine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our functions
from main import get_audio_file_extension, convert_audio_to_wav

def create_demo_m4a_file():
    """Create a demo M4A file with a simple tone."""
    try:
        # Create a 3-second sine wave at 440Hz (A4 note)
        tone = Sine(440).to_audio_segment(duration=3000)
        
        # Create temporary M4A file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as temp_file:
            m4a_path = temp_file.name
        
        # Export as M4A (AAC in MP4 container)
        tone.export(m4a_path, format="mp4", codec="aac")
        logger.info(f"✓ Created demo M4A file: {m4a_path}")
        return m4a_path
    except Exception as e:
        logger.error(f"✗ Failed to create demo M4A file: {e}")
        return None

def demo_m4a_processing():
    """Demonstrate the M4A processing workflow."""
    logger.info("🎵 AlGranoBot M4A Support Demonstration")
    logger.info("=" * 50)
    
    # Step 1: Create a demo M4A file
    logger.info("Step 1: Creating demo M4A file...")
    m4a_path = create_demo_m4a_file()
    if not m4a_path:
        return False
    
    try:
        # Step 2: Demonstrate file extension detection
        logger.info("Step 2: Testing file extension detection...")
        detected_ext = get_audio_file_extension("demo_audio.m4a", "audio/mp4")
        logger.info(f"✓ Detected extension: {detected_ext}")
        
        # Step 3: Demonstrate audio conversion
        logger.info("Step 3: Converting M4A to WAV...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
            wav_path = temp_wav.name
        
        success = convert_audio_to_wav(m4a_path, wav_path)
        
        if success:
            m4a_size = os.path.getsize(m4a_path)
            wav_size = os.path.getsize(wav_path)
            logger.info(f"✓ Conversion successful!")
            logger.info(f"  Original M4A: {m4a_size:,} bytes")
            logger.info(f"  Converted WAV: {wav_size:,} bytes")
            
            # Verify the converted file
            converted_audio = AudioSegment.from_wav(wav_path)
            logger.info(f"  Duration: {len(converted_audio)}ms")
            logger.info(f"  Channels: {converted_audio.channels}")
            logger.info(f"  Sample Rate: {converted_audio.frame_rate}Hz")
        else:
            logger.error("✗ Conversion failed")
            return False
        
        # Step 4: Show what happens in the bot
        logger.info("Step 4: Bot processing simulation...")
        logger.info("In the actual bot, this WAV file would now be sent to Whisper for transcription")
        logger.info("The transcribed text would then be sent back to the user via Telegram")
        
        logger.info("=" * 50)
        logger.info("🎉 M4A support demonstration completed successfully!")
        logger.info("The bot can now handle M4A files sent by users!")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Demo failed: {e}")
        return False
    
    finally:
        # Cleanup
        for path in [m4a_path, wav_path]:
            try:
                if path and os.path.exists(path):
                    os.unlink(path)
            except:
                pass

if __name__ == "__main__":
    success = demo_m4a_processing()
    exit(0 if success else 1)
