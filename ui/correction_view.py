import wx
import wx.adv
import os
import csv
import shutil
from core.translation_manager import tr

class CorrectionView(wx.Panel):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.dataset_path = ""
        self.metadata_path = ""
        self.items = [] # List of {"id": "file_id", "text": "transcript", "audio_path": "path"}
        self.current_index = -1
        self.deleted_ids = set()
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # --- Top: Path Selection ---
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(wx.StaticText(self, label=tr("dataset_path")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_path = wx.TextCtrl(self, style=wx.TE_READONLY)
        path_sizer.Add(self.entry_path, 1, wx.EXPAND)
        
        self.btn_browse = wx.Button(self, label=tr("browse"))
        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        path_sizer.Add(self.btn_browse, 0, wx.LEFT, 5)
        
        self.btn_load = wx.Button(self, label=tr("reload"))
        self.btn_load.Bind(wx.EVT_BUTTON, self.on_load_btn)
        path_sizer.Add(self.btn_load, 0, wx.LEFT, 5)

        self.btn_search = wx.Button(self, label=tr("search_btn"))
        self.btn_search.Bind(wx.EVT_BUTTON, self.on_search)
        path_sizer.Add(self.btn_search, 0, wx.LEFT, 5)
        
        main_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # --- Middle: Editor ---
        
        # Info Label (Segment X of Y) - Important for Screen Reader context
        self.lbl_info = wx.StaticText(self, label=tr("no_dataset_loaded"))
        font_large = self.lbl_info.GetFont()
        font_large.SetPointSize(12)
        font_large.SetWeight(wx.FONTWEIGHT_BOLD)
        self.lbl_info.SetFont(font_large)
        main_sizer.Add(self.lbl_info, 0, wx.ALL, 10)
        
        # ID Label
        self.lbl_id = wx.StaticText(self, label=tr("lbl_id_default"))
        main_sizer.Add(self.lbl_id, 0, wx.LEFT | wx.RIGHT, 10)
        
        # Text Editor
        self.text_transcript = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        font_edit = self.text_transcript.GetFont()
        font_edit.SetPointSize(12)
        self.text_transcript.SetFont(font_edit)
        main_sizer.Add(self.text_transcript, 1, wx.EXPAND | wx.ALL, 10)
        
        # --- Bottom: Controls ---
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_prev = wx.Button(self, label=tr("prev_btn"))
        self.btn_prev.Bind(wx.EVT_BUTTON, self.on_prev)
        btn_sizer.Add(self.btn_prev, 0, wx.RIGHT, 5)
        
        self.btn_play = wx.Button(self, label=tr("play_btn"))
        self.btn_play.Bind(wx.EVT_BUTTON, self.on_play)
        btn_sizer.Add(self.btn_play, 0, wx.RIGHT, 5)
        
        self.btn_delete = wx.Button(self, label=tr("btn_delete_row"))
        self.btn_delete.SetBackgroundColour(wx.Colour(200, 50, 50))
        self.btn_delete.SetForegroundColour(wx.Colour(255, 255, 255))
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        btn_sizer.Add(self.btn_delete, 0, wx.RIGHT, 5)
        
        self.btn_save = wx.Button(self, label=tr("save_btn"))
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        btn_sizer.Add(self.btn_save, 0, wx.RIGHT, 5)
        
        self.btn_next = wx.Button(self, label=tr("next_btn"))
        self.btn_next.Bind(wx.EVT_BUTTON, self.on_next)
        btn_sizer.Add(self.btn_next, 0)
        
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        
        # Shortcuts
        # F3 -> Search
        # F4 -> Prev
        # F5 -> Play
        # F6 -> Next
        # Ctrl+S -> Save
        entries = [
            (wx.ACCEL_NORMAL, wx.WXK_F3, self.btn_search.GetId()),
            (wx.ACCEL_NORMAL, wx.WXK_F5, self.btn_play.GetId()),
            (wx.ACCEL_CTRL, ord('S'), self.btn_save.GetId()),
            (wx.ACCEL_NORMAL, wx.WXK_F6, self.btn_next.GetId()),
            (wx.ACCEL_NORMAL, wx.WXK_F4, self.btn_prev.GetId())
        ]
        accel = wx.AcceleratorTable(entries)
        self.SetAcceleratorTable(accel)

        # Bind shortcuts explicitly
        self.Bind(wx.EVT_MENU, self.on_search, id=self.btn_search.GetId())
        self.Bind(wx.EVT_MENU, self.on_play, id=self.btn_play.GetId())
        self.Bind(wx.EVT_MENU, self.on_save, id=self.btn_save.GetId())
        self.Bind(wx.EVT_MENU, self.on_next, id=self.btn_next.GetId())
        self.Bind(wx.EVT_MENU, self.on_prev, id=self.btn_prev.GetId())

    def set_path(self, path):
        self.entry_path.SetValue(path)
        # Auto load if valid
        if os.path.exists(os.path.join(path, "metadata.csv")):
            self.load_dataset(path)

    def on_browse(self, event):
        dlg = wx.DirDialog(self, tr("select_processed_folder"))
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.set_path(path) # This calls load automatically
            
        dlg.Destroy()

    def on_load_btn(self, event):
        path = self.entry_path.GetValue()
        if os.path.exists(path):
            self.load_dataset(path)
        else:
             wx.MessageBox(tr("invalid_path"), "Errore")

    def on_search(self, event):
        if not self.items:
            return
            
        dlg = wx.TextEntryDialog(self, tr("search_msg"), tr("title_search"))
        if dlg.ShowModal() == wx.ID_OK:
            query = dlg.GetValue().strip().lower()
            if query:
                found = False
                # Start searching from current index + 1 to find "next" occurrences?
                # Or always from start? Default to start for simplicity or allow wrap.
                # Let's search from start for now to ensure we find it.
                for i, item in enumerate(self.items):
                    if query in item['id'].lower() or query in item['text'].lower():
                        self.load_item(i)
                        self.text_transcript.SetFocus()
                        found = True
                        break
                
                if not found:
                    wx.MessageBox(tr("no_results"), tr("title_search"))
        dlg.Destroy()

    def load_dataset(self, path):
        # Check if we are reloading the same dataset to preserve state
        same_dataset = (self.dataset_path == path) or (os.path.normpath(self.dataset_path) == os.path.normpath(path))
        current_id = None
        if same_dataset and 0 <= self.current_index < len(self.items):
             current_id = self.items[self.current_index]['id']
        else:
             self.deleted_ids = set()
             
        self.dataset_path = path
        self.metadata_path = os.path.join(path, "metadata.csv")
        
        if not os.path.exists(self.metadata_path):
            if self.status_callback:
                self.status_callback(f"{tr('no_metadata_found')} {path}")
            return
            
        new_items = []
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" in line:
                        parts = line.strip().split("|")
                        if len(parts) >= 2:
                            fid = parts[0]
                            txt = parts[1]
                            wav_path = os.path.join(path, "wavs", fid + ".wav")
                            if not os.path.exists(wav_path):
                                wav_path = os.path.join(path, fid + ".wav")
                                
                            new_items.append({
                                "id": fid,
                                "text": txt,
                                "audio_path": wav_path
                            })
            
            self.items = new_items
            
            if self.items:
                # Restore Position
                new_index = 0
                if current_id:
                    # Find index of current_id
                    for i, item in enumerate(self.items):
                        if item['id'] == current_id:
                            new_index = i
                            break
                            
                self.current_index = new_index
                self.load_item(new_index)
                
                if self.status_callback:
                    self.status_callback(tr("segments_loaded").format(len(self.items)))
                
                # Only focus if it was a fresh load, otherwise stealing focus on recurring updates might be annoying?
                # Actually, if user hit Reload, they expect focus.
                self.text_transcript.SetFocus() 
            else:
                self.lbl_info.SetLabel(tr("no_segments_found"))
                self.current_index = -1
                
        except Exception as e:
            wx.MessageBox(tr("msg_load_error").format(e), "Errore")

    def load_item(self, index):
        if 0 <= index < len(self.items):
            item = self.items[index]
            self.current_index = index
            
            self.lbl_info.SetLabel(tr("segment_progress").format(index + 1, len(self.items)))
            self.lbl_id.SetLabel(tr("lbl_id_fmt").format(item['id']))
            # Only update text if it CHANGED to avoid overwriting user edits during a "live" refresh?
            # Ideally: check if text_transcript is dirty?
            # But here reload implies "get from disk". 
            # If user is editing, they shouldn't hit reload until saved.
            # But the user asked for "constantly updated csv". 
            # If we are just appending, existing items don't change.
            current_ui_text = self.text_transcript.GetValue()
            if current_ui_text != item['text']:
                 self.text_transcript.SetValue(item['text'])
            
            # Accessibility: Announce via status or just let focus do work?
            # Focus is already on text ctrl usually.
            
    def save_current_memory(self):
        """Save text from UI to memory list"""
        if 0 <= self.current_index < len(self.items):
            new_text = self.text_transcript.GetValue().strip()
            self.items[self.current_index]['text'] = new_text

    def save_to_disk(self):
        """
        Write items back to metadata.csv safely.
        CRITICAL: We must NOT simply overwrite with self.items, because the background process
        might have appended new lines that self.items doesn't know about yet.
        Strategy: Read Disk -> Update matching IDs from Memory -> Write Disk.
        """
        try:
            # 1. Create a quick lookup map from Memory
            # { "file_id": "new_text" }
            memory_map = {item['id']: item['text'] for item in self.items}
            
            if not os.path.exists(self.metadata_path):
                # Should not happen if loaded, but just in case
                return False

            # Backup first
            shutil.copy(self.metadata_path, self.metadata_path + ".bak")
            
            # 2. Read ALL lines from Disk (including new ones we haven't seen)
            final_lines = []
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "|" in line:
                        parts = line.split("|")
                        fid = parts[0]
                        original_text = parts[1]
                        
                        if fid in self.deleted_ids:
                            continue # Successfully skip this line!
                            
                        # If this ID is in our memory, use the user's edited text
                        if fid in memory_map:
                            # We keep the structure "id|text"
                            # We do NOT assume we can just replace the whole line blindly, 
                            # but reconstructing it is safe for this simple format.
                            final_lines.append(f"{fid}|{memory_map[fid]}")
                        else:
                            # This is likely a NEW line added by the background process
                            # Keep it exactly as is
                            final_lines.append(line)
                    else:
                        # Empty lines or garbage? Keep them or drop?
                        # Safer to keep if unsure, but Piper expects id|text.
                        if line: 
                            final_lines.append(line)

            # 3. Write the merged result back
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                for line in final_lines:
                    f.write(line + "\n")
                    
            return True
        except Exception as e:
            wx.MessageBox(f"{tr('save_error')} {e}", "Errore")
            return False

    def on_delete(self, event):
        if 0 <= self.current_index < len(self.items):
            item = self.items[self.current_index]
            self.deleted_ids.add(item['id'])
            
            # Try to erase the wav file to reclaim disk space immediately
            if os.path.exists(item['audio_path']):
                try:
                    os.remove(item['audio_path'])
                except Exception as e:
                    if self.status_callback:
                        self.status_callback(tr("status_fail_delete").format(item['audio_path'], e))
                        
            # Remove from grid
            self.items.pop(self.current_index)
            
            # Navigate to adjacent segment
            if not self.items:
                self.current_index = -1
                self.text_transcript.SetValue("")
                self.lbl_id.SetLabel(tr("no_items_left"))
                self.lbl_info.SetLabel(tr("no_segments_found"))
                if self.status_callback:
                    self.status_callback(tr("status_all_deleted"))
            else:
                if self.current_index >= len(self.items):
                    self.current_index = len(self.items) - 1
                self.load_item(self.current_index)
                
            # Immediately save to disk, so delete takes effect concurrently with transcribing
            self.save_to_disk()

    def on_play(self, event):
        if 0 <= self.current_index < len(self.items):
            wav_path = self.items[self.current_index]['audio_path']
            if os.path.exists(wav_path):
                try:
                    sound = wx.adv.Sound(wav_path)
                    sound.Play(wx.adv.SOUND_ASYNC)
                except Exception as e:
                    if self.status_callback:
                        self.status_callback(tr("msg_playback_error").format(e))
            else:
                 if self.status_callback:
                        self.status_callback(f"{tr('missing_audio')} {wav_path}")

    def on_save(self, event):
        self.save_current_memory()
        if self.save_to_disk():
            if self.status_callback:
                self.status_callback(tr("saved"))
            # Beep or feedback?
            # wx.Bell() # Can be annoying. Status update is safer.

    def on_next(self, event):
        self.save_current_memory() # Auto-save memory on nav
        self.save_to_disk() # Auto-save disk on nav (safe approach)
        
        if self.current_index < len(self.items) - 1:
            self.load_item(self.current_index + 1)
        else:
            if self.status_callback:
                self.status_callback(tr("end_of_list"))

    def on_prev(self, event):
        self.save_current_memory()
        self.save_to_disk()
        
        if self.current_index > 0:
            self.load_item(self.current_index - 1)
