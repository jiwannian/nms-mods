$ErrorActionPreference = "Stop"

$ahk = "D:\tool\AutoHotkey\AutoHotkey64.exe"
$script = Join-Path $PSScriptRoot "CreativeFlyToggle.ahk"

if (-not (Test-Path -LiteralPath $ahk)) {
    throw "未找到 AutoHotkey v2：$ahk"
}
if (-not (Test-Path -LiteralPath $script)) {
    throw "未找到飞行脚本：$script"
}

# 以管理员权限启动，确保 NMS 能接收模拟按键。
Start-Process -FilePath $ahk -ArgumentList @("`"$script`"") -Verb RunAs
