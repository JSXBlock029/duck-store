@echo off
echo 🦆 Starting Duck Store...
echo.
echo 📸 Premium Duck Picture Sales Platform
echo 💳 Credit Card Payments Powered by Stripe
echo.
echo 🔧 Checking setup...
if not exist ".env" (
    echo ❌ Environment file not found!
    echo 📋 Please run setup.py first:
    echo    python setup.py
    echo.
    pause
    exit /b 1
)

if not exist "uploads" (
    echo 📁 Creating uploads directory...
    mkdir uploads
)

echo ✅ Setup looks good!
echo.
echo 🚀 Starting Duck Store...
echo 🌐 Visit http://localhost:5000 in your browser
echo 👑 Admin panel: http://localhost:5000/admin
echo.
echo Press Ctrl+C to stop the server
echo.
python duck_store.py
pause
