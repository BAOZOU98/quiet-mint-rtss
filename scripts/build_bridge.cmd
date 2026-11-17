@echo off
setlocal
pushd "%~dp0.."
if not defined RTSS_DIR set "RTSS_DIR=C:\Program Files (x86)\RivaTuner Statistics Server"
if not defined FRAMEVIEW_SDK_DIR set "FRAMEVIEW_SDK_DIR=C:\Program Files\NVIDIA Corporation\FrameViewSDK\SDK\Public_Release"
if not defined VS_VCVARS set "VS_VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
if not exist "%VS_VCVARS%" (echo Set VS_VCVARS to your vcvarsall.bat & exit /b 1)
if not exist "%FRAMEVIEW_SDK_DIR%\FvSDK_x64.lib" (echo Install the FrameView SDK separately & exit /b 1)
if not exist build\bridge mkdir build\bridge
call "%VS_VCVARS%" x86 >nul
cl /nologo /EHsc /MT /O2 /LD src\bridge\FrameViewBridgeLauncher.cpp /Fe:build\bridge\FrameViewBridge.dll /Fo:build\bridge\launcher.obj /link /IMPLIB:build\bridge\launcher.lib
if errorlevel 1 exit /b 1
call "%VS_VCVARS%" x64 >nul
cl /nologo /EHsc /MT /O2 /DBRIDGE_EXE /I"%FRAMEVIEW_SDK_DIR%" /I"%RTSS_DIR%\SDK\Include" src\bridge\FrameViewBridge.cpp /Fe:build\bridge\FrameViewBridge64.exe /Fo:build\bridge\bridge.obj "%FRAMEVIEW_SDK_DIR%\FvSDK_x64.lib" user32.lib advapi32.lib /link /IMPLIB:build\bridge\bridge.lib
set "build_exit=%errorlevel%"
popd
exit /b %build_exit%
