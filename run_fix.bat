@echo off
:: Elevate to admin and run the PowerShell fix script
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\yan\WorkBuddy\2026-07-05-18-09-42\house-ai\fix_and_restart.ps1'"
