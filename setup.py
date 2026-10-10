#!/usr/bin/env python3
"""
Setup script for Duck Store
This script helps you set up the duck picture selling platform
"""

import os
import sys
import subprocess
import secrets

def print_banner():
    """Print the setup banner"""
    print("🦆" * 50)
    print("🦆           DUCK STORE SETUP           🦆")
    print("🦆     Premium Duck Picture Sales      🦆")
    print("🦆" * 50)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required!")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version.split()[0]}")

def install_requirements():
    """Install required packages"""
    print("\n📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Packages installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install packages. Please run manually:")
        print("   pip install -r requirements.txt")
        return False
    return True

def create_env_file():
    """Create .env file with required environment variables"""
    env_file = ".env"
    
    if os.path.exists(env_file):
        print(f"✅ {env_file} already exists")
        return True
    
    print(f"\n🔧 Creating {env_file} file...")
    
    # Generate a secure secret key
    secret_key = secrets.token_hex(32)
    
    env_content = f"""# Duck Store Environment Variables
# Replace these with your actual values

# Flask secret key (auto-generated)
SECRET_KEY={secret_key}

# Stripe API Keys (get from https://dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_test_your_test_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_publishable_key_here

# Database settings
DATABASE_URL=sqlite:///duck_store.db

# File upload settings
MAX_FILE_SIZE=16777216
UPLOAD_FOLDER=uploads
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"✅ {env_file} created successfully!")
        print("⚠️  Please update the Stripe API keys with your actual values")
        return True
    except Exception as e:
        print(f"❌ Failed to create {env_file}: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'static', 'templates']
    
    print("\n📁 Creating necessary directories...")
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created {directory}/ directory")
        else:
            print(f"✅ {directory}/ directory already exists")

def create_sample_pictures():
    """Create sample picture placeholders"""
    uploads_dir = "uploads"
    
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    # Create sample picture files (you can replace these with actual duck pictures)
    sample_files = [
        "sample_mallard.jpg",
        "sample_duckling.jpg", 
        "sample_wood_duck.jpg"
    ]
    
    print("\n🖼️  Creating sample picture placeholders...")
    for filename in sample_files:
        filepath = os.path.join(uploads_dir, filename)
        if not os.path.exists(filepath):
            # Create a simple text file as placeholder
            with open(filepath, 'w') as f:
                f.write(f"This is a placeholder for {filename}\n")
                f.write("Replace this file with an actual duck picture!\n")
            print(f"✅ Created placeholder: {filename}")
        else:
            print(f"✅ {filename} already exists")

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE! Here's what to do next:")
    print("="*60)
    print()
    print("1. 🔑 Get your Stripe API keys:")
    print("   - Go to https://dashboard.stripe.com/apikeys")
    print("   - Copy your publishable and secret keys")
    print("   - Update the .env file with your keys")
    print()
    print("2. 🖼️  Add your duck pictures:")
    print("   - Place your duck picture files in the uploads/ folder")
    print("   - Supported formats: JPG, PNG, GIF")
    print("   - Maximum file size: 16MB")
    print()
    print("3. 🚀 Start the application:")
    print("   python duck_store.py")
    print()
    print("4. 🌐 Open your browser:")
    print("   http://localhost:5000")
    print()
    print("5. 👑 Access admin panel:")
    print("   http://localhost:5000/admin")
    print()
    print("📚 For help and documentation:")
    print("   - Check the README.md file")
    print("   - Visit Flask documentation: https://flask.palletsprojects.com/")
    print("   - Visit Stripe documentation: https://stripe.com/docs")
    print()
    print("🦆 Happy duck picture selling!")

def main():
    """Main setup function"""
    print_banner()
    
    print("🔍 Checking system requirements...")
    check_python_version()
    
    print("\n📋 Starting setup process...")
    
    # Install requirements
    if not install_requirements():
        print("\n❌ Setup failed during package installation")
        return
    
    # Create environment file
    if not create_env_file():
        print("\n❌ Setup failed during environment file creation")
        return
    
    # Create directories
    create_directories()
    
    # Create sample pictures
    create_sample_pictures()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
