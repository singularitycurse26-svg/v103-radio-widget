$ErrorActionPreference = "SilentlyContinue"
$py = "C:\Users\hawpe\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$script = "C:\Users\hawpe\CascadeProjects\desktop-radio-player\radio.py"
Start-Process -FilePath $py -ArgumentList $script -WindowStyle Hidden
