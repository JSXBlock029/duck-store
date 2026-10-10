@echo off
title 🚀 Auto-Setup Git Repository for lowriskbtc
color 0E

echo.
echo ████████████████████████████████████████████████████████████████
echo ██  🚀 AUTO-SETUP GIT REPOSITORY FOR LOWRISKBTC 🚀  ██
echo ████████████████████████████████████████████████████████████████
echo.
echo 👤 GitHub Username: lowriskbtc
echo 🦆 Project: Duck Store
echo 🔧 This script will set up git and prepare for push
echo.
echo ================================================================
echo.

echo ⚠️  IMPORTANT: You must create the repository on GitHub first!
echo.
echo 📋 BEFORE RUNNING THIS SCRIPT:
echo    1. Go to: https://github.com/new
echo    2. Repository name: duck-store
echo    3. Make it: PUBLIC
echo    4. Click "Create repository"
echo    5. DON'T initialize with README, .gitignore, or license
echo.

echo 🔍 Checking if git is installed...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git is not installed!
    echo 📥 Download from: https://git-scm.com/downloads
    echo.
    pause
    exit /b 1
)

echo ✅ Git is installed
echo.

echo 🔍 Checking if this is already a git repository...
if exist ".git" (
    echo ⚠️  This folder is already a git repository!
    echo.
    echo Choose an option:
    echo 1. Continue with existing git setup
    echo 2. Remove existing git and start fresh
    echo.
    set /p choice="Enter choice (1 or 2): "
    if "!choice!"=="2" (
        echo 🗑️  Removing existing git repository...
        rmdir /s /q .git
        echo ✅ Removed existing git repository
        echo.
    )
)

echo 🚀 Setting up git repository...
git init
echo ✅ Git repository initialized

echo 📝 Adding all files...
git add .
echo ✅ Files added to git

echo 💾 Creating initial commit...
git commit -m "Initial duck store commit - Ready for Vercel deployment"
echo ✅ Initial commit created

echo 🌿 Setting main branch...
git branch -M main
echo ✅ Main branch set

echo 🔗 Adding remote origin...
git remote add origin https://github.com/lowriskbtc/duck-store.git
echo ✅ Remote origin added

echo.
echo ================================================================
echo.
echo 🎯 GIT SETUP COMPLETE!
echo.
echo 📤 NEXT STEPS:
echo    1. Push to GitHub: git push -u origin main
echo    2. Go to Vercel: https://vercel.com
echo    3. Import your duck-store repository
echo    4. Deploy your website!
echo.

echo 💡 TIP: If you get authentication errors, you may need to:
echo    - Set up GitHub Personal Access Token
echo    - Or use GitHub Desktop for easier management
echo.

echo 🔗 YOUR REPOSITORY:
echo    https://github.com/lowriskbtc/duck-store
echo.

echo 🚀 Ready to push? Run: git push -u origin main
echo.

pause
