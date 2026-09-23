@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
set "PKG=%USERPROFILE%\controller-forwarding\wdk-packages"
set "WDK=%PKG%\microsoft.windows.wdk.x64\c"
set "SDK=%PKG%\microsoft.windows.sdk.cpp\c"
set "LIB=%WDK%\Lib\wdf\umdf\x64\2.15;%WDK%\Lib\10.0.26100.0\um\x64;%PKG%\microsoft.windows.sdk.cpp.x64\c\um\x64;%LIB%"
cl /nologo /std:c++20 /W4 /WX /MT /EHsc /DUMDF_VERSION_MAJOR=2 /DUMDF_VERSION_MINOR=15 /DUNICODE /D_UNICODE /external:W0 /external:I"%WDK%\Include\wdf\umdf\2.15" /external:I"%SDK%\Include\10.0.26100.0\um" /external:I"%SDK%\Include\10.0.26100.0\shared" /LD driver.cpp /Fe:MoonmachineSteamHid.dll /link WdfDriverStubUm.lib VhfUm.lib ntdll.lib
if errorlevel 1 exit /b %ERRORLEVEL%
cl /nologo /std:c++20 /W4 /WX /MT /EHsc /DUNICODE /D_UNICODE broker.cpp /Fe:broker.exe /link setupapi.lib newdev.lib
if errorlevel 1 exit /b %ERRORLEVEL%
cl /nologo /std:c++20 /W4 /WX /MT /EHsc test_protocol.cpp /Fe:test_protocol.exe
if errorlevel 1 exit /b %ERRORLEVEL%
test_protocol.exe
if errorlevel 1 exit /b %ERRORLEVEL%
cl /nologo /std:c++20 /W4 /WX /MT /EHsc probe.cpp /Fe:probe.exe /link hid.lib setupapi.lib
exit /b %ERRORLEVEL%
