@echo off
setlocal

set "ROOT=%~dp0"
set "APP_DIR=%ROOT%my3dgsapp"
set "JAVA_HOME=C:\Program Files\Java\jdk-22"
set "ANDROID_SDK_ROOT=D:\Android\sdk"
set "ANDROID_HOME=%ANDROID_SDK_ROOT%"
set "PATH=%JAVA_HOME%\bin;%ANDROID_SDK_ROOT%\platform-tools;%ANDROID_SDK_ROOT%\cmdline-tools\latest\bin;%PATH%"

if not exist "%APP_DIR%\package.json" (
  echo [ERROR] Cannot find my3dgsapp package.json under "%APP_DIR%".
  exit /b 1
)

if not exist "%JAVA_HOME%\bin\java.exe" (
  echo [ERROR] JDK 22 not found: "%JAVA_HOME%".
  echo Install JDK 21+ or edit JAVA_HOME in run_android.bat.
  exit /b 1
)

if not exist "%ANDROID_SDK_ROOT%\platform-tools\adb.exe" (
  echo [ERROR] adb not found under "%ANDROID_SDK_ROOT%\platform-tools".
  echo Edit ANDROID_SDK_ROOT in run_android.bat.
  exit /b 1
)

cd /d "%APP_DIR%" || exit /b 1

> "android\local.properties" echo sdk.dir=D\:\\Android\\sdk

set "TARGET=%~1"
if "%TARGET%"=="" (
  for /f "skip=1 tokens=1,2" %%A in ('adb devices') do (
    if "%%B"=="device" (
      set "TARGET=%%A"
      goto :found_device
    )
  )
)

:found_device
if "%TARGET%"=="" (
  echo [ERROR] No authorized Android device found.
  echo Check USB debugging and run: "%ANDROID_SDK_ROOT%\platform-tools\adb.exe" devices
  exit /b 1
)

echo [INFO] JAVA_HOME=%JAVA_HOME%
java -version
echo [INFO] Android target=%TARGET%

call android\gradlew.bat --stop >nul 2>nul
call npm run build || exit /b 1
call npx cap sync android || exit /b 1
call npx cap run android --target %TARGET% || exit /b 1

echo [OK] Installed my3DGSAPP on Android device %TARGET%.
