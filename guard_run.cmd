@echo off
rem UTF-8 console codepage: without it Python output lands in the log as mojibake.
rem Comments here are ASCII on purpose: after chcp 65001 the cmd parser
rem mis-reads non-ASCII bytes in this file and tries to execute them.
chcp 65001 >nul

cd /d "%~dp0"

rem Alert threshold in USD. Report only when pay-as-you-go spending goes
rem above it. Default covers the legacy 1.19 debt accumulated before the
rem switch to the subscription endpoint /api/coding/v3.
if "%BP_GUARD_LIMIT%"=="" set BP_GUARD_LIMIT=1.20

echo.>> guard.log
powershell -NoProfile -Command "'===== ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')" >> guard.log
python -X utf8 quota.py >> guard.log 2>&1
python -X utf8 guard.py "" %BP_GUARD_LIMIT% >> guard.log 2>&1

if errorlevel 1 (
  powershell -NoProfile -WindowStyle Hidden -Command ^
    "Add-Type -AssemblyName System.Windows.Forms;" ^
    "$n=New-Object System.Windows.Forms.NotifyIcon;" ^
    "$n.Icon=[System.Drawing.SystemIcons]::Warning; $n.Visible=$true;" ^
    "$n.ShowBalloonTip(15000,'BytePlus overage','Spending above subscription. See guard.log',[System.Windows.Forms.ToolTipIcon]::Warning);" ^
    "Start-Sleep -Seconds 16; $n.Dispose()"
)
