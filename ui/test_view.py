import wx
import wx.adv
import threading
import os
import shutil
import wave
import contextlib
from core.docker_manager import DockerManager
from core.config_manager import ConfigManager
from core.ssml_processor import SSMLProcessor, SSMLRules
from core.pssml_handler import PSSMLHandler
from core.translation_manager import tr

class TestView(wx.Panel):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.generated_audio_path = None
        self.current_sound = None
        self.stop_timer = None
        
        # SSML-related state
        self.ssml_enabled = False
        self.ssml_rules = SSMLRules()  # Default rules
        self.original_text = ""  # Store original text when loading .pssml
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Grid for Inputs
        grid_sizer = wx.FlexGridSizer(rows=5, cols=2, vgap=10, hgap=10)
        grid_sizer.AddGrowableCol(1, 1)
        
        # Preset Voice Selection (NEW)
        grid_sizer.Add(wx.StaticText(self, label=tr("lbl_preset")), 0, wx.ALIGN_CENTER_VERTICAL)
        
        preset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.choice_preset = wx.Choice(self, choices=[tr("choice_select_voice")] + list(ConfigManager.PRESET_VOICES.keys()), name=tr("lbl_preset"))
        self.choice_preset.SetSelection(0)
        self.choice_preset.Bind(wx.EVT_CHOICE, self.on_preset_selected)
        preset_sizer.Add(self.choice_preset, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.btn_download_voice = wx.Button(self, label=tr("btn_download_voice"))
        self.btn_download_voice.Bind(wx.EVT_BUTTON, self.on_download_voice)
        self.btn_download_voice.Disable()
        preset_sizer.Add(self.btn_download_voice, 0)
        
        grid_sizer.Add(preset_sizer, 1, wx.EXPAND)
        
        # Separator text
        separator = wx.StaticText(self, label=tr("lbl_or"))
        separator.SetFont(separator.GetFont().Bold())
        grid_sizer.Add(wx.StaticText(self, label=""), 0)
        grid_sizer.Add(separator, 0, wx.ALIGN_CENTER)
        
        # ONNX Model Path
        grid_sizer.Add(wx.StaticText(self, label=tr("onnx_model_label")), 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Accessible File Picker substitute
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.text_onnx_path = wx.TextCtrl(self, name=tr("name_onnx_path"))
        path_sizer.Add(self.text_onnx_path, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.btn_browse_onnx = wx.Button(self, label=tr("browse"))
        self.btn_browse_onnx.Bind(wx.EVT_BUTTON, self.on_browse_onnx)
        path_sizer.Add(self.btn_browse_onnx, 0)
        
        grid_sizer.Add(path_sizer, 1, wx.EXPAND)
        
        # Helper text
        hint = wx.StaticText(self, label=tr("onnx_note"))
        hint.SetForegroundColour(wx.Colour(128, 128, 128))
        grid_sizer.Add(wx.StaticText(self, label=""), 0)
        grid_sizer.Add(hint, 0, wx.EXPAND)
        
        main_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Text Input Area with "Load File" button
        text_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        text_label_sizer.Add(wx.StaticText(self, label=tr("text_to_speak")), 1, wx.ALIGN_CENTER_VERTICAL)
        
        self.btn_load_text = wx.Button(self, label=tr("load_from_file"))
        self.btn_load_text.Bind(wx.EVT_BUTTON, self.on_load_text)
        text_label_sizer.Add(self.btn_load_text, 0)
        
        main_sizer.Add(text_label_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        self.text_input = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 100), name=tr("name_text_input"))
        self.text_input.SetValue(tr("default_text"))
        main_sizer.Add(self.text_input, 0, wx.EXPAND | wx.ALL, 10)
        
        # ===== SSML Settings Panel =====
        ssml_box = wx.StaticBox(self, label=tr("box_ssml"))
        ssml_box_sizer = wx.StaticBoxSizer(ssml_box, wx.VERTICAL)
        
        # Enable SSML checkbox
        self.chk_ssml_enabled = wx.CheckBox(self, label=tr("chk_ssml_enable"), name=tr("chk_ssml_enable"))
        self.chk_ssml_enabled.Bind(wx.EVT_CHECKBOX, self.on_ssml_enabled)
        ssml_box_sizer.Add(self.chk_ssml_enabled, 0, wx.ALL, 5)
        
        # Collapsible panel for settings (initially hidden)
        self.ssml_settings_panel = wx.Panel(self)
        ssml_settings_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # --- Punctuation Pauses ---
        pause_box = wx.StaticBox(self.ssml_settings_panel, label=tr("box_pauses"))
        pause_sizer = wx.StaticBoxSizer(pause_box, wx.VERTICAL)
        
        self.chk_pauses = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_pauses"))
        self.chk_pauses.SetValue(True)
        pause_sizer.Add(self.chk_pauses, 0, wx.ALL, 3)
        
        pause_grid = wx.FlexGridSizer(rows=4, cols=3, vgap=3, hgap=10)
        pause_grid.AddGrowableCol(1, 1)
        
        # Period
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label=tr("lbl_period")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spin_period = wx.SpinCtrl(self.ssml_settings_panel, value="800", min=0, max=5000, name=tr("lbl_period"))
        pause_grid.Add(self.spin_period, 0, wx.EXPAND)
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label="ms"), 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Comma
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label=tr("lbl_comma")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spin_comma = wx.SpinCtrl(self.ssml_settings_panel, value="300", min=0, max=5000, name=tr("lbl_comma"))
        pause_grid.Add(self.spin_comma, 0, wx.EXPAND)
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label="ms"), 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Exclamation
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label=tr("lbl_exclamation")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spin_exclamation = wx.SpinCtrl(self.ssml_settings_panel, value="1000", min=0, max=5000, name=tr("lbl_exclamation"))
        pause_grid.Add(self.spin_exclamation, 0, wx.EXPAND)
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label="ms"), 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Question
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label=tr("lbl_question")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spin_question = wx.SpinCtrl(self.ssml_settings_panel, value="1000", min=0, max=5000, name=tr("lbl_question"))
        pause_grid.Add(self.spin_question, 0, wx.EXPAND)
        pause_grid.Add(wx.StaticText(self.ssml_settings_panel, label="ms"), 0, wx.ALIGN_CENTER_VERTICAL)
        
        pause_sizer.Add(pause_grid, 0, wx.EXPAND | wx.ALL, 3)
        ssml_settings_sizer.Add(pause_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # --- Number Formatting ---
        number_box = wx.StaticBox(self.ssml_settings_panel, label=tr("box_formatting"))
        number_sizer = wx.StaticBoxSizer(number_box, wx.VERTICAL)
        
        self.chk_numbers = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_formatting"))
        self.chk_numbers.SetValue(True)
        number_sizer.Add(self.chk_numbers, 0, wx.ALL, 3)
        
        self.chk_cardinal = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_cardinal"))
        self.chk_cardinal.SetValue(True)
        number_sizer.Add(self.chk_cardinal, 0, wx.ALL, 3)
        
        self.chk_ordinal = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_ordinal"))
        self.chk_ordinal.SetValue(True)
        number_sizer.Add(self.chk_ordinal, 0, wx.ALL, 3)
        
        ssml_settings_sizer.Add(number_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # --- Spelling Rules ---
        spelling_box = wx.StaticBox(self.ssml_settings_panel, label=tr("box_spelling"))
        spelling_sizer = wx.StaticBoxSizer(spelling_box, wx.VERTICAL)
        
        self.chk_spelling = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_spelling"))
        self.chk_spelling.SetValue(True)
        spelling_sizer.Add(self.chk_spelling, 0, wx.ALL, 3)
        
        self.chk_brackets = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_brackets"))
        self.chk_brackets.SetValue(True)
        spelling_sizer.Add(self.chk_brackets, 0, wx.ALL, 3)
        
        self.chk_uppercase = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_uppercase"))
        self.chk_uppercase.SetValue(True)
        spelling_sizer.Add(self.chk_uppercase, 0, wx.ALL, 3)
        
        ssml_settings_sizer.Add(spelling_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # --- Paragraph Structure ---
        para_box = wx.StaticBox(self.ssml_settings_panel, label=tr("box_paragraphs"))
        para_sizer = wx.StaticBoxSizer(para_box, wx.VERTICAL)
        
        self.chk_paragraphs = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_paragraphs"))
        self.chk_paragraphs.SetValue(True)
        para_sizer.Add(self.chk_paragraphs, 0, wx.ALL, 3)
        
        self.chk_double_newline = wx.CheckBox(self.ssml_settings_panel, label=tr("chk_double_newline"))
        self.chk_double_newline.SetValue(True)
        para_sizer.Add(self.chk_double_newline, 0, wx.ALL, 3)
        
        ssml_settings_sizer.Add(para_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # --- Action Buttons ---
        ssml_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_preview_ssml = wx.Button(self.ssml_settings_panel, label=tr("btn_preview_ssml"))
        self.btn_preview_ssml.Bind(wx.EVT_BUTTON, self.on_preview_ssml)
        ssml_btn_sizer.Add(self.btn_preview_ssml, 0, wx.RIGHT, 5)
        
        self.btn_save_pssml = wx.Button(self.ssml_settings_panel, label=tr("btn_save_pssml"))
        self.btn_save_pssml.Bind(wx.EVT_BUTTON, self.on_save_pssml)
        ssml_btn_sizer.Add(self.btn_save_pssml, 0, wx.RIGHT, 5)
        
        self.btn_export_xml = wx.Button(self.ssml_settings_panel, label=tr("btn_export_xml"))
        self.btn_export_xml.Bind(wx.EVT_BUTTON, self.on_export_ssml_xml)
        ssml_btn_sizer.Add(self.btn_export_xml, 0)
        
        ssml_settings_sizer.Add(ssml_btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.ssml_settings_panel.SetSizer(ssml_settings_sizer)
        self.ssml_settings_panel.Hide()  # Initially hidden
        
        ssml_box_sizer.Add(self.ssml_settings_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(ssml_box_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        
        # Buttons Sizer
        self.btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_generate = wx.Button(self, label=tr("generate_audio"))
        self.btn_generate.Bind(wx.EVT_BUTTON, self.on_generate)
        self.btn_sizer.Add(self.btn_generate, 0, wx.RIGHT, 10)
        
        self.btn_play = wx.Button(self, label=tr("play_audio"))
        self.btn_play.Bind(wx.EVT_BUTTON, self.on_play)
        self.btn_play.Disable()
        self.btn_sizer.Add(self.btn_play, 0, wx.RIGHT, 10)
        
        self.btn_stop = wx.Button(self, label=tr("stop_audio"))
        self.btn_stop.Bind(wx.EVT_BUTTON, self.on_stop)
        self.btn_stop.Hide() # Hide initially
        self.btn_sizer.Add(self.btn_stop, 0, wx.RIGHT, 10)
        
        self.btn_save = wx.Button(self, label=tr("save_audio"))
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save_audio)
        self.btn_save.Disable()
        self.btn_sizer.Add(self.btn_save, 0)
        
        main_sizer.Add(self.btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Log
        self.textbox_log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP, name=tr("name_log"))
        main_sizer.Add(self.textbox_log, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)

    def log(self, message):
        wx.CallAfter(self.textbox_log.AppendText, message + "\n")

    def on_browse_onnx(self, event):
        with wx.FileDialog(self, tr("select_onnx"), wildcard="ONNX files (*.onnx)|*.onnx",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.text_onnx_path.SetValue(fileDialog.GetPath())

    def on_load_text(self, event):
        with wx.FileDialog(self, tr("load_text_title"), 
                           wildcard="All supported files (*.txt;*.pssml)|*.txt;*.pssml|Text files (*.txt)|*.txt|PSSML files (*.pssml)|*.pssml",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            filepath = fileDialog.GetPath()
            
            try:
                # Check if it's a .pssml file
                if filepath.endswith('.pssml'):
                    result = PSSMLHandler.load_pssml(filepath)
                    if result:
                        original_text, ssml_text, rules = result
                        self.text_input.SetValue(original_text)
                        self.original_text = original_text
                        
                        # Apply rules to UI
                        self._apply_rules_to_ui(rules)
                        self.ssml_rules = rules
                        
                        # Enable SSML
                        self.chk_ssml_enabled.SetValue(True)
                        self.ssml_enabled = True
                        self.ssml_settings_panel.Show()
                        self.Layout()
                        self.GetParent().Layout()
                        
                        self.log(f"PSSML Loaded: {filepath}")
                    else:
                        wx.MessageBox(f"Error loading PSSML.", tr("title_env_error"), wx.OK | wx.ICON_ERROR)
                else:
                    # Regular text file
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.text_input.SetValue(content)
                    self.log(f"{tr('text_loaded')} {filepath}")
                    
            except Exception as e:
                wx.MessageBox(tr("msg_load_error").format(e), tr("title_env_error"), wx.OK | wx.ICON_ERROR)

    def on_generate(self, event):
        onnx_path = self.text_onnx_path.GetValue()
        text = self.text_input.GetValue().strip()
        
        if not onnx_path or not os.path.exists(onnx_path):
            wx.MessageBox(tr("invalid_onnx"), tr("title_env_error"), wx.OK | wx.ICON_ERROR)
            return
            
        if not text:
            wx.MessageBox(tr("enter_text"), tr("title_env_error"), wx.OK | wx.ICON_ERROR)
            return
            
        self.btn_generate.Disable()
        self.btn_play.Disable()
        self.btn_save.Disable()
        self._reset_play_button() # Ensure clean state
        threading.Thread(target=self._generate_thread, args=(onnx_path, text), daemon=True).start()

    def set_train_view(self, train_view):
        self.train_view = train_view

    def _generate_thread(self, onnx_path, text):
        try:
            self.log(tr("gen_prep"))
            
            # Apply SSML if enabled
            if self.ssml_enabled:
                self.log("Usage SSML...")
                rules = self._get_current_rules()
                text = SSMLProcessor.apply_rules(text, rules)
                # CRITICAL FIX: Piper CLI reads input line-by-line. 
                # Multi-line SSML (<speak>...\n...</speak>) gets split into invalid XML fragments.
                # We must flatten it to a single line.
                text = text.replace('\n', ' ')
                self.log("SSML Applied.")
            
            # Paths
            model_dir = os.path.dirname(onnx_path)
            model_filename = os.path.basename(onnx_path)
            
            # Save Input Text to verify file-based piping works for large texts
            input_text_path = os.path.join(model_dir, "input.txt")
            # CRITICAL: Use newline='\n' to write Unix-style line endings.
            # Windows \r\n can confuse Linux tools/parsers reading from stdin.
            with open(input_text_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
            
            # Use docker volume mapping
            volumes = {model_dir: "/model_dir"}
            
            # FILE-BASED COMMAND (Robust for large inputs)
            # CHANGE: Use 'piper' binary (C++) instead of 'python3 -m piper'
            # The binary is installed in /usr/bin/piper and supports SSML reliably via stdin.
            # FIX: Explicitly point to the bundled espeak-ng-data (moved in Dockerfile)
            cmd_str = (
                f"cat /model_dir/input.txt | "
                f"/usr/bin/piper --model /model_dir/{model_filename} --output_file /model_dir/test_audio.wav "
                f"--espeak_data /usr/share/espeak-ng-data-piper"
            )
            
            full_setup = ConfigManager._get_setup_script()
            full_cmd = ["/bin/bash", "-c", full_setup + cmd_str]
            
            self.log(tr("gen_exec"))
            
            # GPU SAFETY LOGIC
            use_gpu = True
            if hasattr(self, 'train_view') and self.train_view and self.train_view.current_container_id:
                self.log(tr("log_gpu_busy_training")) # "GPU busy with training, switching to CPU..."
                use_gpu = False
            
            success, output = DockerManager.run_container(
                image=ConfigManager.DOCKER_IMAGE,
                command=full_cmd,
                volumes=volumes,
                gpus=use_gpu, 
                log_callback=self.log
            )
            
            if success:
                self.log(tr("gen_complete"))
                
                # Check if file exists on host
                output_wav_host = os.path.join(model_dir, "test_audio.wav")
                if os.path.exists(output_wav_host):
                    self.generated_audio_path = output_wav_host
                    self.log(f"{tr('temp_file_ready')} {output_wav_host}")
                    wx.CallAfter(self.btn_play.Enable)
                    wx.CallAfter(self.btn_save.Enable)
                else:
                    self.log(tr("err_audio_not_found"))
            else:
                self.log(f"Generazione Fallita: {output}")

        except Exception as e:
            self.log(f"Exception: {e}")
        finally:
            wx.CallAfter(self.btn_generate.Enable)

    def on_play(self, event):
        if self.generated_audio_path and os.path.exists(self.generated_audio_path):
            try:
                # 1. Start Sound
                self.current_sound = wx.adv.Sound(self.generated_audio_path)
                if self.current_sound.IsOk():
                    self.current_sound.Play(wx.adv.SOUND_ASYNC)
                    
                    # 2. Switch Button to Stop
                    self.btn_play.Hide()
                    self.btn_stop.Show()
                    self.btn_sizer.Layout() # Re-layout to handle hide/show
                    
                    # 3. Calculate Duration to Auto-Stop
                    duration_sec = 0
                    try:
                        with contextlib.closing(wave.open(self.generated_audio_path, 'r')) as f:
                            frames = f.getnframes()
                            rate = f.getframerate()
                            duration_sec = frames / float(rate)
                    except Exception as e:
                        print(f"Error calcuating duration: {e}")
                        duration_sec = 5 # Fallback
                        
                    # 4. Set Timer to revert to Play button after audio ends
                    # Use wx.CallLater which is a one-shot timer
                    # Add small buffer (+0.5s) to ensure audio is really done
                    delay_ms = int((duration_sec + 0.2) * 1000)
                    self.stop_timer = wx.CallLater(delay_ms, self._reset_play_button)
                    
                else:
                    wx.MessageBox(tr("playback_fail"), tr("title_env_error"))
            except Exception as e:
                wx.MessageBox(tr("msg_playback_error").format(e), tr("title_env_error"))
                
    def on_stop(self, event):
        """Force stop audio and reset buttons"""
        if self.current_sound:
            try:
                self.current_sound.Stop()
            except:
                pass
        self._reset_play_button()

    def _reset_play_button(self):
        """Helper to reset UI to Play state"""
        # Cancel timer if existing
        if self.stop_timer and self.stop_timer.IsRunning():
            self.stop_timer.Stop()
            
        self.btn_stop.Hide()
        self.btn_play.Show()
        self.btn_play.Enable() # Ensure it's enabled
        self.btn_sizer.Layout()

    def on_preset_selected(self, event):
        """Handle preset voice selection"""
        selection = self.choice_preset.GetSelection()
        if selection > 0:  # Not select voice option
            voice_name = self.choice_preset.GetStringSelection()
            voice_info = ConfigManager.PRESET_VOICES[voice_name]
            
            # Check if voice is already downloaded
            voices_dir = os.path.join(os.getcwd(), "voices")
            onnx_path = os.path.join(voices_dir, voice_info["file"])
            
            if os.path.exists(onnx_path):
                self.text_onnx_path.SetValue(onnx_path)
                self.btn_download_voice.Disable()
                self.log(f"Voice ready: {voice_name}")
            else:
                self.text_onnx_path.SetValue("")
                self.btn_download_voice.Enable()
                self.log(f"Voice selected: {voice_name} (needs download)")
        else:
            self.btn_download_voice.Disable()
    
    def on_download_voice(self, event):
        """Download selected preset voice"""
        selection = self.choice_preset.GetSelection()
        if selection <= 0:
            return
            
        voice_name = self.choice_preset.GetStringSelection()
        voice_info = ConfigManager.PRESET_VOICES[voice_name]
        
        self.btn_download_voice.Disable()
        self.btn_generate.Disable()
        
        threading.Thread(
            target=self._download_voice_thread,
            args=(voice_name, voice_info),
            daemon=True
        ).start()
    
    def _download_voice_thread(self, voice_name, voice_info):
        """Download voice files in background"""
        try:
            import requests
            
            # Create voices directory
            voices_dir = os.path.join(os.getcwd(), "voices")
            os.makedirs(voices_dir, exist_ok=True)
            
            # Download ONNX model
            onnx_path = os.path.join(voices_dir, voice_info["file"])
            config_path = os.path.join(voices_dir, voice_info["config_file"])
            
            self.log(tr("log_downloading_preset").format(voice_name))
            
            # Download ONNX
            response = requests.get(voice_info["url"], stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(onnx_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and downloaded % (1024 * 1024) < 8192:  # Log every MB
                        percent = (downloaded / total_size) * 100
                        self.log(f"  {percent:.1f}% ({downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB)")
            
            self.log(f"Downloading main config json...")
            
            # Download JSON config
            response = requests.get(voice_info["config_url"])
            response.raise_for_status()
            with open(config_path, 'wb') as f:
                f.write(response.content)
            
            self.log(f"✓ Download complete!")
            
            # Update UI
            wx.CallAfter(self.text_onnx_path.SetValue, onnx_path)
            wx.CallAfter(self.log, f"Voice Ready: {voice_name}")
            
        except Exception as e:
            self.log(f"Error download: {e}")
            wx.CallAfter(self.btn_download_voice.Enable)
        finally:
            wx.CallAfter(self.btn_generate.Enable)

    def on_save_audio(self, event):
        if not self.generated_audio_path or not os.path.exists(self.generated_audio_path):
             wx.MessageBox(tr("no_audio_to_save"), tr("title_env_error"))
             return

        with wx.FileDialog(self, tr("save_audio_dialog"), wildcard="WAV files (*.wav)|*.wav",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            target_path = fileDialog.GetPath()
            try:
                shutil.copy2(self.generated_audio_path, target_path)
                self.log(tr("log_audio_saved").format(target_path))
                wx.MessageBox(tr("saved_success") + f"\n{target_path}", tr("title_success"))
            except Exception as e:
                wx.MessageBox(tr("msg_save_error").format(e), tr("title_env_error"), wx.OK | wx.ICON_ERROR)
    
    # ===== SSML Methods =====
    
    def on_ssml_enabled(self, event):
        """Toggle SSML settings panel visibility"""
        self.ssml_enabled = self.chk_ssml_enabled.GetValue()
        
        if self.ssml_enabled:
            self.ssml_settings_panel.Show()
        else:
            self.ssml_settings_panel.Hide()
        
        # Re-layout to accommodate panel visibility change
        self.Layout()
        self.GetParent().Layout()
    
    def _get_current_rules(self) -> SSMLRules:
        """Collect current SSML rules from UI controls"""
        rules = SSMLRules()
        
        # Punctuation pauses
        rules.punctuation_pauses["enabled"] = self.chk_pauses.GetValue()
        rules.punctuation_pauses["period"] = self.spin_period.GetValue()
        rules.punctuation_pauses["comma"] = self.spin_comma.GetValue()
        rules.punctuation_pauses["exclamation"] = self.spin_exclamation.GetValue()
        rules.punctuation_pauses["question"] = self.spin_question.GetValue()
        
        # Number formatting
        rules.number_formatting["enabled"] = self.chk_numbers.GetValue()
        rules.number_formatting["cardinal"] = self.chk_cardinal.GetValue()
        rules.number_formatting["ordinal"] = self.chk_ordinal.GetValue()
        
        # Spelling
        rules.spelling["enabled"] = self.chk_spelling.GetValue()
        rules.spelling["brackets"] = self.chk_brackets.GetValue()
        rules.spelling["uppercase"] = self.chk_uppercase.GetValue()
        
        # Paragraph structure
        rules.paragraph_structure["enabled"] = self.chk_paragraphs.GetValue()
        rules.paragraph_structure["double_newline"] = self.chk_double_newline.GetValue()
        
        # Custom dictionary (preserved from loaded rules)
        rules.custom_dictionary = self.ssml_rules.custom_dictionary.copy()
        
        return rules
    
    def _apply_rules_to_ui(self, rules: SSMLRules):
        """Apply loaded rules to UI controls"""
        # Punctuation pauses
        self.chk_pauses.SetValue(rules.punctuation_pauses.get("enabled", True))
        self.spin_period.SetValue(rules.punctuation_pauses.get("period", 800))
        self.spin_comma.SetValue(rules.punctuation_pauses.get("comma", 300))
        self.spin_exclamation.SetValue(rules.punctuation_pauses.get("exclamation", 1000))
        self.spin_question.SetValue(rules.punctuation_pauses.get("question", 1000))
        
        # Number formatting
        self.chk_numbers.SetValue(rules.number_formatting.get("enabled", True))
        self.chk_cardinal.SetValue(rules.number_formatting.get("cardinal", True))
        self.chk_ordinal.SetValue(rules.number_formatting.get("ordinal", True))
        
        # Spelling
        self.chk_spelling.SetValue(rules.spelling.get("enabled", True))
        self.chk_brackets.SetValue(rules.spelling.get("brackets", True))
        self.chk_uppercase.SetValue(rules.spelling.get("uppercase", True))
        
        # Paragraph structure
        self.chk_paragraphs.SetValue(rules.paragraph_structure.get("enabled", True))
        self.chk_double_newline.SetValue(rules.paragraph_structure.get("double_newline", True))
        
        # Store custom dictionary
        self.ssml_rules.custom_dictionary = rules.custom_dictionary.copy()
    
    def on_preview_ssml(self, event):
        """Show SSML preview dialog"""
        text = self.text_input.GetValue().strip()
        
        if not text:
            wx.MessageBox(tr("enter_text"), tr("title_warning"), wx.OK | wx.ICON_WARNING)
            return
        
        # Get current rules and apply
        rules = self._get_current_rules()
        ssml_text = SSMLProcessor.apply_rules(text, rules)
        
        # Create preview dialog
        dialog = wx.Dialog(self, title=tr("title_preview_ssml"), size=(700, 500))
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Info text
        info = wx.StaticText(dialog, label=tr("msg_ssml_preview"))
        dialog_sizer.Add(info, 0, wx.ALL, 10)
        
        # SSML text display
        ssml_display = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP, name="Anteprima SSML")
        ssml_display.SetValue(ssml_text)
        dialog_sizer.Add(ssml_display, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_copy = wx.Button(dialog, label=tr("btn_copy_clipboard"))
        def on_copy(evt):
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(ssml_text))
                wx.TheClipboard.Close()
                wx.MessageBox(tr("msg_copied"), tr("title_success"), wx.OK | wx.ICON_INFORMATION)
        btn_copy.Bind(wx.EVT_BUTTON, on_copy)
        btn_sizer.Add(btn_copy, 0, wx.RIGHT, 5)
        
        btn_close = wx.Button(dialog, wx.ID_CLOSE, tr("menu_exit")) # Reuse 'Exit' or standard close
        btn_close.Bind(wx.EVT_BUTTON, lambda e: dialog.Close())
        btn_sizer.Add(btn_close, 0)
        
        dialog_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        dialog.SetSizer(dialog_sizer)
        dialog.ShowModal()
        dialog.Destroy()
    
    def on_save_pssml(self, event):
        """Save current text and rules as .pssml project"""
        text = self.text_input.GetValue().strip()
        
        if not text:
            wx.MessageBox(tr("enter_text"), tr("title_warning"), wx.OK | wx.ICON_WARNING)
            return
        
        with wx.FileDialog(self, tr("btn_save_pssml"), wildcard="PSSML files (*.pssml)|*.pssml",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            filepath = fileDialog.GetPath()
            
            # Get current rules and generate SSML
            rules = self._get_current_rules()
            ssml_text = SSMLProcessor.apply_rules(text, rules)
            
            # Save to file
            if PSSMLHandler.save_pssml(filepath, text, ssml_text, rules):
                self.log(f"PSSML Saved: {filepath}")
                wx.MessageBox(tr("msg_project_saved").format(filepath), tr("title_success"), wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox(tr("msg_save_error"), tr("title_env_error"), wx.OK | wx.ICON_ERROR)
    
    def on_export_ssml_xml(self, event):
        """Export pure SSML XML"""
        text = self.text_input.GetValue().strip()
        
        if not text:
            wx.MessageBox(tr("enter_text"), tr("title_warning"), wx.OK | wx.ICON_WARNING)
            return
        
        with wx.FileDialog(self, tr("btn_export_xml"), wildcard="XML files (*.xml)|*.xml|SSML files (*.ssml)|*.ssml",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            filepath = fileDialog.GetPath()
            
            # Get current rules and generate SSML
            rules = self._get_current_rules()
            ssml_text = SSMLProcessor.apply_rules(text, rules)
            
            # Export to file
            if PSSMLHandler.export_ssml_xml(filepath, ssml_text):
                self.log(f"XML Exported: {filepath}")
                wx.MessageBox(tr("msg_ssml_exported").format(filepath), tr("title_success"), wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox(tr("msg_save_error"), tr("title_env_error"), wx.OK | wx.ICON_ERROR)
