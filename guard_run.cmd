@echo off
cd /d "%~dp0"
echo. >> guard.log
powershell -NoProfile -Command "'===== ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')" >> guard.log
python -X utf8 quota.py >> guard.log 2>&1
python -X utf8 guard.py >> guard.log 2>&1
if errorlevel 1 (
  powershell -NoProfile -WindowStyle Hidden -Command ^
    "Add-Type -AssemblyName System.Windows.Forms;" ^
    "$n=New-Object System.Windows.Forms.NotifyIcon;" ^
    "$n.Icon=[System.Drawing.SystemIcons]::Warning; $n.Visible=$true;" ^
    "$n.ShowBalloonTip(15000,'BytePlus overage','Расход сверх подписки. См. projects\byteplus\guard.log',[System.Windows.Forms.ToolTipIcon]::Warning);" ^
    "Start-Sleep -Seconds 16; $n.Dispose()"
)
