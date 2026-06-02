@echo off
uvicorn app.main:app --reload --lifespan on
pause