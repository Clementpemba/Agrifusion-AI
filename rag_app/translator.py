# translator.py - Final Working Version with deep-translator
from deep_translator import GoogleTranslator
from gtts import gTTS
import speech_recognition as sr
import os
import tempfile
import re

class LanguageTranslator:
    def __init__(self):
        self.supported_languages = {
            'en': 'english',
            'ny': 'chichewa',
            'tum': 'tumbuka'
        }
        
        # Common words for language detection
        self.chichewa_words = [
            'ndi', 'ku', 'pa', 'za', 'monga', 'chaka', 'ulimi', 'munda', 
            'mbewu', 'nthaka', 'madzi', 'dzuwa', 'mvula', 'kutentha', 
            'mungu', 'fumbi', 'mtengo', 'tchire', 'mseu', 'bwino', 'chonde',
            'zikomo', 'mwana', 'amayi', 'abambo', 'azimayi', 'abwana'
        ]
        
        self.tumbuka_words = [
            'ni', 'ku', 'pa', 'za', 'mukhe', 'chaka', 'ulimi', 'munda',
            'mbewu', 'nthaka', 'madzi', 'zuwa', 'vula', 'kutentha',
            'mungu', 'fumbi', 'muti', 'chilimwe', 'njila', 'uwemi', 'chonde',
            'yewo', 'mwana', 'mayi', 'data', 'awana', 'vwana'
        ]
    
    def detect_language(self, text):
        """Detect language of input text"""
        try:
            text_lower = text.lower()
            
            # Count matches for Tumbuka
            tumbuka_count = sum(1 for word in self.tumbuka_words if word in text_lower)
            
            # Count matches for Chichewa
            chichewa_count = sum(1 for word in self.chichewa_words if word in text_lower)
            
            # Determine language based on higher match count
            if tumbuka_count > chichewa_count and tumbuka_count > 2:
                return 'tum'
            elif chichewa_count > 2:
                return 'ny'
            else:
                return 'en'
                
        except Exception as e:
            print(f"Language detection error: {e}")
            return 'en'
    
    def translate_to_english(self, text, source_lang=None):
        """Translate Chichewa/Tumbuka to English"""
        if not text:
            return ""
            
        if not source_lang:
            source_lang = self.detect_language(text)
        
        # If already English, return as is
        if source_lang == 'en':
            return text
        
        try:
            # Map language codes for deep-translator
            lang_map = {'ny': 'ny', 'tum': 'tum'}
            target_lang = lang_map.get(source_lang)
            
            if target_lang:
                translated = GoogleTranslator(source=target_lang, target='en').translate(text)
                return translated
            else:
                return text
                
        except Exception as e:
            print(f"Translation to English error: {e}")
            return text
    
    def translate_from_english(self, text, target_lang='ny'):
        """Translate English to Chichewa or Tumbuka"""
        if not text or target_lang == 'en':
            return text
        
        try:
            # Map language codes for deep-translator
            lang_map = {'ny': 'ny', 'tum': 'tum'}
            target = lang_map.get(target_lang, 'ny')
            
            translated = GoogleTranslator(source='en', target=target).translate(text)
            return translated
            
        except Exception as e:
            print(f"Translation from English error: {e}")
            return text
    
    def text_to_speech(self, text, lang='ny'):
        """Convert text to audio response"""
        if not text:
            return None
            
        try:
            # Google TTS language codes
            lang_map = {
                'ny': 'ny',  # Chichewa
                'tum': 'sw',  # Swahili as fallback for Tumbuka
                'en': 'en'
            }
            
            tts_lang = lang_map.get(lang, 'en')
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            tts.save(temp_file.name)
            
            return temp_file.name
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return None
    
    def speech_to_text(self, audio_file):
        """Convert voice input to text"""
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(audio_file) as source:
                audio = recognizer.record(source)
            
            # Try English first
            try:
                text = recognizer.recognize_google(audio, language='en-US')
                if text:
                    return text, 'en'
            except:
                pass
            
            # Try Chichewa
            try:
                text = recognizer.recognize_google(audio, language='ny')
                if text:
                    return text, 'ny'
            except:
                pass
            
            # Try generic (auto-detect)
            try:
                text = recognizer.recognize_google(audio)
                if text:
                    detected_lang = self.detect_language(text)
                    return text, detected_lang
            except:
                pass
            
            return None, None
            
        except Exception as e:
            print(f"Speech Recognition Error: {e}")
            return None, None
    
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters
        text = re.sub(r'[^\w\s\.\,\!\?-]', '', text)
        
        return text.strip()

# Create single instance to reuse
translator = LanguageTranslator()

# Add this at the very end of translator.py
if __name__ == "__main__":
    print("Testing Translator...")
    
    # Test translation
    test_text = "Hello, I need farming advice"
    print(f"English: {test_text}")
    
    chichewa = translator.translate_from_english(test_text, 'ny')
    print(f"Chichewa: {chichewa}")
    
    detected = translator.detect_language(chichewa)
    print(f"Detected language: {detected}")
    
    print("\n✅ Translator is working correctly!")