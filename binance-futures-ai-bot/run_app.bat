@echo off
title Vibe-Trading AI | Binance Futures Desktop Terminal
chcp 65001 > nul
echo ========================================================
echo   ⚡ VIBE-TRADING AI - BINANCE FUTURES DESKTOP BOT
echo ========================================================
echo Đang khởi động hệ thống...
cd /d "%~dp0"
python main.py
pause
