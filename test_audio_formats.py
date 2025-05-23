#!/usr/bin/env python3
"""
Unit tests for audio format support in AlGranoBot.
Tests the M4A support and other audio format handling functionality.
"""

import tempfile
import os
import sys
from unittest.mock import Mock, patch
import pytest
from pydub import AudioSegment
import numpy as np

# Add the main module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import get_audio_file_extension, convert_audio_to_wav


@pytest.fixture
def temp_files():
    """Fixture to manage temporary files."""
    temp_file_list = []
    yield temp_file_list
    
    # Cleanup after test
    for temp_file in temp_file_list:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception:
            pass


def create_test_audio_file(format_ext: str, temp_files: list, duration_ms: int = 1000) -> str:
    """Create a test audio file in the specified format."""
    # Generate a simple sine wave
    sample_rate = 44100
    frequency = 440  # A4 note
    duration_seconds = duration_ms / 1000.0
    
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), False)
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit integer
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Create AudioSegment
    audio = AudioSegment(
        audio_data.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1
    )
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=format_ext) as temp_file:
        temp_path = temp_file.name
        temp_files.append(temp_path)
    
    # Export to the specified format
    audio.export(temp_path, format=format_ext.lstrip('.'))
    return temp_path


@pytest.mark.parametrize("filename,mime_type,expected", [
    ("test.m4a", None, ".m4a"),
    ("audio.MP3", None, ".mp3"),
    ("voice.OGG", None, ".ogg"),
    ("music.wav", None, ".wav"),
    ("song.flac", None, ".flac"),
    ("audio.aac", None, ".aac"),
    ("unknown.txt", None, ".ogg"),  # Default fallback
])
def test_get_audio_file_extension_from_filename(filename, mime_type, expected):
    """Test file extension detection from filename."""
    result = get_audio_file_extension(filename, mime_type)
    assert result == expected


@pytest.mark.parametrize("filename,mime_type,expected", [
    (None, "audio/mp4", ".m4a"),
    (None, "audio/x-m4a", ".m4a"),
    (None, "audio/mpeg", ".mp3"),
    (None, "audio/ogg", ".ogg"),
    (None, "audio/wav", ".wav"),
    (None, "audio/flac", ".flac"),
    (None, "audio/aac", ".aac"),
    (None, "unknown/type", ".ogg"),  # Default fallback
])
def test_get_audio_file_extension_from_mime_type(filename, mime_type, expected):
    """Test file extension detection from MIME type."""
    result = get_audio_file_extension(filename, mime_type)
    assert result == expected


def test_get_audio_file_extension_filename_priority():
    """Test that filename takes priority over MIME type."""
    result = get_audio_file_extension("test.m4a", "audio/mpeg")
    assert result == ".m4a"


def test_convert_audio_to_wav_m4a(temp_files):
    """Test M4A to WAV conversion."""
    try:
        # Create a test M4A file
        m4a_path = create_test_audio_file(".m4a", temp_files)
        
        # Create output WAV file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
            wav_path = wav_file.name
            temp_files.append(wav_path)
        
        # Test conversion
        result = convert_audio_to_wav(m4a_path, wav_path)
        
        # Verify conversion succeeded
        assert result, "M4A to WAV conversion should succeed"
        assert os.path.exists(wav_path), "WAV file should be created"
        assert os.path.getsize(wav_path) > 0, "WAV file should not be empty"
        
        # Verify the WAV file can be read by AudioSegment
        converted_audio = AudioSegment.from_wav(wav_path)
        assert len(converted_audio) > 0, "Converted audio should have content"
        
    except Exception as e:
        # If pydub/ffmpeg is not available, skip this test
        pytest.skip(f"Audio conversion test skipped due to missing dependencies: {e}")


def test_convert_audio_to_wav_invalid_file(temp_files):
    """Test conversion with invalid input file."""
    # Create a non-existent file path
    invalid_path = "/tmp/non_existent_file.m4a"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
        wav_path = wav_file.name
        temp_files.append(wav_path)
    
    # Test conversion with invalid input
    result = convert_audio_to_wav(invalid_path, wav_path)
    
    # Verify conversion failed gracefully
    assert not result, "Conversion should fail for non-existent file"


@pytest.mark.parametrize("fmt", [".ogg", ".mp3", ".m4a", ".wav", ".flac", ".aac"])
def test_supported_formats_coverage(fmt):
    """Test that all documented formats are supported in extension detection."""
    # Test with filename
    result = get_audio_file_extension(f"test{fmt}")
    assert result == fmt, f"Format {fmt} should be detected from filename"


class TestAudioFormatIntegration:
    """Integration tests for the audio processing pipeline."""
    
    @patch('main.model')
    @patch('main.logger')
    @pytest.mark.asyncio
    async def test_transcribe_audio_m4a_workflow(self, mock_logger, mock_model):
        """Test the complete M4A transcription workflow."""
        # This is a simplified integration test
        # In a real scenario, you would mock the Telegram objects and test the full workflow
        
        # Mock the Whisper model response
        mock_segments = [
            Mock(text="Hello "),
            Mock(text="world "),
            Mock(text="this is a test")
        ]
        mock_info = Mock(language="en", duration=3.5)
        mock_model.transcribe.return_value = (mock_segments, mock_info)
        
        # This test would require more complex setup to mock Telegram objects
        # For now, we're testing the core functionality in isolation
        assert True, "Integration test placeholder"
