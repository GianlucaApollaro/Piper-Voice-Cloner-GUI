import wx
import threading
import os
import datetime
from core.docker_manager import DockerManager
from core.config_manager import ConfigManager
from core.translation_manager import tr

class TranslationView(wx.Panel):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.audio_path = None
        self.translated_text = ""
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label=tr("title_translation"))
        title_font = title.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Instructions
        instructions = wx.StaticText(
            self, 
            label=tr("instr_translation")
        )
        main_sizer.Add(instructions, 0, wx.ALL | wx.EXPAND, 10)
        
        # Grid for inputs
        grid_sizer = wx.FlexGridSizer(rows=2, cols=3, vgap=10, hgap=10)
        grid_sizer.AddGrowableCol(1, 1)
        
        # Row 1: Audio File
        lbl_audio = wx.StaticText(self, label=tr("lbl_audio_file"))
        grid_sizer.Add(lbl_audio, 0, wx.ALIGN_CENTER_VERTICAL)
        
        self.text_audio_path = wx.TextCtrl(self, name=tr("lbl_audio_file"))
        self.text_audio_path.SetHint(tr("hint_audio_file"))
        grid_sizer.Add(self.text_audio_path, 1, wx.EXPAND)
        
        self.btn_browse = wx.Button(self, label=tr("browse"), name=tr("browse"))
        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_browse_audio)
        grid_sizer.Add(self.btn_browse, 0)
        
        # Row 2: Target Language
        lbl_target = wx.StaticText(self, label=tr("lbl_target_lang"))
        grid_sizer.Add(lbl_target, 0, wx.ALIGN_CENTER_VERTICAL)
        
        self.choice_target_lang = wx.Choice(
            self,
            choices=[
                tr("lang_it"),
                tr("lang_en"),
                tr("lang_es"),
                tr("lang_fr"),
                tr("lang_de")
            ],
            name=tr("lbl_target_lang")
        )
        self.choice_target_lang.SetSelection(0)  # Default: Italiano
        grid_sizer.Add(self.choice_target_lang, 0, wx.EXPAND)
        
        grid_sizer.Add(wx.StaticText(self, label=""), 0)  # Empty cell
        
        main_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_translate = wx.Button(self, label=tr("btn_translate"), name=tr("btn_translate"))
        self.btn_translate.Bind(wx.EVT_BUTTON, self.on_translate)
        btn_sizer.Add(self.btn_translate, 0, wx.RIGHT, 10)
        
        self.btn_save = wx.Button(self, label=tr("btn_save_trans"), name=tr("btn_save_trans"))
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_save.Disable()
        btn_sizer.Add(self.btn_save, 0, wx.RIGHT, 10)
        
        self.btn_clear = wx.Button(self, label=tr("btn_clear"), name=tr("btn_clear"))
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        btn_sizer.Add(self.btn_clear, 0)
        
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Separator
        main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)
        
        # Result label
        result_label = wx.StaticText(self, label=tr("lbl_result"))
        main_sizer.Add(result_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        # Result text area
        self.text_result = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
            name=tr("lbl_result")
        )
        self.text_result.SetHint(tr("lbl_result") + "...")
        main_sizer.Add(self.text_result, 1, wx.EXPAND | wx.ALL, 10)
        
        # Log area
        log_label = wx.StaticText(self, label=tr("name_log"))
        main_sizer.Add(log_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        self.text_log = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
            name=tr("name_log"),
            size=(-1, 100)
        )
        main_sizer.Add(self.text_log, 0, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
    
    def log(self, message):
        """Add message to log"""
        wx.CallAfter(self.text_log.AppendText, message + "\n")
    
    def on_browse_audio(self, event):
        """Browse for audio file"""
        wildcard = "Audio files (*.mp3;*.wav;*.flac;*.m4a;*.ogg)|*.mp3;*.wav;*.flac;*.m4a;*.ogg|All files (*.*)|*.*"
        dlg = wx.FileDialog(
            self,
            tr("lbl_audio_file"),
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            self.audio_path = dlg.GetPath()
            self.text_audio_path.SetValue(self.audio_path)
            self.log(f"{tr('lbl_audio_file')} {os.path.basename(self.audio_path)}")
        
        dlg.Destroy()
    
    def on_translate(self, event):
        """Start translation"""
        if not self.audio_path or not os.path.exists(self.audio_path):
            wx.MessageBox(
                tr("missing_audio"),
                tr("title_path_error"),
                wx.OK | wx.ICON_WARNING
            )
            return
        
        # Get target language code
        selection = self.choice_target_lang.GetSelection()
        lang_map = {0: "it", 1: "en", 2: "es", 3: "fr", 4: "de"}
        target_lang = lang_map.get(selection, "it")
        
        self.btn_translate.Disable()
        self.btn_browse.Disable()
        self.choice_target_lang.Disable()
        self.text_result.Clear()
        
        self.log(tr("trans_start_log").format(self.choice_target_lang.GetStringSelection()))
        
        if self.status_callback:
            self.status_callback(tr("translating_progress"))
        
        threading.Thread(
            target=self._translate_thread,
            args=(self.audio_path, target_lang),
            daemon=True
        ).start()
    
    def _translate_thread(self, audio_path, target_lang):
        """Translation thread"""
        try:
            # We assume translation_script.py is present in root
            script_path = os.path.join(os.getcwd(), "translation_script.py")
             # If not present, we will rely on internal logic or error out?
            # Creating it on the fly is safer as per previous logic
            
            script_content = f'''
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
    
    print(f"Traduzione in {{target_lang}}...")
    
    # Whisper task="translate" translates to English by default
    # For other languages, we need to transcribe and then translate
    if target_lang == "en":
        # Direct translation to English
        segments, info = model.transcribe(audio_path, task="translate")
        detected_lang = info.language if hasattr(info, 'language') else 'unknown'
        print(f"Lingua rilevata: {{detected_lang}}")
    else:
        # Forziamo il task transcribe e il target_lang per ottenere una traduzione zero-shot
        segments, info = model.transcribe(audio_path, task="transcribe", language=target_lang)
        detected_lang = info.language if hasattr(info, 'language') else 'unknown'
        print(f"Lingua rilevata: {{detected_lang}} (Forzata a {target_lang})")
        print("NOTA: Whisper esegue una traduzione zero-shot forzando la lingua di output.")
    
    text = " ".join([s.text for s in segments]).strip()
    
    print("TRANSLATION_START")
    print(text)
    print("TRANSLATION_END")

if __name__ == "__main__":
    translate_audio("/audio", "{target_lang}")
'''
            
            # Write script to host
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            
            self.log(tr("status_download_start_docker"))
            
            cache_dir = os.path.join(os.getcwd(), "models_cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Run translation
            success, output = DockerManager.run_container(
                image=ConfigManager.DOCKER_IMAGE,
                command=[
                    "/bin/bash", "-c",
                    "LIBS=$(find /usr /opt -name libcudnn_ops.so.9* 2>/dev/null); "
                    "if [ -n \"$LIBS\" ]; then export LD_LIBRARY_PATH=$(dirname $(echo \"$LIBS\" | head -n 1)):$LD_LIBRARY_PATH; fi; "
                    "python -u /script.py"
                ],
                volumes={
                    audio_path: "/audio",
                    script_path: "/script.py",
                    cache_dir: "/root/.cache/huggingface"
                },
                gpus=True,
                log_callback=self.log
            )
            
            if success:
                # Extract translated text from output
                lines = output.split("\n")
                in_translation = False
                translation_lines = []
                
                for line in lines:
                    if "TRANSLATION_START" in line:
                        in_translation = True
                        continue
                    elif "TRANSLATION_END" in line:
                        break
                    elif in_translation:
                        translation_lines.append(line)
                
                self.translated_text = "\n".join(translation_lines).strip()
                
                if self.translated_text:
                    wx.CallAfter(self.text_result.SetValue, self.translated_text)
                    wx.CallAfter(self.btn_save.Enable)
                    self.log("✓ " + tr("trans_complete"))
                    
                    if self.status_callback:
                        wx.CallAfter(self.status_callback, tr("trans_complete"))
                else:
                    self.log("Errore: Nessun testo tradotto ricevuto")
                    wx.CallAfter(
                        wx.MessageBox,
                        "Impossibile estrarre il testo tradotto.",
                        tr("title_env_error"),
                        wx.OK | wx.ICON_ERROR
                    )
            else:
                self.log(f"{tr('trans_error')} {output}")
                wx.CallAfter(
                    wx.MessageBox,
                    tr("trans_error"),
                    tr("title_env_error"),
                    wx.OK | wx.ICON_ERROR
                )
        
        except Exception as e:
            self.log(f"Exception: {e}")
            wx.CallAfter(
                wx.MessageBox,
                f"Error: {e}",
                tr("title_env_error"),
                wx.OK | wx.ICON_ERROR
            )
        
        finally:
            wx.CallAfter(self.btn_translate.Enable)
            wx.CallAfter(self.btn_browse.Enable)
            wx.CallAfter(self.choice_target_lang.Enable)
    
    def on_save(self, event):
        """Save translation to file"""
        if not self.translated_text:
            return
        
        # Generate default filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_lang = self.choice_target_lang.GetStringSelection().split("(")[1].split(")")[0]
        default_name = f"traduzione_{target_lang}_{timestamp}.txt"
        
        dlg = wx.FileDialog(
            self,
            tr("btn_save_trans"),
            defaultFile=default_name,
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(self.translated_text)
                
                self.log(f"✓ " + tr("saved"))
                wx.MessageBox(
                    tr("trans_save_success").format(save_path),
                    tr("title_success"),
                    wx.OK | wx.ICON_INFORMATION
                )
            except Exception as e:
                self.log(f"{tr('save_error')} {e}")
                wx.MessageBox(
                    f"{tr('save_error')}\n{e}",
                    tr("title_env_error"),
                    wx.OK | wx.ICON_ERROR
                )
        
        dlg.Destroy()
    
    def on_clear(self, event):
        """Clear all fields"""
        self.audio_path = None
        self.translated_text = ""
        self.text_audio_path.Clear()
        self.text_result.Clear()
        self.text_log.Clear()
        self.btn_save.Disable()
        self.choice_target_lang.SetSelection(0)
        self.log("Ready.")
