# V-103 Atlanta Desktop Radio Widget

A lightweight always-on-top desktop music widget that plays V-103 Atlanta radio 24/7 nonstop.

## Features
- Auto-plays V-103 Atlanta on launch
- Play/Pause button
- Animated equalizer bars
- Drag anywhere to reposition
- Always-on-top floating widget
- Auto-reconnects if stream drops
- Auto-starts on Windows login

## Install

### 1. Install VLC (required for audio)
```
winget install VideoLAN.VLC
```

### 2. Install Python 3.11+ (if not already installed)
```
winget install Astral.Python.3.11
```

### 3. Run the widget
```
python radio.py
```

### 4. Auto-start on boot (Windows)
Copy the shortcut to your Startup folder:
```powershell
$startup = [Environment]::GetFolderPath("Startup")
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut("$startup\V-103 Radio.lnk")
$sc.TargetPath = "python"
$sc.Arguments = "C:\path\to\desktop-radio-player\radio.py"
$sc.WorkingDirectory = "C:\path\to\desktop-radio-player"
$sc.IconLocation = "C:\Program Files\VideoLAN\VLC\vlc.exe,0"
$sc.Save()
```

## No pip packages needed
This widget uses only Python's built-in `tkinter` library for the UI and VLC (system install) for audio playback. No `pip install` required.

## Stream
V-103 Atlanta (WVEE-FM 103.3): `https://live.amperwave.net/direct/audacy-wveefmaac-imc`

## Files
- `radio.py` — Main widget application
- `start-radio.ps1` — PowerShell launcher script
- `requirements.txt` — No external pip dependencies

## License
MIT
