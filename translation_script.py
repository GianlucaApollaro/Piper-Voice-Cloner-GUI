
import sys
import subprocess

def install_deps():
    print("Installazione dipendenze...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "faster-whisper"], stdout=subprocess.DEVNULL)

try:
    from faster_whisper import WhisperModel
except ImportError:
    install_deps()
    from faster_whisper import WhisperModel

def translate_audio(audio_path, target_lang):
    print("Caricamento modello Whisper...")
    try:
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except:
        print("Fallback a modello medium...")
        model = WhisperModel("medium", device="cuda", compute_type="float16")
    
    print(f"Traduzione in {target_lang}...")
    
    # Whisper task="translate" translates to English by default
    # For other languages, we need to transcribe and then translate
    if target_lang == "en":
        # Direct translation to English
        segments, info = model.transcribe(audio_path, task="translate")
        detected_lang = info.language if hasattr(info, 'language') else 'unknown'
        print(f"Lingua rilevata: {detected_lang}")
    else:
        # Forziamo il task transcribe e il target_lang per ottenere una traduzione zero-shot
        segments, info = model.transcribe(audio_path, task="transcribe", language=target_lang)
        detected_lang = info.language if hasattr(info, 'language') else 'unknown'
        print(f"Lingua rilevata: {detected_lang} (Forzata a en)")
        print("NOTA: Whisper esegue una traduzione zero-shot forzando la lingua di output.")
    
    text = " ".join([s.text for s in segments]).strip()
    
    print("TRANSLATION_START")
    print(text)
    print("TRANSLATION_END")

if __name__ == "__main__":
    translate_audio("/audio", "en")
