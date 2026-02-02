"""
Vonage Voice Recorder System

Vonage APIを使用した音声録音システム
"""

__version__ = "0.1.0"

from src.config import Config, ConfigurationError

__all__ = ["Config", "ConfigurationError"]
