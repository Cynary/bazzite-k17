@echo off
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "PROBE_VS=%%i"
if not defined PROBE_VS exit /b 1
call "%PROBE_VS%\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /std:c++20 /EHsc /W4 /Ilibvirtualgamepad\include probe.cpp libvirtualgamepad\client\client.cpp /Fe:probe.exe /link setupapi.lib hid.lib windowsapp.lib user32.lib xinput.lib
exit /b %errorlevel%
