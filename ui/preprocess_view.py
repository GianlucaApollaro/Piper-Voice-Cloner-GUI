import wx
import threading
import os
import subprocess
from core.docker_manager import DockerManager
from core.config_manager import ConfigManager
from core.translation_manager import tr

class PreprocessView(wx.Panel):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Grid for Options
        grid_sizer = wx.FlexGridSizer(rows=0, cols=2, vgap=10, hgap=10)
        grid_sizer.AddGrowableCol(1, 1)
        
        # Dataset Path
        grid_sizer.Add(wx.StaticText(self, label=tr("dataset_folder")), 0, wx.ALIGN_CENTER_VERTICAL)
        
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.entry_path = wx.TextCtrl(self)
        path_sizer.Add(self.entry_path, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.btn_browse = wx.Button(self, label=tr("browse"))
        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_browse_dataset)
        path_sizer.Add(self.btn_browse, 0)
        
        grid_sizer.Add(path_sizer, 1, wx.EXPAND)
        
        # Language
        grid_sizer.Add(wx.StaticText(self, label=tr("dataset_lang")), 0, wx.ALIGN_CENTER_VERTICAL)
        
        lang_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # UPDATED: Specific English codes to avoid accent ambiguity
        self.choice_language = wx.Choice(self, choices=["it", "en-us", "en", "es", "fr", "de"])
        
        # Smart Default Language
        import locale
        try:
            # Get system locale (e.g. 'en_US', 'it_IT')
            sys_lang, _ = locale.getdefaultlocale()
            sys_lang = sys_lang.lower().replace("_", "-") if sys_lang else "en-us"
            
            # Map common prefixes to our supported codes
            if "it" in sys_lang:
                default_lang = "it"
            elif "en-us" in sys_lang:
                default_lang = "en-us"
            elif "en-gb" in sys_lang:
                default_lang = "en-gb"
            elif "es" in sys_lang:
                default_lang = "es"
            elif "fr" in sys_lang:
                default_lang = "fr"
            elif "de" in sys_lang:
                default_lang = "de"
            else:
                default_lang = "en-us" # Global default
                
        except Exception:
            default_lang = "en-us"
            
        # Select if exists, else default to 0
        idx = self.choice_language.FindString(default_lang)
        if idx != wx.NOT_FOUND:
            self.choice_language.SetSelection(idx)
        else:
            self.choice_language.SetSelection(1) # Default to en-us if all else fails
            
        lang_sizer.Add(self.choice_language, 0, wx.RIGHT, 20)
        grid_sizer.Add(lang_sizer, 0, wx.ALIGN_LEFT)

        # Max Workers (Restored)
        grid_sizer.Add(wx.StaticText(self, label=tr("lbl_workers")), 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Default to CPU count or 1
        cpu_count = os.cpu_count() or 1
        self.spin_workers = wx.SpinCtrl(self, value=str(cpu_count), min=1, max=64)
        grid_sizer.Add(self.spin_workers, 0, wx.ALIGN_LEFT)
        
        main_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Explanation Text
        info = wx.StaticText(self, label=tr("process_note")) # Reuse or new key? Reusing "process_note" might be confusing ("Audiosplitting..."). 
        # Actually this step is JUST Piper Preprocessing. 
        # Let's add a static text explaining this specific step.
        lbl_info = wx.StaticText(self, label=tr("preprocess_info_note"))
        main_sizer.Add(lbl_info, 0, wx.ALL, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # We reuse the translation key "btn_preprocess_ds" ("Preprocess Dataset")
        self.btn_preprocess = wx.Button(self, label=tr("btn_preprocess_ds"))
        self.btn_preprocess.Bind(wx.EVT_BUTTON, self.on_preprocess)
        btn_sizer.Add(self.btn_preprocess, 0, wx.RIGHT, 10)
        
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Log
        self.textbox_log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        main_sizer.Add(self.textbox_log, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)

    def log(self, message):
        wx.CallAfter(self.textbox_log.AppendText, message + "\n")

    def set_path(self, path):
        self.entry_path.SetValue(path)

    def on_browse_dataset(self, event):
        dlg = wx.DirDialog(self, tr("dlg_select_ds_folder"), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.entry_path.SetValue(path)
        dlg.Destroy()

    def on_preprocess(self, event):
        dataset_path = self.entry_path.GetValue()
        if not os.path.exists(dataset_path):
            wx.MessageBox(tr("msg_ds_path_missing"), "Error", wx.OK | wx.ICON_ERROR)
            return
            
        lang_code = self.choice_language.GetStringSelection()
        max_workers = self.spin_workers.GetValue()
        
        self.btn_preprocess.Disable()
        self.log(tr("log_prep_started").format(lang_code))
        self.log(tr("log_workers_count").format(max_workers))
        
        threading.Thread(target=self._preprocess_thread, args=(dataset_path, lang_code, max_workers), daemon=True).start()

    def set_train_view(self, train_view):
        self.train_view = train_view

    def _preprocess_thread(self, dataset_path, lang_code, max_workers):
        try:
            dataset_path = self.entry_path.GetValue().strip()
            if os.path.isfile(dataset_path):
                dataset_path = os.path.dirname(dataset_path)
            dataset_path = dataset_path.rstrip("/\\")
            
            # Default single_speaker=True here as it's a voice cloner
            # FIX: Added dataset_format="ljspeech" (standard) and corrected keyword arg use_single_speaker
            cmd = ConfigManager.get_preprocess_command(lang_code, dataset_format="ljspeech", use_single_speaker=True, max_workers=max_workers)
            volumes = {dataset_path: "/dataset"}
            
            success, result = DockerManager.run_container(
                image=ConfigManager.DOCKER_IMAGE,
                command=cmd,
                volumes=volumes,
                gpus=True, 
                detach=True
            )
            
            if success:
                 container_id = result.strip()
                 self.log(tr("log_prep_container_started").format(container_id))
                 
                 # Stream logs
                 final_status = self._stream_logs(container_id)
                 
                 if final_status:
                     self.log(tr("log_prep_success_banner"))
                     
                     # Update Train View
                     if hasattr(self, 'train_view') and self.train_view:
                         wx.CallAfter(self.train_view.set_path, dataset_path)
                         
                     wx.CallAfter(wx.MessageBox, tr("msg_prep_complete"), "Info", wx.OK | wx.ICON_INFORMATION)
                 else:
                     self.log(tr("log_prep_failed_exit"))
                     wx.CallAfter(wx.MessageBox, tr("msg_prep_failed"), "Error", wx.OK | wx.ICON_ERROR)
            else:
                self.log(tr("log_start_container_error").format(result))
                wx.CallAfter(wx.MessageBox, tr("msg_start_docker_error").format(result), "Error", wx.OK | wx.ICON_ERROR)
                
        except Exception as e:
            self.log(tr("log_prep_exception").format(e))
            
        wx.CallAfter(self.btn_preprocess.Enable)

    def _stream_logs(self, container_id):
        # Stream until container stops
        # Reusing logic from TrainView somewhat simpler
        process = subprocess.Popen(
            ["docker", "logs", "-f", container_id], 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8', 
            errors='replace'
        )
        
        for line in process.stdout:
            self.log(line.strip())
            
        process.wait()
        
        # Check exit code
        try:
            inspect_cmd = ["docker", "inspect", container_id, "--format", "{{.State.ExitCode}}"]
            exit_code_str = subprocess.check_output(inspect_cmd, text=True).strip()
            return int(exit_code_str) == 0
        except:
            return False
