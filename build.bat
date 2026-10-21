@echo off
rem Builds Conduit Launcher into dist\Conduit Launcher (needs Python 3 with the packages in requirements.txt).
rem The release zip is that folder: the launcher itself, nothing of the game or the emulator.
setlocal
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --onedir --name "Conduit Launcher" ^
  --icon "%~dp0src\app.ico" --add-data "%~dp0src\locales;locales" --add-data "%~dp0src\app.ico;." ^
  --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" "%~dp0src\launcher.py" || exit /b 1
set "OUT=%~dp0dist\Conduit Launcher"
copy /y "%~dp0baixar-emulador.bat" "%OUT%\" >nul
copy /y "%~dp0LICENSE" "%OUT%\LICENSE.txt" >nul
copy /y "%~dp0CREDITS.md" "%OUT%\CREDITS.md" >nul
copy /y "%~dp0docs\LEIA-ME.txt" "%OUT%\LEIA-ME.txt" >nul
copy /y "%~dp0docs\THIRD-PARTY.txt" "%OUT%\THIRD-PARTY.txt" >nul
if not exist "%OUT%\mods" mkdir "%OUT%\mods"
echo Pronto: %OUT%
exit /b 0
