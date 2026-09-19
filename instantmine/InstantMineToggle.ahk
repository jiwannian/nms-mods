#Requires AutoHotkey v2.0
#SingleInstance Force
; 启动 Python 开关。真正的内存读写在 instantmine_toggle.py。

py := "C:\Program Files\Python310\python.exe"
script := A_ScriptDir "\instantmine_toggle.py"
if !FileExist(py)
    py := "python"
Run Format('"{}" "{}"', py, script), A_ScriptDir
ExitApp
