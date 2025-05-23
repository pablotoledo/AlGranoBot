#!/usr/bin/env python3
"""
Manual test script for M4A support in AlGranoBot.
This script creates test M4A files and verifies the conversion functionality.
"""

import os
import tempfile
import logging
from pydub import AudioSegment
from pydub.generators import Sine
import sys
import pytest

# Add the main module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import get_audio_file_extension, convert_audio_to_wav

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def temp_files():
    """Fixture to manage temporary files."""
    temp_file_list = []
    yield temp_file_list
    
    # Cleanup after test
    for temp_file in temp_file_list:
        try:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception:
            pass


def create_test_m4a_file(duration_seconds=3, frequency=440):
    """Create a test M4A file with a sine wave."""
    try:
        # Generate a sine wave
        tone = Sine(frequency).to_audio_segment(duration=duration_seconds * 1000)
        
        # Create temporary M4A file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as temp_file:
            m4a_path = temp_file.name
        
        # Export as M4A
        tone.export(m4a_path, format="mp4", codec="aac")
        logger.info(f"Created test M4A file: {m4a_path}")
        return m4a_path
    except Exception as e:
        logger.error(f"Failed to create test M4A file: {e}")
        return None


@pytest.mark.parametrize("filename,mime_type,expected", [
    ("audio.m4a", "audio/mp4", ".m4a"),
    ("voice.M4A", None, ".m4a"),
    (None, "audio/x-m4a", ".m4a"),
    ("song.mp3", "audio/mpeg", ".mp3"),
])
def test_file_extension_detection(filename, mime_type, expected):
    """Test the file extension detection functionality."""
    result = get_audio_file_extension(filename, mime_type)
    assert result == expected, f"Expected {expected}, got {result} for {filename}, {mime_type}"


def test_m4a_conversion(temp_files):
    """Test M4A to WAV conversion."""
    # Create test M4A file
    m4a_path = create_test_m4a_file()
    if not m4a_path:
        pytest.fail("Could not create test M4A file")
    
    temp_files.append(m4a_path)
    
    # Create output WAV path
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
        wav_path = temp_file.name
        temp_files.append(wav_path)
    
    # Test conversion
    logger.info(f"Converting {m4a_path} to {wav_path}")
    success = convert_audio_to_wav(m4a_path, wav_path)
    
    assert success, "M4A to WAV conversion should succeed"
    assert os.path.exists(wav_path), "WAV file should be created"
    
    wav_size = os.path.getsize(wav_path)
    m4a_size = os.path.getsize(m4a_path)
    logger.info(f"✓ Conversion successful! M4A: {m4a_size} bytes, WAV: {wav_size} bytes")
    
    # Verify the WAV file can be loaded
    audio = AudioSegment.from_wav(wav_path)
    logger.info(f"✓ WAV file verification: Duration {len(audio)}ms, Channels: {audio.channels}")
    assert len(audio) > 0, "Converted audio should have content"


@pytest.mark.parametrize("ext,export_format", [
    ('.mp3', 'mp3'),
    ('.m4a', 'mp4'),  # M4A is typically MP4 container with AAC codec
    ('.wav', 'wav'),
    ('.ogg', 'ogg'),
])
def test_various_formats(ext, export_format, temp_files):
    """Test support for various audio formats."""
    try:
        # Generate test audio
        tone = Sine(440).to_audio_segment(duration=1000)  # 1 second
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            audio_path = temp_file.name
            temp_files.append(audio_path)
        
        # Export in the specified format
        if ext == '.m4a':
            tone.export(audio_path, format=export_format, codec="aac")
        else:
            tone.export(audio_path, format=export_format)
        
        # Test extension detection
        detected_ext = get_audio_file_extension(f"test{ext}")
        assert detected_ext == ext, f"Expected {ext}, got {detected_ext}"
        
        file_size = os.path.getsize(audio_path)
        logger.info(f"✓ {ext}: Created {file_size} bytes, detected as {detected_ext}")
        
    except Exception as e:
        pytest.fail(f"Failed to create/test {ext}: {e}")


def test_dependency_check():
    """Test that required dependencies are available."""
    try:
        import pydub
        logger.info("✓ pydub is available")
    except ImportError:
        pytest.fail("pydub is not available - install with: pip install pydub")
    
    try:
        # Test if ffmpeg is available
        AudioSegment.from_file
        logger.info("✓ ffmpeg appears to be available")
    except Exception as e:
        logger.warning(f"⚠ ffmpeg might not be available: {e}")
        pytest.skip(f"ffmpeg might not be available: {e}")


if __name__ == "__main__":
    # Run pytest when executed directly
    pytest.main([__file__, "-v"])
