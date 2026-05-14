@echo off
title Cargando Facturador Ferreenvios...
cd /d "%~dp0"

:: 1. Iniciar Streamlit en segundo plano (miniminizado)
start /min "" streamlit run app.py --server.headless true

:: 2. Esperar 3 segundos para que el servidor cargue
timeout /t 3 /nobreak >nul

:: 3. Forzar apertura del navegador en la dirección local
start http://localhost:8501

exit