<p align="center"><img src="logo.svg" width="128" alt="JhFastYT"></p>

# JhFastYT

Aplicación de escritorio para descargar videos y audios de YouTube (mp4, mkv, webm, mp3, m4a, opus, flac, wav), con lista de pendientes, historial de descargados y vista previa. Usa [yt-dlp](https://github.com/yt-dlp/yt-dlp).

Requisitos: Windows 10 u 11 y conexión a internet.

## Instalar

**Con un comando** (PowerShell):

```powershell
irm https://raw.githubusercontent.com/21harley/JhFastYT/main/install/install.ps1 | iex
```

**Con el instalador:** descarga `JhFastYT-Setup.exe` desde [Releases](../../releases/latest) y ábrelo.

Ambos instalan en `%LOCALAPPDATA%\JhFastYT` sin pedir administrador, descargan `ffmpeg` y `deno`, y crean un acceso en el menú Inicio.

## Actualizar

Vuelve a ejecutar el comando de instalación o el instalador. Tus datos no se tocan.

## Desinstalar

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/21harley/JhFastYT/main/install/install.ps1))) -Uninstall
```

Quita la app y las herramientas. Tu lista y tu historial siguen en `%LOCALAPPDATA%\JhFastYT\data`; borra esa carpeta si no los quieres. Los videos descargados están en `Descargas\JhFastYT` y no se borran.

## Desarrollo

```
run.bat            crea .venv, instala requirements.txt y abre src\app.py
manifest.json      componentes que baja el instalador (app, ffmpeg, deno)
install\           install.ps1 (comando) y setup.iss (instalador .exe, Inno Setup)
.github\workflows  construye el .exe y publica el release al crear un tag v*
```

Publicar una versión: `git tag v0.1.0 && git push --tags`. El workflow compila con PyInstaller y adjunta `JhFastYT-win-x64.zip` y `JhFastYT-Setup.exe`.

Si YouTube cambia algo y la descarga falla, actualiza `yt-dlp` (`pip install -U yt-dlp`) y publica un release nuevo: `yt-dlp` va dentro del `.exe`.

Si la app falla al abrir, el error queda en `data\error.log`.

Si YouTube responde "Sign in to confirm you're not a bot", elige en el menú de la app el navegador donde tienes sesión de YouTube iniciada (Firefox suele ser el que mejor funciona; Chrome y Edge pueden fallar mientras están abiertos).
