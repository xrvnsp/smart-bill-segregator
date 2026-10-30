@echo off
title Push to GitHub - Smart Bill Segregator
echo =======================================================
echo   Pushing Latest Smart Bill Segregator to GitHub...
echo   Repository: https://github.com/xrvnsp/smart-bill-segregator
echo =======================================================
echo.

git add .
git status
git commit -m "Update Smart Bill Segregator: Payment Tracker, Cashback Reconciler, EMI True Cost Calculator & WhatsApp sharing"
git branch -M main
git remote add origin https://github.com/xrvnsp/smart-bill-segregator.git 2>nul
git remote set-url origin https://github.com/xrvnsp/smart-bill-segregator.git
git push -u origin main

echo.
echo =======================================================
echo   Done! Check your repository:
echo   https://github.com/xrvnsp/smart-bill-segregator
echo =======================================================
pause
