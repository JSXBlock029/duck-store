# 🚀 Deploy Duck Store to Vercel

This guide will help you deploy your duck store to Vercel so you have a real website that anyone can visit!

## 📋 Prerequisites

1. **GitHub Account** (free)
2. **Vercel Account** (free)
3. **Your duck store files** (already in this folder)

## 🔧 Step 1: Prepare Your Files

Your files are already ready for deployment! The key files are:
- `vercel_app.py` - Main application for Vercel
- `vercel.json` - Vercel configuration
- `requirements.txt` - Python dependencies
- `templates/` - HTML templates

## 🌐 Step 2: Create GitHub Repository

1. Go to [github.com](https://github.com) and sign in
2. Click "New repository"
3. Name it: `duck-store`
4. Make it **Public** (required for free Vercel)
5. Click "Create repository"

## 📤 Step 3: Upload Files to GitHub

1. **Download GitHub Desktop** from [desktop.github.com](https://desktop.github.com)
2. **Clone** your new repository
3. **Copy all files** from this DuckStore folder to the cloned repository
4. **Commit and push** the changes

**Alternative (Command Line):**
```bash
git init
git add .
git commit -m "Initial duck store commit"
git branch -M main
git remote add origin https://github.com/lowriskbtc/duck-store.git
git push -u origin main
```

## 🚀 Step 4: Deploy to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "New Project"
3. **Import** your `duck-store` repository
4. **Framework Preset**: Select "Other"
5. **Root Directory**: Leave as `./`
6. **Build Command**: Leave empty
7. **Output Directory**: Leave empty
8. **Install Command**: `pip install -r requirements.txt`
9. Click "Deploy"

## ⚙️ Step 5: Configure Environment Variables

After deployment, go to your project settings in Vercel:

1. **Environment Variables** tab
2. Add these variables:
   ```
   SECRET_KEY=your_secret_key_here
   STRIPE_SECRET_KEY=your_stripe_secret_key
   STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
   ```

## 🎉 Step 6: Your Website is Live!

Your duck store will be available at:
- **Production URL**: `https://your-project-name.vercel.app`
- **Custom Domain**: You can add your own domain later

## 🔄 Step 7: Update Your Store

Every time you push changes to GitHub:
1. Vercel automatically detects changes
2. Builds and deploys your updates
3. Your website stays current

## 💡 Pro Tips

### **For Better Performance:**
- Use **PostgreSQL** instead of SQLite (Vercel has add-ons)
- Store images on **Cloudinary** or **AWS S3**
- Use **Vercel Edge Functions** for faster responses

### **Custom Domain:**
1. Buy a domain (GoDaddy, Namecheap, etc.)
2. Add it in Vercel project settings
3. Update DNS records as instructed

### **Database Options:**
- **Free**: Keep using SQLite (resets on each deployment)
- **Paid**: Use Vercel Postgres or external database
- **Best**: Use external database for persistent data

## 🆘 Troubleshooting

### **Build Errors:**
- Check `requirements.txt` has all dependencies
- Ensure Python version compatibility
- Check for syntax errors in your code

### **Runtime Errors:**
- Check environment variables are set
- Verify database connection
- Check Vercel function logs

### **Common Issues:**
- **File uploads**: Vercel uses `/tmp` directory (temporary)
- **Database**: SQLite resets on each deployment
- **Sessions**: May not persist between requests

## 🎯 Next Steps

1. **Deploy your store** following this guide
2. **Add your duck pictures** (you'll need to re-upload after each deployment)
3. **Set up Stripe** for real payments
4. **Customize** your store design
5. **Share your website** with customers!

## 📞 Need Help?

- **Vercel Docs**: [vercel.com/docs](https://vercel.com/docs)
- **GitHub Help**: [help.github.com](https://help.github.com)
- **Flask Docs**: [flask.palletsprojects.com](https://flask.palletsprojects.com)

---

**Happy Deploying! 🦆🚀🌐**
