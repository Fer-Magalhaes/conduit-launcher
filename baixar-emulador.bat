@echo off
rem Baixa o shadPS4 que o Conduit Launcher usa para a pasta emu, sem abrir o launcher.
rem Faz o mesmo que o botao "Baixar / atualizar emulador": pega o ultimo release do build "Infamous"
rem (GPL-2.0, https://github.com/rayhlancaner-png/shadPS4-Infamous-FixBuild).
rem Downloads the shadPS4 build Conduit Launcher uses into the emu folder, without opening the launcher.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$h = @{ 'User-Agent' = 'Conduit-Launcher' };" ^
  "$r = Invoke-RestMethod 'https://api.github.com/repos/rayhlancaner-png/shadPS4-Infamous-FixBuild/releases/latest' -Headers $h;" ^
  "$a = $r.assets | Where-Object name -eq 'shadPS4.exe';" ^
  "if (-not $a) { throw 'shadPS4.exe nao encontrado no release ' + $r.tag_name };" ^
  "New-Item -ItemType Directory -Force 'emu\user' | Out-Null;" ^
  "Write-Host ('Baixando shadPS4 ' + $r.tag_name + ' (' + [math]::Round($a.size / 1MB) + ' MB)...');" ^
  "$ProgressPreference = 'SilentlyContinue';" ^
  "Invoke-WebRequest $a.browser_download_url -OutFile 'emu\shadPS4.exe.part' -Headers $h -UseBasicParsing;" ^
  "if ((Get-Item 'emu\shadPS4.exe.part').Length -ne $a.size) { throw 'Download incompleto' };" ^
  "Move-Item -Force 'emu\shadPS4.exe.part' 'emu\shadPS4.exe';" ^
  "Set-Content 'emu\version.txt' $r.tag_name;" ^
  "Write-Host 'Pronto: emu\shadPS4.exe'"
if errorlevel 1 (
  echo Nao deu para baixar. Verifique a internet e tente de novo.
)
pause
