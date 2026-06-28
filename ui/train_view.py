import wx
import threading
import subprocess
import os
import re
import datetime
from core.docker_manager import DockerManager
from core.config_manager import ConfigManager
from core.translation_manager import tr

class TrainView(wx.Panel):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.current_container_id = None
        self.stop_event = threading.Event()
        self.last_valid_checkpoint = 0 # Track last valid selection
        
        # Early Stopping State
        self.best_loss = float('inf')
        self.patience_counter = 0
        self.PATIENCE_LIMIT = 50 # Tracks epochs, not steps
        
        # Auto-Export State
        self.autoexport_best_in_window = None # Tuple: (loss, filepath, epoch)
        self.autoexport_window_start_epoch = 0
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Grid
        grid_sizer = wx.FlexGridSizer(rows=0, cols=2, vgap=10, hgap=10)
        grid_sizer.AddGrowableCol(1, 1)
        
        # Auto-detect GPU settings
        gpu_config = ConfigManager.detect_gpu_settings()
        recommended_bs = str(gpu_config["batch_size"])
        gpu_name = gpu_config["gpu_name"]
        
        # Batch Size
        grid_sizer.Add(wx.StaticText(self, label=tr("batch_size")), 0, wx.ALIGN_CENTER_VERTICAL)
        bs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.entry_batch = wx.TextCtrl(self, value=recommended_bs, size=(50, -1))
        bs_sizer.Add(self.entry_batch, 0, wx.RIGHT, 10)
        
        # Show detected GPU info in tooltip or small label if possible, or just log it
        if gpu_name != "Unknown/CPU":
            # Add a small note about the detected GPU
            lbl_gpu = wx.StaticText(self, label=f"({gpu_name})")
            lbl_gpu.SetForegroundColour(wx.Colour(100, 100, 100)) # Grey text
            bs_sizer.Add(lbl_gpu, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Accumulate Grad Batches
        bs_sizer.Add(wx.StaticText(self, label=tr("lbl_accumulate")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_accumulate = wx.SpinCtrl(self, value="1", min=1, max=64, size=(50, -1))
        bs_sizer.Add(self.entry_accumulate, 0, wx.RIGHT, 10)
        
        bs_sizer.Add(wx.StaticText(self, label=tr("val_split")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_val_split = wx.TextCtrl(self, value="0.0")
        bs_sizer.Add(self.entry_val_split, 0, wx.RIGHT, 10)

        bs_sizer.Add(wx.StaticText(self, label=tr("stop_patience")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_patience = wx.TextCtrl(self, value="50")
        bs_sizer.Add(self.entry_patience, 0, wx.RIGHT, 10)

        # Overtraining Protection
        self.chk_overtraining = wx.CheckBox(self, label=tr("chk_overtraining"))
        self.chk_overtraining.SetValue(False) # Default Off
        bs_sizer.Add(self.chk_overtraining, 0, wx.RIGHT, 10)
        
        # Auto-Export and Speak Settings
        autoexport_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Row 1: Checkbox + Keep N latest
        autoexport_row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_autoexport = wx.CheckBox(self, label=tr("chk_autoexport"))
        self.chk_autoexport.SetValue(False)
        autoexport_row1.Add(self.chk_autoexport, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        autoexport_row1.Add(wx.StaticText(self, label=tr("lbl_keep_recent")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_keep_n = wx.SpinCtrl(self, value="5", min=1, max=100, size=(50, -1))
        autoexport_row1.Add(self.entry_keep_n, 0, wx.RIGHT, 10)
        autoexport_sizer.Add(autoexport_row1, 0, wx.BOTTOM, 5)
        
        # Row 2: Keep best every X window
        autoexport_row2 = wx.BoxSizer(wx.HORIZONTAL)
        autoexport_row2.Add(wx.StaticText(self, label=tr("lbl_keep_best_x")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_keep_best_x = wx.SpinCtrl(self, value="5", min=1, max=1000, size=(60, -1))
        autoexport_row2.Add(self.entry_keep_best_x, 0)
        
        autoexport_sizer.Add(autoexport_row2, 0)
        
        bs_sizer.Add(autoexport_sizer, 0, wx.RIGHT, 10)
        
        bs_sizer.Add(wx.StaticText(self, label=tr("max_epochs")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_epochs = wx.SpinCtrl(self, value="6000")
        self.entry_epochs.SetRange(1, 100000)
        bs_sizer.Add(self.entry_epochs, 0, wx.RIGHT, 10)

        bs_sizer.Add(wx.StaticText(self, label=tr("save_every")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_ckpt_freq = wx.TextCtrl(self, value="1", size=(50, -1))
        bs_sizer.Add(self.entry_ckpt_freq, 0, wx.RIGHT, 10)
        
        # Learning Rate
        bs_sizer.Add(wx.StaticText(self, label=tr("lbl_learning_rate")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_lr = wx.TextCtrl(self, value="0.0001", size=(70, -1))
        bs_sizer.Add(self.entry_lr, 0, wx.RIGHT, 10)
        
        # Loader Workers
        bs_sizer.Add(wx.StaticText(self, label=tr("lbl_workers")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_workers = wx.SpinCtrl(self, value="8", min=0, max=32, size=(50, -1))
        bs_sizer.Add(self.entry_workers, 0)
        
        grid_sizer.Add(bs_sizer, 0, wx.ALIGN_LEFT)
        
        # Dataset Path
        grid_sizer.Add(wx.StaticText(self, label=tr("dataset_folder")), 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Sizer for Path + Browse Button
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.entry_path = wx.TextCtrl(self)
        path_sizer.Add(self.entry_path, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.btn_browse = wx.Button(self, label=tr("browse"))
        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_browse_dataset)
        path_sizer.Add(self.btn_browse, 0)
        
        grid_sizer.Add(path_sizer, 1, wx.EXPAND)

        
        lang_prec_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Smart Default Language - REMOVED (Redundant)
            
        lang_prec_sizer.Add(wx.StaticText(self, label=tr("precision")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.choice_precision = wx.Choice(self, choices=["16", "32"])
        self.choice_precision.SetSelection(0) # Default to 16 for RTX 5070 (Better VRAM usage, same quality)
        lang_prec_sizer.Add(self.choice_precision, 0)
        
        grid_sizer.Add(lang_prec_sizer, 0, wx.ALIGN_LEFT)
        
        # Base Model Checkpoint (Refactored for Accessibility)
        grid_sizer.Add(wx.StaticText(self, label=tr("base_model")), 0, wx.ALIGN_CENTER_VERTICAL)
        
        ckpt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.choice_checkpoint = wx.Choice(self, choices=[])
        ckpt_sizer.Add(self.choice_checkpoint, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.btn_load_ckpt = wx.Button(self, label=tr("load"))
        self.btn_load_ckpt.Bind(wx.EVT_BUTTON, self.on_load_checkpoint_btn)
        ckpt_sizer.Add(self.btn_load_ckpt, 0)
        
        grid_sizer.Add(ckpt_sizer, 0, wx.EXPAND)
        
        # Populate Checkpoints safely
        try:
            self.load_checkpoints()
        except Exception as e:
            wx.MessageBox(tr("msg_load_ckpt_error").format(e), tr("title_error"))
        
        main_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_gen_report = wx.Button(self, label=tr("btn_gen_report"))
        self.btn_gen_report.Bind(wx.EVT_BUTTON, lambda e: self.generate_analysis_report())
        btn_sizer.Add(self.btn_gen_report, 0, wx.RIGHT, 10)

        self.btn_start = wx.Button(self, label=tr("start_training")) # Green
        self.btn_start.SetBackgroundColour(wx.Colour(0, 128, 0))
        self.btn_start.SetForegroundColour(wx.Colour(255, 255, 255))
        self.btn_start.Bind(wx.EVT_BUTTON, self.start_training)
        btn_sizer.Add(self.btn_start, 0, wx.RIGHT, 10)
        
        self.btn_stop = wx.Button(self, label=tr("stop_training")) # Red
        self.btn_stop.SetBackgroundColour(wx.Colour(128, 0, 0))
        self.btn_stop.SetForegroundColour(wx.Colour(255, 255, 255))
        self.btn_stop.Bind(wx.EVT_BUTTON, self.stop_training)
        self.btn_stop.Disable()
        btn_sizer.Add(self.btn_stop, 0)
        
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Log
        self.textbox_log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        main_sizer.Add(self.textbox_log, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)

        # Accessibility: Shortcut for Stop Training (Ctrl+K)
        stop_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.stop_training, id=stop_id)
        
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('K'), stop_id)
        ])
        self.SetAcceleratorTable(accel_tbl)

    def load_checkpoints(self):
        self.checkpoints_map = {}
        choices = [tr("checkpoint_none")]
        
        # 1. Add Presets (No separators)
        for label in ConfigManager.PRESET_CHECKPOINTS.keys():
            choices.append(label)
            self.checkpoints_map[label] = "PRESET:" + label
            
        # 2. Add Custom from Folder
        ckpt_dir = os.path.join(os.getcwd(), "checkpoints")
        if not os.path.exists(ckpt_dir):
            os.makedirs(ckpt_dir)
            
        for f in os.listdir(ckpt_dir):
            if f.endswith(".ckpt"):
                choices.append(f)
                self.checkpoints_map[f] = os.path.join(ckpt_dir, f)
                
        self.choice_checkpoint.SetItems(choices)
        self.choice_checkpoint.SetSelection(0) 
        
    def on_load_checkpoint_btn(self, event):
        dlg = wx.FileDialog(self, tr("dlg_choose_ckpt"), wildcard="Checkpoint files (*.ckpt)|*.ckpt", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            name = os.path.basename(path)
            
            # Copy or Reference? Just reference for now
            self.checkpoints_map[name] = path
            
            # Check if already exists to avoid duplicates
            if self.choice_checkpoint.FindString(name) == wx.NOT_FOUND:
                self.choice_checkpoint.Append(name)
            
            self.choice_checkpoint.SetStringSelection(name)
        dlg.Destroy()
        
    def log(self, message):
        wx.CallAfter(self.textbox_log.AppendText, message + "\n")

    def set_path(self, path):
        self.entry_path.SetValue(path)

    def start_training(self, event):
        dataset_path = self.entry_path.GetValue()
        if not os.path.exists(dataset_path):
            wx.MessageBox(tr("msg_ds_path_missing"), "Error", wx.OK | wx.ICON_ERROR)
            return

        batch_size = self.entry_batch.GetValue()
        val_split = self.entry_val_split.GetValue()
        precision = self.choice_precision.GetStringSelection()
        
        # Set Patience from UI
        try:
            self.PATIENCE_LIMIT = int(self.entry_patience.GetValue())
        except ValueError:
            self.PATIENCE_LIMIT = 50 # Fallback
            
        self.btn_start.Disable()
        self.btn_stop.Enable()
        self.stop_event.clear()
        
        # Get Max Epochs
        try:
             max_epochs = int(self.entry_epochs.GetValue())
        except ValueError:
             max_epochs = 10000
             
        # Get Checkpoint Frequency
        try:
             ckpt_freq = int(self.entry_ckpt_freq.GetValue())
        except ValueError:
             ckpt_freq = 1

        # Get Learning Rate
        try:
            learning_rate = float(self.entry_lr.GetValue())
        except ValueError:
            learning_rate = 0.0001
            wx.CallAfter(wx.MessageBox, tr("msg_invalid_lr"), tr("title_warning"), wx.OK | wx.ICON_WARNING)

        # Get Workers
        num_workers = self.entry_workers.GetValue()
        
        # Get Accumulate Grad Batches
        accumulate_grad_batches = self.entry_accumulate.GetValue()

        # Reset Early Stopping
        self.best_loss = float('inf')
        self.patience_counter = 0
        self.best_loss_epoch = 0
        self.last_seen_epoch = -1

        # Overtraining Logic
        monitor_val_loss = self.chk_overtraining.GetValue()
        if monitor_val_loss:
            # Enforce 5% split if checked
            try:
                current_split = float(self.entry_val_split.GetValue())
            except ValueError:
                current_split = 0.0
            
            if current_split < 0.05:
                self.entry_val_split.SetValue("0.05")
                val_split = "0.05"
                self.log(tr("log_val_split_enforced")) # Need this key or just log string? "Enforcing Validation Split 0.05 for protection"

        # Auto-Export Logic
        autoexport_enabled = self.chk_autoexport.GetValue()
        autoexport_keep_n = self.entry_keep_n.GetValue()
        autoexport_best_x = self.entry_keep_best_x.GetValue()

        threading.Thread(target=self._training_thread, args=(dataset_path, batch_size, val_split, precision, max_epochs, ckpt_freq, learning_rate, monitor_val_loss, num_workers, accumulate_grad_batches, autoexport_enabled, autoexport_keep_n, autoexport_best_x), daemon=True).start()

    def stop_training(self, event):
        # Generate report only if stopped manually (event is not None)
        # For Auto-stop, we generate it before calling this.
        if event:
            self.generate_report(tr("reason_manual"))
            
        self.stop_event.set()
        
        if self.current_container_id:
            self.log("Stopping container...")
            subprocess.run(["docker", "stop", self.current_container_id])
            self.current_container_id = None
        wx.CallAfter(self.btn_start.Enable)
        wx.CallAfter(self.btn_stop.Disable)

    def on_browse_dataset(self, event):
        dlg = wx.DirDialog(self, tr("dlg_select_ds_folder"), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.entry_path.SetValue(path)
        dlg.Destroy()


    def generate_report(self, reason):
        try:
            dataset_path = self.entry_path.GetValue()
            if not os.path.exists(dataset_path):
                return
                
            report_path = os.path.join(dataset_path, "training_report.txt")
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            best_loss_str = f"{self.best_loss:.4f}" if self.best_loss != float('inf') else "N/A"
            
            content = (
                f"{tr('report_header')}\n"
                f"{tr('report_date').format(now)}\n"
                f"{tr('report_stop_reason').format(reason)}\n"
                f"{tr('report_best_loss').format(best_loss_str)}\n"
                f"-----------------------\n"
            )
            
            with open(report_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")
                
            self.log(tr("log_report_saved").format(report_path))
            
        except Exception as e:
            self.log(tr("log_report_error").format(e))

    def generate_analysis_report(self):
        dataset_path = self.entry_path.GetValue()
        if not os.path.exists(dataset_path):
             wx.MessageBox(tr("msg_ds_not_found"), tr("title_error"))
             return
             
        # Import dynamically to avoid top-level issues if dependencies missing
        try:
            from core.analyze_metrics import analyze_training_metrics
            
            # Find metrics.csv
            logs_dir = os.path.join(dataset_path, "lightning_logs")
            # Find latest version with metrics.csv
            import glob
            versions = glob.glob(os.path.join(logs_dir, "version_*"))
            if not versions:
                wx.MessageBox(tr("msg_no_train_log"), "Info")
                return
                
            latest_version = max(versions, key=os.path.getmtime)
            metrics_path = os.path.join(latest_version, "metrics.csv")
            
            if not os.path.exists(metrics_path):
                 wx.MessageBox(tr("msg_metrics_not_found"), "Info")
                 return
                 
            self.log(tr("log_gen_analysis").format(metrics_path))
            report = analyze_training_metrics(metrics_path, dataset_path)
            
            self.log(tr("log_report_generated").format(report))
            wx.MessageBox(tr("msg_analysis_success"), tr("title_success"))
            
        except ImportError:
             wx.MessageBox(tr("msg_libs_missing"), tr("title_error"))
        except Exception as e:
             self.log(tr("log_analysis_error").format(e))
             wx.MessageBox(tr("msg_analysis_error").format(e), tr("title_error"))

    def _training_thread(self, dataset_path, batch_size, val_split, precision, max_epochs, ckpt_freq, learning_rate, monitor_val_loss, num_workers, accumulate_grad_batches, autoexport_enabled=False, autoexport_keep_n=5, autoexport_best_x=10):
        try:
            # Handle Checkpoint Selection
            selected_label = self.choice_checkpoint.GetStringSelection()
            resume_checkpoint_host = None
            resume_checkpoint_container = None
            
            if selected_label in self.checkpoints_map:
                val = self.checkpoints_map[selected_label]
                if val.startswith("PRESET:"):
                    preset_key = val.split(":", 1)[1]
                    self.log(tr("log_downloading_preset").format(preset_key))
                    entry = ConfigManager.PRESET_CHECKPOINTS[preset_key]
                    ckpt_dir = os.path.join(os.getcwd(), "checkpoints")
                    resume_checkpoint_host = ConfigManager.download_checkpoint(entry, ckpt_dir)
                else:
                    resume_checkpoint_host = val
            
            # Helper logic: if user selected a checkpoint, we mount it as /resume.ckpt
            volumes = {dataset_path: "/dataset"}
            
            # Mount local piper_train/__main__.py to override container version
            # We MUST mount ONLY the file, not the folder, or we hide the compiled C extensions (.so) 
            # inside the container, causing ModuleNotFoundError in monotonic_align
            local_piper_train = os.path.abspath(os.path.join(os.getcwd(), "piper_train"))
            local_main_py = os.path.join(local_piper_train, "__main__.py")
            
            if os.path.exists(local_main_py):
                volumes[local_main_py] = "/piper/src/python/piper_train/__main__.py"
                self.log(tr("log_mount_main"))

            # Also mount vits/lightning.py to bring in the new VitsModel with --learning-rate support
            local_lightning_py = os.path.join(local_piper_train, "vits", "lightning.py")
            if os.path.exists(local_lightning_py):
                 volumes[local_lightning_py] = "/piper/src/python/piper_train/vits/lightning.py"
                 self.log(tr("log_mount_lightning"))
            
            if resume_checkpoint_host and os.path.exists(resume_checkpoint_host):
                 resume_checkpoint_container = "/resume.ckpt"
                 volumes[resume_checkpoint_host] = resume_checkpoint_container
                 self.log(tr("log_resuming_ckpt").format(selected_label))
            elif resume_checkpoint_host:
                 self.log(tr("log_ckpt_not_found").format(resume_checkpoint_host))

            train_cmd = ConfigManager.get_train_command(
                batch_size, val_split, quality="medium", precision=precision, 
                max_epochs=max_epochs, resume_checkpoint=resume_checkpoint_container, 
                checkpoint_epochs=ckpt_freq, learning_rate=learning_rate,
                num_workers=num_workers, accumulate_grad_batches=accumulate_grad_batches
            )

            self.log(tr("log_start_train_tty"))
            success, output = DockerManager.run_container(
                image=ConfigManager.DOCKER_IMAGE,
                command=train_cmd,
                volumes=volumes,
                gpus=True,
                detach=True,
                tty=True # Force TTY to ensure tqdm/progress bars are output to logs
            )
            
            if success:
                self.current_container_id = output.strip()
                self.log(tr("log_container_started").format(self.current_container_id))
                
                # Start Log Streamer
                self.log_thread = threading.Thread(target=self._stream_logs, args=(self.current_container_id,))
                self.log_thread.daemon = True
                self.log_thread.start()
                
                # Start CSV Metric Monitor (Robust Loss Tracking)
                self.metric_thread = threading.Thread(target=self._monitor_metrics, args=(dataset_path, monitor_val_loss, autoexport_enabled, autoexport_keep_n, autoexport_best_x))
                self.metric_thread.daemon = True
                self.metric_thread.start()
            else:
                self.log(tr("log_start_container_fail").format(output))
                wx.CallAfter(self.btn_start.Enable)
                wx.CallAfter(self.btn_stop.Disable)

        except Exception as e:
            self.log(f"Exception: {str(e)}")
            wx.CallAfter(self.btn_start.Enable)
            wx.CallAfter(self.btn_stop.Disable)

    def _stream_logs(self, container_id):
        # Continue streaming as long as container is running or we have logs
        while not self.stop_event.is_set():
            # Check if container is actually running before trying to log
            if not self._is_container_running(container_id):
                break
                
            process = subprocess.Popen(
                ["docker", "logs", "-f", "--tail", "10", container_id], 
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8', 
                errors='replace'
            )
            
            while not self.stop_event.is_set():
                line = process.stdout.readline()
                if not line: 
                    if process.poll() is not None:
                        break
                    continue

                stripped = line.strip()
                self.log(stripped)
                
                # Logic for Early Stopping
                # Clean ANSI codes (Colors) for cleaner parsing
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean_line = ansi_escape.sub('', stripped)
                
                # Legacy Regex Parser (Backup)
                # We now prefer the CSV monitor, but this keeps the logs clean-ish
                match = re.search(r'(?:val_loss|loss)\s*[:=]\s*([\d\.]+)', clean_line, re.IGNORECASE)
                
                # Parse tqdm speed (it/s or s/it) for Status Bar
                # Example: 100%|...| 10/100 [00:12<00:00,  1.23it/s, loss=...]
                speed_match = re.search(r'(\d+(?:\.\d+)?)(it/s|s/it)', clean_line)
                if speed_match and self.status_callback:
                    val = speed_match.group(1)
                    unit = speed_match.group(2)
                    self.status_callback(f"Training: {val} {unit}")

                if match:
                     pass # Handled by CSV monitor now to avoid Double Logging
            
            # Wait for process to end
            process.wait()
            self.log(tr("log_stream_ended"))
            
        self.log(tr("log_stream_ended"))
        
        # Check actual container exit code
        try:
            # Use the passed container_id, not self.current_container_id which might be None (in preprocessing)
            target_id = container_id if container_id else self.current_container_id
            
            if target_id:
                inspect_cmd = ["docker", "inspect", target_id, "--format", "{{.State.ExitCode}}"]
                # Provide stderr=subprocess.DEVNULL to suppress docker's "No such object" error in console if any
                exit_code_str = subprocess.check_output(inspect_cmd, text=True, stderr=subprocess.DEVNULL).strip()
                return int(exit_code_str) == 0
            return False
        except subprocess.CalledProcessError:
            # Container was already removed by docker run --rm, exit code is inaccessible
            return True # Assume success if it finished and was removed cleanly
        except Exception as e:
            self.log(tr("msg_exit_code_error").format(e))
            return False

    def _monitor_metrics(self, dataset_dir, monitor_val_loss=False, autoexport_enabled=False, autoexport_keep_n=5, autoexport_best_x=10):
        """
        Monitors metrics.csv in the lightning_logs directory.
        This provides robust access to Loss values, bypassing Docker TTY issues.
        Also handles auto-export capabilities when configured.
        """
        import csv
        import time
        import glob
        import shutil
        import wx.adv
        
        self.log(tr("log_start_csv_monitor"))
        
        # dataset_dir is passed as argument
        logs_dir = os.path.join(dataset_dir, "lightning_logs")
        
        last_read_line = 0
        current_csv_path = None
        
        # Auto-Export Tracking
        last_processed_ckpt = None
        rolling_exports = [] # List of strings to paths
        
        # Reset Best Window tracking variables
        self.autoexport_best_in_window = None
        self.autoexport_window_start_epoch = 0
        
        loss_val = 0.0
        current_epoch = None
        
        while not self.stop_event.is_set():
            time.sleep(2) # Check every 2 seconds
            
            # 1. Find the latest version directory
            if not current_csv_path:
                versions = glob.glob(os.path.join(logs_dir, "version_*"))
                if not versions:
                    continue
                
                # Sort by creation time (or name version_N) to get latest
                latest_version = max(versions, key=os.path.getmtime)
                candidate_csv = os.path.join(latest_version, "metrics.csv")
                
                if os.path.exists(candidate_csv):
                    current_csv_path = candidate_csv
                    self.log(tr("log_metrics_found").format(os.path.basename(latest_version)))
                else:
                    continue
            
            # 2. Read new lines from CSV
            try:
                if not os.path.exists(current_csv_path):
                    continue
                    
                with open(current_csv_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    # Skip header if first read
                    if last_read_line == 0 and len(lines) > 0:
                        header = lines[0].strip().split(',')
                        try:
                            loss_idx = header.index("loss_gen_all")
                            # epoch_idx = header.index("epoch") 
                        except ValueError:
                             # Header not ready or different format
                             continue
                    
                    if len(lines) > last_read_line:
                        # Process new lines
                        header = lines[0].strip().split(',')
                        # Determine which metric to track
                        target_col = "val_loss" if monitor_val_loss else "loss_gen_all"
                        
                        if target_col not in header: continue
                        loss_idx = header.index(target_col)
                        
                        for i in range(max(1, last_read_line), len(lines)):
                            row = lines[i].strip().split(',')
                            if len(row) > loss_idx:
                                try:
                                    loss_val = float(row[loss_idx])
                                    
                                    # Extract epoch if we can to match best in window
                                    current_epoch = None
                                    if "epoch" in header:
                                        epoch_idx = header.index("epoch")
                                        if len(row) > epoch_idx:
                                            current_epoch = int(float(row[epoch_idx]))
                                    
                                    # Log the current status to let the user know we're tracking
                                    if current_epoch is not None:
                                        self.log(f"[Metrics] Epoch {current_epoch} completed | Loss: {loss_val:.4f}")
                                    else:
                                        self.log(f"[Metrics] Step completed | Loss: {loss_val:.4f}")
                                        
                                    # Update Early Stopping Logic
                                    if loss_val < self.best_loss:
                                        self.best_loss = loss_val
                                        self.patience_counter = 0
                                        if current_epoch is not None:
                                            self.best_loss_epoch = current_epoch
                                        # Only log significant improvements or occasionally
                                        self.log(tr("log_improvement").format(loss_val))
                                    else:
                                        if current_epoch is not None:
                                            if hasattr(self, 'best_loss_epoch'):
                                                self.patience_counter = current_epoch - getattr(self, 'best_loss_epoch', 0)
                                            if current_epoch != getattr(self, 'last_seen_epoch', -1):
                                                self.last_seen_epoch = current_epoch
                                                if self.patience_counter % 10 == 0 and self.patience_counter > 0:
                                                    self.log(tr("log_no_improvement").format(self.patience_counter, loss_val))
                                        else:
                                            self.patience_counter += 1
                                            if self.patience_counter % 50 == 0:
                                                 self.log(tr("log_no_improvement").format(self.patience_counter, loss_val))
                                    
                                    if self.patience_counter >= self.PATIENCE_LIMIT:
                                         self.log(tr("log_auto_stop"))
                                         self.generate_report(tr("reason_auto_stop"))
                                         self.stop_training(None)
                                         return
                                         
                                except ValueError:
                                    continue
                        
                        last_read_line = len(lines)
                        
            except Exception as e:
                # self.log(f"Errore lettura CSV: {e}")
                pass
                
            # --- AUTO EXPORT LOGIC ---
            if autoexport_enabled and current_csv_path:
                try:
                    ckpt_dir = os.path.join(os.path.dirname(current_csv_path), "checkpoints")
                    if os.path.exists(ckpt_dir):
                        ckpts = glob.glob(os.path.join(ckpt_dir, "*.ckpt"))
                        if ckpts:
                            # Get the most recently modified checkpoint
                            latest_ckpt = max(ckpts, key=os.path.getmtime)
                            
                            # Only process if it's a new checkpoint we haven't seen yet
                            if latest_ckpt != last_processed_ckpt:
                                # Start a background thread to handle the export and vocalization
                                # Note: we pass loss_val and current_epoch, which we parsed from the CSV above
                                t = threading.Thread(
                                    target=self._trigger_autoexport,
                                    args=(latest_ckpt, loss_val, current_epoch, autoexport_keep_n, autoexport_best_x, dataset_dir, rolling_exports),
                                    daemon=True
                                )
                                t.start()
                                last_processed_ckpt = latest_ckpt
                except Exception as e:
                    self.log(f"Auto-export monitor error: {e}")
            
            # Check if container is still running
            if self.current_container_id and self._is_container_running(self.current_container_id):
                 time.sleep(1)
                 continue
            else:
                 break

    def _trigger_autoexport(self, ckpt_path, loss_val, current_epoch, keep_n, keep_best_x, dataset_dir, rolling_exports):
        """
        Background routine that:
        1. Exports the new checkpoint to ONNX
        2. Speaks the stats using the newly exported model
        3. Manages disk space limits and 'best of' saving
        """
        import subprocess
        import os
        import wx.adv
        
        try:
            exports_dir = os.path.join(dataset_dir, "exported_model")
            os.makedirs(exports_dir, exist_ok=True)
            
            ckpt_filename = os.path.basename(ckpt_path)
            model_base = ckpt_filename.replace(".ckpt", "")
            
            import re
            m = re.search(r'epoch=(\d+)', model_base)
            if m:
                current_epoch = int(m.group(1))
            
            # 1. Export Command
            self.log(f"[Auto-Export] Exporting {model_base}...")
            # We map dataset_dir to /dataset in the background container, and pipe the export there.
            volumes = {dataset_dir: "/dataset"}
            # The path to the checkpoint within the container context
            rel_ckpt_path = os.path.relpath(ckpt_path, dataset_dir).replace('\\', '/')
            cnt_ckpt_path = f"/dataset/{rel_ckpt_path}"
            
            export_cmd = ConfigManager.get_export_command(cnt_ckpt_path, model_name=model_base, config_path="/dataset/config.json")
            
            success, output = DockerManager.run_container(
                image=ConfigManager.DOCKER_IMAGE,
                command=export_cmd,
                volumes=volumes,
                gpus=True,
                detach=False, # Run synchronously in this bg thread
                log_callback=lambda line: self.log(f"[Export ONNX] {line}")
            )
            
            out_onnx_host = os.path.join(exports_dir, f"{model_base}.onnx")
            out_json_host = os.path.join(exports_dir, f"{model_base}.onnx.json")
            
            if not success or not os.path.exists(out_onnx_host):
                self.log(f"[Auto-Export] Export failed: {output}")
                return
                
            self.log(f"[Auto-Export] Export successful: {model_base}")
            
            # Add to rolling list
            rolling_exports.append(model_base)
            
            # Track Best In Window
            if current_epoch is not None:
                if self.autoexport_best_in_window is None or loss_val < self.autoexport_best_in_window[0]:
                    self.autoexport_best_in_window = (loss_val, model_base, current_epoch)
                
                # Have we finished a window?
                # E.g. If we're at epoch 10, window is 1-10. So window completes when (epoch % keep_best_x) == 0
                if current_epoch > 0 and (current_epoch % keep_best_x) == 0:
                    best_loss, best_model, best_epoch = self.autoexport_best_in_window
                    self.log(f"[Auto-Export] Saving best model for epoch window {current_epoch - keep_best_x}-{current_epoch}. Best is {best_model} with loss {best_loss:.4f}.")
                    
                    # Rename the best model so it has a permanent name and escapes the rolling deletron
                    perm_name = f"best_window_{current_epoch}.onnx"
                    perm_json = f"best_window_{current_epoch}.onnx.json"
                    
                    src_onnx = os.path.join(exports_dir, f"{best_model}.onnx")
                    src_json = os.path.join(exports_dir, f"{best_model}.onnx.json")
                    
                    dst_onnx = os.path.join(exports_dir, perm_name)
                    dst_json = os.path.join(exports_dir, perm_json)
                    
                    try:
                        import shutil
                        if os.path.exists(src_onnx): shutil.copy2(src_onnx, dst_onnx)
                        if os.path.exists(src_json): shutil.copy2(src_json, dst_json)
                    except Exception as e:
                        self.log(f"[Auto-Export] Error saving permanent best model: {e}")
                    
                    # Reset window
                    self.autoexport_best_in_window = None
            
            # Cleanup Rolling list based on files in directory
            # We look at the actual filesystem to survive restarts
            all_exports = []
            best_exports = []
            for f in os.listdir(exports_dir):
                if f.endswith(".onnx"):
                    mtime = os.path.getmtime(os.path.join(exports_dir, f))
                    if f.startswith("best_window_"):
                        best_exports.append((mtime, f))
                    elif "preview" not in f:
                        all_exports.append((mtime, f))
            
            # Sort by mtime ascending (oldest first)
            all_exports.sort(key=lambda x: x[0])
            best_exports.sort(key=lambda x: x[0])
            
            # Remove oldest rolling models if we have more than keep_n
            while len(all_exports) > keep_n:
                oldest_mtime, oldest_model_onnx = all_exports.pop(0)
                model_base_name = oldest_model_onnx[:-5] # remove .onnx
                old_onnx = os.path.join(exports_dir, f"{model_base_name}.onnx")
                old_json = os.path.join(exports_dir, f"{model_base_name}.onnx.json")
                try:
                    if os.path.exists(old_onnx): os.remove(old_onnx)
                    if os.path.exists(old_json): os.remove(old_json)
                except Exception as e:
                     self.log(f"[Auto-Export] Error deleting old export {model_base_name}: {e}")
                     
            # Remove oldest best models if we have more than keep_n
            while len(best_exports) > keep_n:
                oldest_mtime, oldest_best_onnx = best_exports.pop(0)
                best_base_name = oldest_best_onnx[:-5] # remove .onnx
                old_onnx = os.path.join(exports_dir, f"{best_base_name}.onnx")
                old_json = os.path.join(exports_dir, f"{best_base_name}.onnx.json")
                try:
                    if os.path.exists(old_onnx): os.remove(old_onnx)
                    if os.path.exists(old_json): os.remove(old_json)
                except Exception as e:
                     self.log(f"[Auto-Export] Error deleting old best export {best_base_name}: {e}")
            
            # 2. Synthesize TTS with Piper
            # Prepare spoken text
            ep_string = f"Epoch {current_epoch}." if current_epoch is not None else ""
            speak_text = f"{ep_string} Loss {loss_val:.3f}."
            
            # Use docker volume mapping
            speak_vols = {exports_dir: "/model_dir"}
            input_txt_host = os.path.join(exports_dir, "input.txt")
            with open(input_txt_host, 'w', encoding='utf-8', newline='\n') as f:
                f.write(speak_text)
                
            out_wav_host = os.path.join(exports_dir, f"{model_base}_preview.wav")
            
            # Run inference in docker
            speak_cmd_str = (
                f"cat /model_dir/input.txt | "
                f"/usr/bin/piper --model /model_dir/{model_base}.onnx --output_file /model_dir/{model_base}_preview.wav "
                f"--espeak_data /usr/share/espeak-ng-data-piper"
            )
            
            full_setup = ConfigManager._get_setup_script()
            speak_cmd = ["/bin/bash", "-c", full_setup + speak_cmd_str]
            
            self.log(f"[Auto-Export] Generating preview audio: '{speak_text}'")
            succ_speak, speak_out = DockerManager.run_container(
                image=ConfigManager.DOCKER_IMAGE,
                command=speak_cmd,
                volumes=speak_vols,
                gpus=False, # Leave GPU for training, CPU perfectly fine for a short TTS run
                detach=False,
                log_callback=lambda line: self.log(f"[Piper TTS] {line}")
            )
            
            # Play Sound
            if succ_speak and os.path.exists(out_wav_host):
                sound = wx.adv.Sound(out_wav_host)
                if sound.IsOk():
                    sound.Play(wx.adv.SOUND_ASYNC)
                    
                # Optionally delete older preview wavs to save space
                for f in os.listdir(exports_dir):
                    if f.endswith("_preview.wav") and model_base not in f:
                        try:
                            os.remove(os.path.join(exports_dir, f))
                        except: pass
            else:
                 self.log(f"[Auto-Export] Failed to generate preview TTS: {speak_out}")
                
        except Exception as e:
            self.log(f"[Auto-Export] Unexpected error: {e}")

    def _is_container_running(self, container_id):
        try:
            cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_id]
            output = subprocess.check_output(cmd, text=True).strip()
            return output == 'true'
        except:
            return False

    def _kill_container(self, container_id):
         try:
             subprocess.run(["docker", "stop", container_id], timeout=10)
         except:
             pass
