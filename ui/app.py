import wx
import threading
import sys
import os
from core.docker_manager import DockerManager
from core.config_manager import ConfigManager
from core.translation_manager import tr, TranslationManager
from ui.dataset_view import DatasetView
from ui.train_view import TrainView
from ui.export_view import ExportView
from ui.correction_view import CorrectionView
from ui.test_view import TestView
from ui.translation_view import TranslationView
from ui.preprocess_view import PreprocessView

class PiperAppFrame(wx.Frame):
    def __init__(self, parent, title="Piper Voice Cloner"):
        super().__init__(parent, title=title, size=(1000, 700))
        
        # Initialize Translation
        self.tm = TranslationManager.get_instance()
        
        # Menu Bar
        menubar = wx.MenuBar()
        
        # Language Menu (replaces File Menu)
        lang_menu = wx.Menu()
        
        # Language Items
        self.item_it = lang_menu.AppendRadioItem(101, "Italiano")
        self.item_en = lang_menu.AppendRadioItem(102, "English")
        
        # Check current language
        current_lang = self.tm._language
        if current_lang == "en":
            self.item_en.Check()
        else:
            self.item_it.Check()
            
        lang_menu.AppendSeparator()
        lang_menu.Append(wx.ID_EXIT, tr("menu_exit"), tr("menu_exit_help"))
            
        menubar.Append(lang_menu, tr("menu_language"))
        self.SetMenuBar(menubar)
        
        # Bind Menu Events
        self.Bind(wx.EVT_MENU, self.on_change_language, id=101)
        self.Bind(wx.EVT_MENU, self.on_change_language, id=102)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), id=wx.ID_EXIT)

        # Ensure cleanup on close
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.panel = wx.Panel(self)
        self.notebook = wx.Notebook(self.panel)
        
        # Views
        self.translation_view = TranslationView(self.notebook, status_callback=self.set_status)
        self.dataset_view = DatasetView(self.notebook, status_callback=self.set_status)
        self.correction_view = CorrectionView(self.notebook, status_callback=self.set_status)
        self.preprocess_view = PreprocessView(self.notebook, status_callback=self.set_status)
        self.train_view = TrainView(self.notebook, status_callback=self.set_status)
        self.test_view = TestView(self.notebook, status_callback=self.set_status)
        self.export_view = ExportView(self.notebook, status_callback=self.set_status)
        
        # Link views for auto-filling paths
        # Chain updates: Dataset -> Preprocess -> Train -> Export ...
        # Simplified linking manually here or via method
        self.dataset_view.set_siblings(self.preprocess_view, self.correction_view)
        # We need to ensure PreprocessView updates TrainView
        # But set_siblings isn't defined generic. 
        # For now, let's keep it simple or assume user manually navigates?
        # Ideally, successful preprocess should set path in TrainView.
        # Let's add simple set methods where needed if not present.
        self.preprocess_view.set_train_view(self.train_view)
        
        # Link Test View to Train View for GPU Safety (Switch to CPU if training)
        self.test_view.set_train_view(self.train_view)
        
        # Add tabs in requested logical order
        # 1. Translation (Independent)
        self.notebook.AddPage(self.translation_view, tr("tab_translation"))
        # 2. Dataset Source (Whisper/Split)
        self.notebook.AddPage(self.dataset_view, tr("tab_dataset"))
        # 3. Correction
        self.notebook.AddPage(self.correction_view, tr("tab_correction"))
        # 4. Preprocessing (Piper)
        self.notebook.AddPage(self.preprocess_view, tr("btn_preprocess_ds")) # "Preprocess Dataset"
        # 5. Training
        self.notebook.AddPage(self.train_view, tr("tab_train"))
        # 6. Export (Before Test)
        self.notebook.AddPage(self.export_view, tr("tab_export"))
        # 7. Test Model
        self.notebook.AddPage(self.test_view, tr("tab_test"))
        
        # Accessibility Fix: Handle Shift+Tab on Notebook Tabs
        self.notebook.Bind(wx.EVT_NAVIGATION_KEY, self.on_notebook_nav)
        
        # Status Bar
        self.CreateStatusBar()
        self.SetStatusText(tr("status_ready"))
        self.gpu_status_msg = tr("status_init")
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.panel.SetSizer(sizer)
        
        # Accessibility Fix: Handle Tab (Forward) inside Pages to loop back to Tabs
        for page in [self.translation_view, self.dataset_view, self.correction_view, self.preprocess_view, self.train_view, self.export_view, self.test_view]:
            self.bind_page_navigation(page)
        
        # Shortcuts
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_F1, 1001),
            (wx.ACCEL_NORMAL, wx.WXK_F2, 1002)
        ])
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.show_system_status, id=1001)
        self.Bind(wx.EVT_MENU, self.focus_tabs, id=1002)
        
        # Initial Checks
        self.check_environment()
        
        # Center on screen
        self.Centre()

    def on_change_language(self, event):
        new_lang = "it" if event.GetId() == 101 else "en"
        if new_lang == self.tm._language:
            return
            
        # Update Config
        cm = ConfigManager()
        cm.config["language"] = new_lang
        cm.save_config(cm.config)
        
        # Ask Restart
        res = wx.MessageBox(
            tr("msg_restart_required"),
            tr("menu_restart_required"),
            wx.YES_NO | wx.ICON_QUESTION
        )
        
        if res == wx.YES:
            self.Close()
            # In a real packaged app, getting auto-restart is hard. 
            # We just close for now, user re-launches.

    def check_environment(self):
        """Run checks in background"""
        def _check():
            # 0. Cleanup Stale Containers
            wx.CallAfter(self.SetStatusText, tr("status_cleaning_stale"))
            DockerManager.cleanup_stale_containers(ConfigManager.DOCKER_IMAGE)
            
            wx.CallAfter(self.SetStatusText, tr("status_checking_docker"))
            self.gpu_status_msg = tr("status_checking_docker")
            
            if not DockerManager.is_docker_installed():
                msg = tr("status_docker_not_found")
                self.gpu_status_msg = f"Status: Error - {msg}"
                wx.CallAfter(self.show_error, msg)
                return

            wx.CallAfter(self.SetStatusText, tr("status_checking_gpu"))
            self.gpu_status_msg = tr("status_checking_gpu")
            
            success, msg = DockerManager.check_gpu_support()
            if success:
                final_msg = tr("status_ready_gpu")
                self.gpu_status_msg = final_msg
                wx.CallAfter(self.SetStatusText, final_msg)
            else:
                final_msg = f"{tr('status_gpu_fail')} {msg}"
                self.gpu_status_msg = final_msg
                wx.CallAfter(self.show_error, final_msg)

        threading.Thread(target=_check, daemon=True).start()

    def show_system_status(self, event):
        wx.MessageBox(self.gpu_status_msg, tr("title_system_status"), wx.OK | wx.ICON_INFORMATION)

    def focus_tabs(self, event):
        self.notebook.SetFocus()

    def set_status(self, text):
        wx.CallAfter(self.SetStatusText, f"Status: {text}")

    def show_error(self, message):
        self.SetStatusText(f"Status: Error - {message}")
        wx.MessageBox(message, tr("title_env_error"), wx.OK | wx.ICON_ERROR)

    def on_notebook_nav(self, event):
        """
        Fix for Shift+Tab getting stuck on Notebook Tabs.
        If we are navigating BACKWARDS and the event comes from the Notebook (Tabs),
        we force focus into the LAST element of the current page.
        """
        # Critical: Ignore Window Change events (Ctrl+Tab, Ctrl+Shift+Tab)
        if event.IsWindowChange():
            event.Skip()
            return

        if not event.GetDirection(): # Backward (Shift+Tab)
            # Only intervene if the focus is CURRENTLY on the Notebook (Tabs)
            # This allows Shift+Tab from inside the page to reach the tabs naturally.
            if self.FindFocus() == self.notebook:
                current_page = self.notebook.GetCurrentPage()
                if current_page:
                    # Try to navigate into the page from the bottom
                    if current_page.NavigateIn(wx.NavigationKeyEvent.IsBackward):
                        return # Successfully moved focus into the page
        
        event.Skip()

    def bind_page_navigation(self, page):
        """
        Bind navigation event to the PAGE to intercept Forward Loop.
        Use this instead of binding keys to specific children, as Buttons consume Tab.
        """
        page.Bind(wx.EVT_NAVIGATION_KEY, self.on_page_nav)
        
    def get_last_focusable_child(self, page):
        """Scan backwards to find the true last focusable element"""
        for child in reversed(page.GetChildren()):
             try:
                if child.AcceptsFocusFromKeyboard():
                    return child
             except:
                if child.AcceptsFocus():
                    return child
        return None

    def on_page_nav(self, event):
        """
        Handle Tab (Forward) on the Page.
        If we are on the LAST element -> Jump to Tabs.
        """
        # Critical: Ignore Window Change events (Ctrl+Tab)
        if event.IsWindowChange():
            event.Skip()
            return

        if event.GetDirection(): # Forward
            current_page = self.notebook.GetCurrentPage()
            last_child = self.get_last_focusable_child(current_page)
            
            # Check if current focus is the last child
            if last_child and wx.Window.FindFocus() == last_child:
                self.notebook.SetFocus()
                return # Handled
                
        event.Skip()

    def on_close(self, event):
        """Handle application close: ensure docker containers are stopped."""
        try:
            # Stop Training if running
            if self.train_view and self.train_view.current_container_id:
                self.train_view.stop_training(None)
                
            # We could also forcefully cleanup any containers here too
            # DockerManager.cleanup_stale_containers(ConfigManager.DOCKER_IMAGE)
            # But that might delay closing too much. 
            # The stop_training call should triggers 'docker stop'.
        except:
            pass
        
        self.Destroy()
