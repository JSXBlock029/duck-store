@echo off
title 🦆 Duck Store - Premium Duck Picture Sales
color 0A

echo.
echo ████████████████████████████████████████████████████████████████
echo ██  🦆 DUCK STORE - Premium Duck Picture Sales Platform  🦆  ██
echo ████████████████████████████████████████████████████████████████
echo.
echo 📸 Sell your duck pictures with credit card payments!
echo 💳 Powered by Stripe for secure transactions
echo 🌐 Beautiful web interface for your customers
echo.
echo ================================================================
echo.

echo 🔧 First time setup? Let's get you started...
echo.

:setup_choice
set /p choice="Do you want to run the setup script? (y/n): "
if /i "%choice%"=="y" goto setup
if /i "%choice%"=="n" goto start
echo Please enter y or n
goto setup_choice

:setup
echo.
echo 📋 Running setup script...
python setup.py
echo.
echo ✅ Setup complete! 
echo.
pause
goto start

:start
echo.
echo 🚀 Starting Duck Store...
echo.
echo 🌐 Your store will open at: http://localhost:5000
echo 👑 Admin panel: http://localhost:5000/admin
echo.
echo 💡 Tips:
echo    - Add your duck pictures to the uploads/ folder
echo    - Use the admin panel to manage your store
echo    - Get Stripe API keys from https://dashboard.stripe.com
echo.
echo Press Ctrl+C to stop the server when you're done
echo.
echo ================================================================
echo.

python duck_store.py

echo.
echo 🦆 Thanks for using Duck Store!
pause
