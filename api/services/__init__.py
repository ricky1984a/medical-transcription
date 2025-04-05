"""
Services package for business logic
"""
# Import common services to make them available through the package
try:
    from .speech_recognition import save_temp_file, transcribe_audio
except ImportError:
    pass

try:
    from .translation import translate_text, get_supported_languages
except ImportError:
    pass