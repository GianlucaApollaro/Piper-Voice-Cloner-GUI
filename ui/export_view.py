import wx
import threading
import os
from core.docker_manager import DockerManager
from core.config_manager import ConfigManager
from core.translation_manager import tr

class ExportView(wx.Panel):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Grid
        grid_sizer = wx.FlexGridSizer(rows=2, cols=2, vgap=10, hgap=10)
        grid_sizer.AddGrowableCol(1, 1)
        
        # Dataset
        lbl_dataset = wx.StaticText(self, label=tr("dataset_folder"))
        grid_sizer.Add(lbl_dataset, 0, wx.ALIGN_CENTER_VERTICAL)
        
        dataset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.entry_dataset = wx.TextCtrl(self, name="Cartella Dataset")
        self.btn_browse_dataset = wx.Button(self, label=tr("browse"))
        self.btn_browse_dataset.Bind(wx.EVT_BUTTON, self.on_browse_dataset)
        
        dataset_sizer.Add(self.entry_dataset, 1, wx.EXPAND | wx.RIGHT, 5)
        dataset_sizer.Add(self.btn_browse_dataset, 0)
        grid_sizer.Add(dataset_sizer, 1, wx.EXPAND)
        
        # Checkpoint
        lbl_ckpt = wx.StaticText(self, label=tr("ckpt_file_label"))
        grid_sizer.Add(lbl_ckpt, 0, wx.ALIGN_CENTER_VERTICAL)
        
        ckpt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.entry_ckpt = wx.TextCtrl(self, name="File Checkpoint")
        self.btn_browse_ckpt = wx.Button(self, label=tr("browse"))
        self.btn_browse_ckpt.Bind(wx.EVT_BUTTON, self.on_browse_ckpt)
        
        ckpt_sizer.Add(self.entry_ckpt, 1, wx.EXPAND | wx.RIGHT, 5)
        ckpt_sizer.Add(self.btn_browse_ckpt, 0)
        grid_sizer.Add(ckpt_sizer, 1, wx.EXPAND)
        
        main_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Helper text
        hint = wx.StaticText(self, label=tr("export_note"))
        hint.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(hint, 0, wx.LEFT | wx.BOTTOM, 10)

        # Button
        self.btn_export = wx.Button(self, label=tr("export_onnx_btn"))
        self.btn_export.Bind(wx.EVT_BUTTON, self.run_export)
        main_sizer.Add(self.btn_export, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        # Log
        self.textbox_log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        main_sizer.Add(self.textbox_log, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)

    def log(self, message):
        wx.CallAfter(self.textbox_log.AppendText, message + "\n")

    def on_browse_dataset(self, event):
        dlg = wx.DirDialog(self, tr("select_dataset_folder"), style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.entry_dataset.SetValue(dlg.GetPath())
        dlg.Destroy()

    def on_browse_ckpt(self, event):
        dlg = wx.FileDialog(self, tr("select_ckpt_file"), wildcard="Checkpoint (*.ckpt)|*.ckpt", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.entry_ckpt.SetValue(dlg.GetPath())
        dlg.Destroy()

    def run_export(self, event):
        dataset_path = self.entry_dataset.GetValue()
        local_ckpt_path = self.entry_ckpt.GetValue()
        
        if not dataset_path or not os.path.exists(dataset_path):
            wx.MessageBox(tr("invalid_path"), tr("title_error"), wx.OK | wx.ICON_ERROR)
            return

        if not local_ckpt_path or not os.path.exists(local_ckpt_path):
            wx.MessageBox(tr("invalid_path"), tr("title_error"), wx.OK | wx.ICON_ERROR)
            return

        if os.path.isdir(local_ckpt_path):
            wx.MessageBox(tr("ckpt_is_dir_error"), tr("title_error"), wx.OK | wx.ICON_ERROR)
            return
            
        # Verify config.json exists in dataset
        config_path = os.path.join(dataset_path, "config.json")
        if not os.path.exists(config_path):
            wx.MessageBox(
                tr("msg_config_missing"), 
                tr("title_error"), wx.OK | wx.ICON_ERROR
            )
            return
            
        # Verify checkpoint is inside dataset
        # Normalize paths
        abs_dataset = os.path.abspath(dataset_path)
        abs_ckpt = os.path.abspath(local_ckpt_path)
        
        if not abs_ckpt.startswith(abs_dataset):
            wx.MessageBox(
                tr("ckpt_outside_error"), 
                tr("title_path_error"), wx.OK | wx.ICON_ERROR
            )
            return
            
        # Calculate relative path for container
        # e.g. C:\Data\lightning_logs\...\last.ckpt -> lightning_logs/...\last.ckpt
        rel_path = os.path.relpath(abs_ckpt, abs_dataset)
        # Convert path separators to forward slashes for Linux container
        rel_path_linux = rel_path.replace(os.sep, '/')
        
        # Container path is /dataset/<rel_path>
        container_ckpt_path = f"/dataset/{rel_path_linux}"
        
        self.btn_export.Disable()
        threading.Thread(target=self._export_thread, args=(dataset_path, container_ckpt_path), daemon=True).start()

    def _export_thread(self, dataset_path, container_ckpt_path):
        try:
            cmd = ConfigManager.get_export_command(container_ckpt_path)
            volumes = {dataset_path: "/dataset"}
            
            self.log(tr("log_starting_export"))
            self.log(tr("log_container_ckpt_path").format(container_ckpt_path))
            
            success, output = DockerManager.run_container(
                image=ConfigManager.DOCKER_IMAGE,
                command=cmd,
                volumes=volumes,
                gpus=True,
                log_callback=self.log # Enable real-time logging
            )
            
            # log_callback handles the streaming output, so we don't need to print 'output' again 
            # unless we want debugging. run_container returns the FULL log in 'output' anyway.
            # Let's just log the final status.
            
            if success:
                # Post-process exported config JSON to add standard language metadata
                self._enrich_exported_config(dataset_path)
                self.log(tr("log_export_success_banner"))
                self.log(tr("log_check_exported_folder"))
                wx.MessageBox(tr("export_success"), tr("title_success"), wx.OK | wx.ICON_INFORMATION)
            else:
                self.log(tr("log_export_failed_banner"))
                wx.MessageBox(tr("export_error"), tr("title_error"), wx.OK | wx.ICON_ERROR)
                
        except Exception as e:
            self.log(f"Exception: {str(e)}")
        finally:
            wx.CallAfter(self.btn_export.Enable)

    def _enrich_exported_config(self, dataset_path, model_name="model"):
        import json
        config_file_path = os.path.join(dataset_path, "exported_model", f"{model_name}.onnx.json")
        if not os.path.exists(config_file_path):
            self.log(f"Warning: Exported config not found for enrichment: {config_file_path}")
            return
            
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 1. Enrich dataset name from folder name if blank
            if not data.get("dataset"):
                data["dataset"] = os.path.basename(os.path.normpath(dataset_path))
                
            # 2. Enrich quality
            audio_settings = data.setdefault("audio", {})
            if audio_settings.get("quality") == "dataset" or not audio_settings.get("quality"):
                audio_settings["quality"] = "medium"
                
            # 3. Enrich language metadata
            lang_settings = data.setdefault("language", {})
            raw_code = (lang_settings.get("code") or data.get("espeak", {}).get("voice") or "it").lower().strip()
            
            # Map of language codes to full Piper language metadata
            LANG_METADATA = {
                "it": {
                    "code": "it_IT",
                    "family": "it",
                    "region": "IT",
                    "name_native": "Italiano",
                    "name_english": "Italian",
                    "country_english": "Italy"
                },
                "it_it": {
                    "code": "it_IT",
                    "family": "it",
                    "region": "IT",
                    "name_native": "Italiano",
                    "name_english": "Italian",
                    "country_english": "Italy"
                },
                "en": {
                    "code": "en_GB",
                    "family": "en",
                    "region": "GB",
                    "name_native": "English",
                    "name_english": "English",
                    "country_english": "Great Britain"
                },
                "en_gb": {
                    "code": "en_GB",
                    "family": "en",
                    "region": "GB",
                    "name_native": "English",
                    "name_english": "English",
                    "country_english": "Great Britain"
                },
                "en-gb": {
                    "code": "en_GB",
                    "family": "en",
                    "region": "GB",
                    "name_native": "English",
                    "name_english": "English",
                    "country_english": "Great Britain"
                },
                "en_us": {
                    "code": "en_US",
                    "family": "en",
                    "region": "US",
                    "name_native": "English",
                    "name_english": "English",
                    "country_english": "United States"
                },
                "en-us": {
                    "code": "en_US",
                    "family": "en",
                    "region": "US",
                    "name_native": "English",
                    "name_english": "English",
                    "country_english": "United States"
                },
                "es": {
                    "code": "es_ES",
                    "family": "es",
                    "region": "ES",
                    "name_native": "Español",
                    "name_english": "Spanish",
                    "country_english": "Spain"
                },
                "es_es": {
                    "code": "es_ES",
                    "family": "es",
                    "region": "ES",
                    "name_native": "Español",
                    "name_english": "Spanish",
                    "country_english": "Spain"
                },
                "fr": {
                    "code": "fr_FR",
                    "family": "fr",
                    "region": "FR",
                    "name_native": "Français",
                    "name_english": "French",
                    "country_english": "France"
                },
                "fr_fr": {
                    "code": "fr_FR",
                    "family": "fr",
                    "region": "FR",
                    "name_native": "Français",
                    "name_english": "French",
                    "country_english": "France"
                },
                "de": {
                    "code": "de_DE",
                    "family": "de",
                    "region": "DE",
                    "name_native": "Deutsch",
                    "name_english": "German",
                    "country_english": "Germany"
                },
                "de_de": {
                    "code": "de_DE",
                    "family": "de",
                    "region": "DE",
                    "name_native": "Deutsch",
                    "name_english": "German",
                    "country_english": "Germany"
                }
            }
            
            meta = LANG_METADATA.get(raw_code, LANG_METADATA["it"])
            for k, v in meta.items():
                lang_settings[k] = v
                
            # Save it back
            with open(config_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.log(f"Successfully enriched exported config JSON with language metadata: {meta['code']}")
            
        except Exception as ex:
            self.log(f"Error enriching exported config JSON: {ex}")
