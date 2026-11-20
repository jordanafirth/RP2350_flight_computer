"""KiCad 10 standalone scripting with explicit settings and I/O ownership.

Use KiCad's bundled Python. The module-level LoadBoard convenience function
depends on an editor-global Pgm instance on this installation; the I/O plugin
accepts an explicit project and works without an editor window.
"""
import wx
import pcbnew

app = wx.App(False)
settings = pcbnew.SETTINGS_MANAGER()
plugin = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

def load_board(path,project_path=None):
    from pathlib import Path
    project=Path(project_path) if project_path else Path(path).with_suffix('.kicad_pro')
    if project.exists():
        settings.LoadProject(str(project.resolve()))
    board=plugin.LoadBoard(str(path), None, None, settings.Prj())
    board.SetProject(settings.Prj())
    board.SynchronizeNetsAndNetClasses(False)
    return board

def save_board(board, path):
    plugin.SaveBoard(str(path), board)
