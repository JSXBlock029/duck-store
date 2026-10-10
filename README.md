# 🦆 Duck Store - Premium Duck Picture Sales

A beautiful and secure e-commerce platform for selling duck pictures with credit card payments powered by Stripe.

## ✨ Features

- **🖼️ Beautiful Gallery**: Responsive grid layout showcasing your duck pictures
- **💳 Secure Payments**: Stripe-powered credit card processing with PCI compliance
- **🛒 Shopping Cart**: Easy-to-use cart system with session management
- **🔍 Search & Filter**: Find pictures by category, tags, or search terms
- **📱 Mobile Responsive**: Works perfectly on all devices
- **👑 Admin Panel**: Easy management of pictures, orders, and sales
- **📊 Sales Analytics**: Track your revenue and order history
- **🔒 Security**: Environment-based configuration, no hardcoded secrets

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.7 or higher
- Stripe account (for payment processing)
- Duck pictures to sell

### 2. Installation

```bash
# Clone or download the project
cd newblofin

# Run the setup script
python setup.py

# Or install manually
pip install -r requirements.txt
```

### 3. Configuration

1. **Get Stripe API Keys**:
   - Sign up at [stripe.com](https://stripe.com)
   - Go to [API Keys](https://dashboard.stripe.com/apikeys)
   - Copy your publishable and secret keys

2. **Update Environment Variables**:
   - Edit the `.env` file
   - Replace the placeholder Stripe keys with your actual keys

### 4. Add Your Duck Pictures

Place your duck picture files in the `uploads/` folder:
- Supported formats: JPG, PNG, GIF
- Maximum file size: 16MB
- Recommended resolution: 1920x1080 or higher

### 5. Start the Application

```bash
python duck_store.py
```

Visit [http://localhost:5000](http://localhost:5000) in your browser!

## 🏗️ Project Structure

```
newblofin/
├── duck_store.py          # Main Flask application
├── setup.py               # Setup and installation script
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (created by setup)
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Home page
│   ├── gallery.html      # Picture gallery
│   ├── checkout.html     # Payment checkout
│   └── ...               # Other templates
├── uploads/              # Picture uploads directory
├── static/               # Static files (CSS, JS, images)
└── duck_store.db         # SQLite database (created automatically)
```

## 💳 Payment Setup

### Stripe Configuration

1. **Test Mode** (Recommended for development):
   - Use test API keys starting with `pk_test_` and `sk_test_`
   - Test with Stripe's test card numbers:
     - Success: `4242 4242 4242 4242`
     - Decline: `4000 0000 0000 0002`

2. **Live Mode** (For production):
   - Switch to live API keys starting with `pk_live_` and `sk_live_`
   - Update your `.env` file
   - Ensure HTTPS is enabled

### Security Features

- ✅ No hardcoded API keys
- ✅ Environment-based configuration
- ✅ Stripe Elements for secure card input
- ✅ PCI compliance through Stripe
- ✅ CSRF protection
- ✅ Secure session management

## 🎨 Customization

### Styling

The application uses Bootstrap 5 with custom CSS variables:
- Primary color: `#ff6b35` (Orange)
- Secondary color: `#f7931e` (Dark Orange)
- Accent color: `#ffd23f` (Yellow)

### Adding New Features

1. **New Routes**: Add to `duck_store.py`
2. **New Templates**: Create in `templates/` folder
3. **Database Models**: Extend the existing models
4. **Payment Methods**: Integrate additional Stripe payment methods

## 📱 Admin Panel

Access the admin panel at `/admin` to:
- 📸 Manage duck pictures (add, edit, delete)
- 📊 View sales analytics and revenue
- 📋 Process orders and track customers
- ⚙️ Configure store settings

## 🔧 Development

### Running in Development Mode

```bash
# Enable debug mode
export FLASK_ENV=development
python duck_store.py
```

### Database Management

```python
# Access the database
from duck_store import db, app

with app.app_context():
    # Create tables
    db.create_all()
    
    # Add sample data
    # ... your code here
```

### Testing

The application includes sample data for testing:
- Sample duck pictures
- Test database
- Stripe test mode integration

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**:
   - Use production Stripe keys
   - Set `FLASK_ENV=production`
   - Configure proper `SECRET_KEY`

2. **Web Server**:
   - Use Gunicorn or uWSGI
   - Configure Nginx as reverse proxy
   - Enable HTTPS with SSL certificates

3. **Database**:
   - Consider PostgreSQL for production
   - Set up database backups
   - Configure connection pooling

### Example Gunicorn Command

```bash
gunicorn -w 4 -b 0.0.0.0:8000 duck_store:app
```

## 🐛 Troubleshooting

### Common Issues

1. **Stripe Keys Not Working**:
   - Verify API keys are correct
   - Check if you're using test vs live keys
   - Ensure keys are properly set in `.env`

2. **Pictures Not Displaying**:
   - Check file permissions in `uploads/` folder
   - Verify file paths in database
   - Check browser console for errors

3. **Payment Failures**:
   - Use Stripe test cards for development
   - Check Stripe dashboard for error logs
   - Verify webhook endpoints (if configured)

### Getting Help

- Check the Flask documentation: [flask.palletsprojects.com](https://flask.palletsprojects.com/)
- Stripe documentation: [stripe.com/docs](https://stripe.com/docs)
- Create an issue in the project repository

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🦆 About Duck Store

Duck Store was created to provide photographers and duck enthusiasts with a simple, secure, and beautiful way to sell their duck pictures online. Whether you're a professional wildlife photographer or just love taking pictures of ducks, this platform makes it easy to turn your passion into profit.

---

**Happy Duck Picture Selling! 🦆📸💰** 

## Admin access

The admin area requires HTTP Basic auth using the `ADMIN_PASSWORD` environment variable (any username). If it is not set, the admin area is disabled. See `.env.example` for all settings.
