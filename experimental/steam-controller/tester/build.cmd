@echo off
cd /d "%~dp0"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
"%CSC%" /nologo /warn:4 /warnaserror+ /optimize+ /target:exe /out:SteamControllerLab.exe /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll ControllerState.cs SteamMotion.cs NativeHid.cs Tester.cs Tests.cs
if errorlevel 1 exit /b %ERRORLEVEL%
SteamControllerLab.exe --self-test
if errorlevel 1 exit /b %ERRORLEVEL%
copy /y SteamControllerLab.exe LabTests.exe >nul
"%CSC%" /nologo /warn:4 /warnaserror+ /optimize+ /target:winexe /out:SteamControllerLab.exe /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll ControllerState.cs SteamMotion.cs NativeHid.cs Tester.cs Tests.cs
exit /b %ERRORLEVEL%
