import wx
from ui.app import PiperAppFrame

def main():
    app = wx.App(False)
    frame = PiperAppFrame(None, title="Piper Voice Cloner")
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
