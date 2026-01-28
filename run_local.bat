@echo off
title JLSatiro Clipper AI - LOCAL CPU MODE
echo ==================================================
echo      JLSatiro Clipper AI - VERSAO LOCAL CPU
echo ==================================================
echo.
echo [1] Checando dependencias...
echo (Isso pode demorar na primeira vez)
pip install -r requirements.txt
echo.
echo [2] Iniciando Aplicacao...
python app.py
pause
