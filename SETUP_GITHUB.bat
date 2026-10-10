@echo off
title 🚀 Setup GitHub Repository for lowriskbtc
color 0A

echo.
echo ████████████████████████████████████████████████████████████████
echo ██  🚀 GITHUB SETUP FOR LOWRISKBTC - Deploy Your Duck Store! 🚀  ██
echo ████████████████████████████████████████████████████████████████
echo.
echo 👤 GitHub Username: lowriskbtc
echo 🦆 Project: Duck Store
echo 🌐 Goal: Deploy to Vercel for real website
echo.
echo ================================================================
echo.

echo 📋 STEP-BY-STEP SETUP FOR lowriskbtc:
echo.

echo 🌐 STEP 1: Create GitHub Repository
echo    Go to: https://github.com/new
echo    Repository name: duck-store
echo    Make it: PUBLIC (required for free Vercel)
echo    Click: "Create repository"
echo.

echo 📤 STEP 2: Upload Files (Choose ONE method)
echo.
echo    METHOD A - GitHub Desktop (Recommended):
echo    1. Download: https://desktop.github.com
echo    2. Clone your duck-store repository
echo    3. Copy ALL files from this DuckStore folder
echo    4. Commit and push changes
echo.

echo    METHOD B - Command Line:
echo    1. Open Command Prompt in this folder
echo    2. Run these commands:
echo       git init
echo       git add .
echo       git commit -m "Initial duck store commit"
echo       git branch -M main
echo       git remote add origin https://github.com/lowriskbtc/duck-store.git
echo       git push -u origin main
echo.

echo 🚀 STEP 3: Deploy to Vercel
echo    1. Go to: https://vercel.com
echo    2. Sign in with GitHub
echo    3. Click "New Project"
echo    4. Import your duck-store repository
echo    5. Framework: Select "Other"
echo    6. Install Command: pip install -r requirements.txt
echo    7. Click "Deploy"
echo.

echo ⚙️ STEP 4: Environment Variables
echo    After deployment, add these in Vercel:
echo    SECRET_KEY=your_secret_key_here
echo    STRIPE_SECRET_KEY=your_stripe_secret_key
echo    STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
echo.

echo 🎉 STEP 5: Your Website is Live!
echo    URL: https://duck-store-lowriskbtc.vercel.app
echo    (or similar Vercel URL)
echo.

echo ================================================================
echo.

echo 🔗 YOUR LINKS:
echo    📁 GitHub: https://github.com/lowriskbtc
echo    🚀 Vercel: https://vercel.com
echo    📖 Full Guide: DEPLOY_TO_VERCEL.md
echo.

echo 💡 PRO TIPS:
echo    - Make repository PUBLIC (required for free Vercel)
echo    - Use GitHub Desktop for easy file management
echo    - Vercel auto-deploys when you push to GitHub
echo    - You can add custom domain later
echo.

echo 🎯 READY TO START?
echo    1. Open DEPLOY_TO_VERCEL.md for detailed instructions
echo    2. Create your GitHub repository
echo    3. Upload these files
echo    4. Deploy to Vercel
echo    5. Share your duck store website!
echo.

echo 🦆 Your duck pictures are about to go global! 🚀🌐
echo.

pause
