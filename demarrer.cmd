@echo off
rem ---------------------------------------------------------------
rem  Bureau des Primes - apercu local
rem
rem  Le site lit son registre par le reseau et son API est en PHP :
rem  un double-clic sur index.html ne suffit pas. Ce script cherche
rem  un PHP utilisable, demarre la base locale si elle est installee,
rem  puis ouvre le navigateur.
rem
rem  Ctrl+C ou fermer cette fenetre arrete le serveur web.
rem ---------------------------------------------------------------
cd /d "%~dp0"
setlocal
set PORT=8080
set DEV=%LOCALAPPDATA%\bureau-des-primes-dev

rem --- 1. trouver PHP : d'abord celui du systeme, sinon la pile portable.
rem     On teste avec "if defined" et non "if %PHP%==" : la commande
rem     contient des guillemets, qui casseraient la comparaison.
set PHP=
where php >nul 2>&1
if not errorlevel 1 set PHP=php
if not defined PHP if exist "%DEV%\php\php.exe" set PHP="%DEV%\php\php.exe" -c "%DEV%\php\php.ini"
if not defined PHP goto :statique

rem --- 2. la base locale, si la pile portable est installee
if not exist "%DEV%\mariadb\bin\mariadbd.exe" goto :web
netstat -an | findstr /c:"127.0.0.1:3307" >nul
if not errorlevel 1 goto :web
echo Demarrage de la base locale sur le port 3307...
start "Bureau des Primes - base" /min "%DEV%\mariadb\bin\mariadbd.exe" --datadir="%DEV%\data" --port=3307 --bind-address=127.0.0.1 --skip-name-resolve
rem laisser au serveur le temps d'ouvrir son port
ping -n 5 127.0.0.1 >nul

:web
echo.
echo   Bureau des Primes  -  http://localhost:%PORT%/
echo   API PHP active. Ctrl+C pour arreter.
echo.
start "" http://localhost:%PORT%/
%PHP% -S 127.0.0.1:%PORT% -t .
goto :eof

:statique
echo.
echo   PHP est introuvable : le site demarre en mode statique.
echo   Le jeu fonctionne, mais la connexion Discord, le classement
echo   et l'historique resteront masques (voir README.md).
echo.
where python >nul 2>&1
if errorlevel 1 (
  echo   Python non plus n'est pas installe. Rien a lancer.
  pause
  exit /b 1
)
echo   Bureau des Primes  -  http://localhost:%PORT%/
start "" http://localhost:%PORT%/
python -m http.server %PORT% --bind 127.0.0.1
