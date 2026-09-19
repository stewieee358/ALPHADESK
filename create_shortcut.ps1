$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut("$env:USERPROFILE\Desktop\ALPHADESK.lnk")
$lnk.TargetPath       = Join-Path $PSScriptRoot "mini-bb.bat"
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.Description      = "ALPHADESK Terminal"
$lnk.Save()
Write-Host "Desktop shortcut created: $env:USERPROFILE\Desktop\ALPHADESK.lnk"
