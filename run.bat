@echo off
chcp 65001 >nul
title Quy trinh Video - YouTube Voice SRT Canva
cd /d %~dp0
rem --- Quan trong: ep moi thu tai ve nam trong thu muc tool (o nao chua tool thi nam o do) ---
set HF_HOME=%~dp0Data\hf
set HUGGINGFACE_HUB_CACHE=%~dp0Data\hf\hub
set TORCH_HOME=%~dp0Data\torch
set TTS_HOME=%~dp0Data\tts
set PIP_CACHE_DIR=%~dp0Data\pip-cache
if not exist Data mkdir Data
rem --- Tao moi truong Python rieng ngay trong thu muc tool, khong dung chung o C ---
if not exist .venv\Scripts\python.exe (
  echo Lan dau: dang tao moi truong Python rieng trong thu muc tool...
  python -m venv .venv
)
echo Dang cai / kiem tra thu vien... Lan dau hoi lau mot chut.
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
.venv\Scripts\python.exe app.py
pause
