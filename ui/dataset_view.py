import wx
import threading
import os
from core.docker_manager import DockerManager
from core.config_manager import ConfigManager
from core.audio_processor import AudioProcessor
from core.translation_manager import tr

class DatasetView(wx.Panel):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.train_view = None
        self.export_view = None
        self.correction_view = None
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Grid Sizer for inputs
        grid_sizer = wx.FlexGridSizer(rows=11, cols=3, vgap=10, hgap=10)
        grid_sizer.AddGrowableCol(1, 1)
        
        # Row 0: Path
        lbl_path = wx.StaticText(self, label=tr("input_folder"))
        grid_sizer.Add(lbl_path, 0, wx.ALIGN_CENTER_VERTICAL)
        
        self.entry_path = wx.TextCtrl(self)
        grid_sizer.Add(self.entry_path, 1, wx.EXPAND)
        
        btn_browse = wx.Button(self, label=tr("browse"))
        btn_browse.Bind(wx.EVT_BUTTON, self.browse_folder)
        grid_sizer.Add(btn_browse, 0)
        
        # Row 1: Language
        lbl_lang = wx.StaticText(self, label=tr("lang_code"))
        grid_sizer.Add(lbl_lang, 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Smart Default Language
        import locale
        try:
            sys_lang = locale.getdefaultlocale()[0]
            default_lang = sys_lang[:2] if sys_lang else "it"
        except:
            default_lang = "it"

        self.entry_lang = wx.TextCtrl(self, value=default_lang)
        grid_sizer.Add(self.entry_lang, 0, wx.ALIGN_LEFT)

        # Single Speaker Checkbox
        self.chk_single_speaker = wx.CheckBox(self, label=tr("single_speaker"))
        self.chk_single_speaker.SetValue(True) # Default for voice cloning usually
        grid_sizer.Add(self.chk_single_speaker, 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Row 2: Silence Threshold
        self.lbl_thresh = wx.StaticText(self, label=tr("lbl_thresh_offset"))
        grid_sizer.Add(self.lbl_thresh, 0, wx.ALIGN_CENTER_VERTICAL)
        
        self.entry_thresh = wx.TextCtrl(self, value="-20")
        grid_sizer.Add(self.entry_thresh, 0, wx.ALIGN_LEFT)
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        
        # Row 3: Minimum Silence Length
        lbl_min_len = wx.StaticText(self, label=tr("lbl_min_len"))
        grid_sizer.Add(lbl_min_len, 0, wx.ALIGN_CENTER_VERTICAL)
        
        self.entry_min_len = wx.TextCtrl(self, value="500")
        grid_sizer.Add(self.entry_min_len, 0, wx.ALIGN_LEFT)
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        
        # Row 4: Relative Threshold Checkbox
        self.chk_relative_thresh = wx.CheckBox(self, label=tr("chk_relative_thresh"))
        self.chk_relative_thresh.SetValue(True) # Default Relative
        self.chk_relative_thresh.Bind(wx.EVT_CHECKBOX, self.on_relative_toggle)
        grid_sizer.Add(self.chk_relative_thresh, 0, wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        
        # Row 5: Combine Short Clips
        self.chk_combine_clips = wx.CheckBox(self, label=tr("chk_combine_clips"))
        self.chk_combine_clips.SetValue(True) # Default Combine
        grid_sizer.Add(self.chk_combine_clips, 0, wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        
        # Row 6: Reject Segments With Numbers
        self.chk_reject_numbers = wx.CheckBox(self, label=tr("chk_reject_numbers"))
        self.chk_reject_numbers.SetValue(True) # Default ON for Piper safety
        grid_sizer.Add(self.chk_reject_numbers, 0, wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        grid_sizer.Add(wx.StaticText(self, label=""), 0) # empty cell
        
        # Row 7: Target Duration
        lbl_target_dur = wx.StaticText(self, label=tr("lbl_target_dur"))
        grid_sizer.Add(lbl_target_dur, 0, wx.ALIGN_CENTER_VERTICAL)
        self.entry_target_dur = wx.TextCtrl(self, value="10.0")
        grid_sizer.Add(self.entry_target_dur, 0, wx.ALIGN_LEFT)
        grid_sizer.Add(wx.StaticText(self, label=""), 0)

        # Row 8: Max Duration
        lbl_max_dur = wx.StaticText(self, label=tr("lbl_max_dur"))
        grid_sizer.Add(lbl_max_dur, 0, wx.ALIGN_CENTER_VERTICAL)
        self.entry_max_dur = wx.TextCtrl(self, value="15.0")
        grid_sizer.Add(self.entry_max_dur, 0, wx.ALIGN_LEFT)
        grid_sizer.Add(wx.StaticText(self, label=""), 0)

        # Row 9: Min Duration
        lbl_min_dur = wx.StaticText(self, label=tr("lbl_min_dur"))
        grid_sizer.Add(lbl_min_dur, 0, wx.ALIGN_CENTER_VERTICAL)
        self.entry_min_dur = wx.TextCtrl(self, value="0.5")
        grid_sizer.Add(self.entry_min_dur, 0, wx.ALIGN_LEFT)
        grid_sizer.Add(wx.StaticText(self, label=""), 0)
        
        main_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Info Text
        msg = tr("process_note")
        main_sizer.Add(wx.StaticText(self, label=msg), 0, wx.ALL, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_preprocess = wx.Button(self, label=tr("start_process"))
        self.btn_preprocess.Bind(wx.EVT_BUTTON, self.run_preprocess)
        btn_sizer.Add(self.btn_preprocess, 0, wx.RIGHT, 10)
        
        self.btn_merge = wx.Button(self, label=tr("merge_ds"))
        self.btn_merge.Bind(wx.EVT_BUTTON, self.on_merge_btn)
        btn_sizer.Add(self.btn_merge, 0, wx.RIGHT, 10)
        
        
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Log
        self.textbox_log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        main_sizer.Add(self.textbox_log, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)

    def on_relative_toggle(self, event):
        if self.chk_relative_thresh.GetValue():
            self.lbl_thresh.SetLabel(tr("lbl_thresh_offset"))
            if self.entry_thresh.GetValue() == "-32":
                self.entry_thresh.SetValue("-20")
        else:
            self.lbl_thresh.SetLabel(tr("lbl_thresh_abs"))
            if self.entry_thresh.GetValue() == "-20":
                self.entry_thresh.SetValue("-32")

    def browse_folder(self, event):
        dlg = wx.DirDialog(self, tr("dlg_choose_folder_mp3"))
        if dlg.ShowModal() == wx.ID_OK:
            self.entry_path.SetValue(dlg.GetPath())
        dlg.Destroy()

    def log(self, message):
        wx.CallAfter(self.textbox_log.AppendText, message + "\n")

    def run_preprocess(self, event):
        path = self.entry_path.GetValue()
        if not path or not os.path.exists(path):
            wx.MessageBox(tr("msg_invalid_source"), "Error", wx.OK | wx.ICON_ERROR)
            return
            
        is_single = self.chk_single_speaker.GetValue()
        
        try:
            silence_thresh = float(self.entry_thresh.GetValue())
        except ValueError:
            silence_thresh = -32.0
            
        try:
            min_silence_len = int(self.entry_min_len.GetValue())
        except ValueError:
            min_silence_len = 500
            
        is_relative = self.chk_relative_thresh.GetValue()
        combine_clips = self.chk_combine_clips.GetValue()
        reject_numbers = self.chk_reject_numbers.GetValue()
        
        try:
            target_dur = float(self.entry_target_dur.GetValue())
        except ValueError:
            target_dur = 10.0
            
        try:
            max_dur = float(self.entry_max_dur.GetValue())
        except ValueError:
            max_dur = 15.0
            
        try:
            min_dur = float(self.entry_min_dur.GetValue())
        except ValueError:
            min_dur = 0.5

        self.btn_preprocess.Disable()
        if self.status_callback:
            self.status_callback(tr("status_starting_smart"))
            
        threading.Thread(
            target=self._run_smart_thread,
            args=(path, is_single, silence_thresh, min_silence_len, is_relative, combine_clips, target_dur, max_dur, min_dur, reject_numbers),
            daemon=True
        ).start()

    def _run_smart_thread(self, source_path, is_single_speaker, silence_thresh, min_silence_len, is_relative, combine_clips, target_dur=10.0, max_dur=15.0, min_dur=0.5, reject_numbers=True):
        try:
            # 1. Define Output Path
            processed_dir = os.path.join(source_path, "processed")
            if not os.path.exists(processed_dir):
                os.makedirs(processed_dir)
                
            self.log(tr("log_processing_from").format(source_path))
            self.log(tr("log_output_folder").format(processed_dir))
            self.log(tr("log_starting_docker_smart"))
            
            if self.status_callback:
                self.status_callback(tr("status_download_start_docker"))
            
            # 2. Run Smart Pipeline (Split + Transcribe)
            # We pass self.log as the callback so Docker output is streamed to the UI
            lang = self.entry_lang.GetValue()
            success, output = AudioProcessor.run_smart_pipeline(
                source_path, 
                processed_dir, 
                lang=lang, 
                silence_thresh=silence_thresh, 
                min_silence_len=min_silence_len, 
                is_relative=is_relative,
                combine_clips=combine_clips,
                target_dur=target_dur,
                max_dur=max_dur,
                min_dur=min_dur,
                reject_numbers=reject_numbers,
                status_callback=self.log
            )
            
            if success:
                self.log(tr("log_step1_complete"))
                self.log(tr("log_all_complete"))
                
                # Pass path to valid siblings
                if self.preprocess_view:
                    wx.CallAfter(self.preprocess_view.set_path, processed_dir)
                if self.correction_view:
                     wx.CallAfter(self.correction_view.set_path, processed_dir)
                    
                if self.status_callback: self.status_callback(tr("status_ready_train")) # Maybe "Ready for Preprocess"?

            else:
                self.log(tr("log_smart_fail").format(output))
                if self.status_callback: self.status_callback(tr("status_process_fail"))

        except Exception as e:
            self.log(f"Exception: {str(e)}")
        finally:
            wx.CallAfter(self.btn_preprocess.Enable)


    def set_siblings(self, preprocess, correction=None):
        self.preprocess_view = preprocess
        self.correction_view = correction
        self.train_view = None # No longer directly linked
        self.export_view = None

    def on_merge_btn(self, event):
        target_path = self.entry_path.GetValue()
        if not target_path or not os.path.exists(os.path.join(target_path, "metadata.csv")):
            wx.MessageBox(tr("msg_load_target_first"), tr("title_error"))
            return

        dlg = wx.DirDialog(self, tr("dlg_select_new_source"))
        if dlg.ShowModal() == wx.ID_OK:
            source_path = dlg.GetPath()
            self.run_merge(source_path, target_path)
        dlg.Destroy()


    def run_merge(self, source_path, target_path):
        import shutil
        import time
        import re
        import tempfile

        source_meta = os.path.join(source_path, "metadata.csv")
        target_meta = os.path.join(target_path, "metadata.csv")

        if not os.path.exists(source_meta):
            wx.MessageBox(tr("msg_invalid_dataset_missing_meta"), tr("title_error"))
            return

        def looks_like_embedded_metadata(text):
            if "|" in text:
                return True
            if re.search(r"\b[\w()\- ]+_\d{4}\b", text):
                return True
            return False

        def validate_merge_line(seg_id, text):
            seg_id = (seg_id or "").strip()
            text = (text or "").strip()

            if not seg_id:
                return False, tr("reason_blank_segment_id")
            if not text:
                return False, tr("reason_blank_transcript")
            if "\n" in text or "\r" in text:
                return False, tr("reason_newline_transcript")
            if len(text) > 400:
                return False, tr("reason_length_exceeds").format(len(text))
            if len(text.split()) > 80:
                return False, tr("reason_word_count_exceeds").format(len(text.split()))
            if looks_like_embedded_metadata(text):
                return False, tr("reason_embedded_metadata")
            return True, ""

        def load_safe_rows(metadata_path):
            rows = []
            ids = set()
            with open(metadata_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
                for raw_line in f:
                    line = raw_line.rstrip("\n")
                    if "|" not in line:
                        self.log(tr("log_skip_malformed_no_pipe").format(line[:80]))
                        continue
                    seg_id, seg_text = line.split("|", 1)
                    seg_id = seg_id.strip()
                    seg_text = seg_text.strip()

                    is_valid, reason = validate_merge_line(seg_id, seg_text)
                    if not is_valid:
                        self.log(tr("log_skip_malformed_reason").format(seg_id or '[blank]', reason))
                        continue
                    if seg_id in ids:
                        self.log(tr("log_skip_duplicate").format(seg_id))
                        continue

                    rows.append((seg_id, seg_text))
                    ids.add(seg_id)
            return rows, ids

        def atomic_rewrite_metadata(metadata_path, rows):
            metadata_dir = os.path.dirname(metadata_path) or "."
            fd, temp_path = tempfile.mkstemp(prefix="metadata_merge_", suffix=".tmp", dir=metadata_dir, text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as temp_f:
                    for seg_id, seg_text in rows:
                        temp_f.write(f"{seg_id}|{seg_text}\n")
                    temp_f.flush()
                    os.fsync(temp_f.fileno())
                os.replace(temp_path, metadata_path)
            except Exception:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass
                raise

        # Backup
        try:
            shutil.copy(target_meta, target_meta + ".bak")
            self.log(tr("log_backup_created"))
        except Exception as e:
            self.log(tr("log_backup_error").format(e))
            return

        count = 0
        skipped = 0

        try:
            source_rows, _ = load_safe_rows(source_meta)
            target_rows, existing_ids = load_safe_rows(target_meta)

            target_wav_dir = os.path.join(target_path, "wavs")
            if not os.path.exists(target_wav_dir):
                os.makedirs(target_wav_dir, exist_ok=True)

            for fid, text in source_rows:
                src_wav = os.path.join(source_path, fid + ".wav")
                if not os.path.exists(src_wav):
                    src_wav = os.path.join(source_path, "wavs", fid + ".wav")

                if not os.path.exists(src_wav):
                    self.log(tr("log_skip_missing_wav").format(fid))
                    skipped += 1
                    continue

                final_id = fid
                if final_id in existing_ids:
                    final_id = f"{fid}_{int(time.time())}"
                    self.log(tr("log_duplicate_id_renamed").format(fid, final_id))

                is_valid, reason = validate_merge_line(final_id, text)
                if not is_valid:
                    self.log(tr("log_skip_merge_reason").format(fid, reason))
                    skipped += 1
                    continue

                dest_wav = os.path.join(target_wav_dir, final_id + ".wav")
                shutil.copy2(src_wav, dest_wav)

                target_rows.append((final_id, text))
                existing_ids.add(final_id)
                count += 1

            atomic_rewrite_metadata(target_meta, target_rows)

            self.log(tr("log_merge_complete").format(count, skipped))
            wx.MessageBox(tr("msg_merge_complete").format(count), "Info")

        except Exception as e:
            self.log(tr("log_merge_error").format(e))
            wx.MessageBox(f"{tr('log_merge_error').format(e)}", tr("invalid_path"), wx.OK | wx.ICON_ERROR)
