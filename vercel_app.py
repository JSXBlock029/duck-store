#!/usr/bin/env python3
"""
Duck Store - Vercel Deployment Version
A web application to sell duck pictures with credit card payments
"""

import os
import json
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import stripe

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))


# --- Admin protection -----------------------------------------------------------
# Every /admin route requires HTTP Basic auth with the ADMIN_PASSWORD environment
# variable (any username). If ADMIN_PASSWORD is not set, the admin area is disabled.
import hmac as _hmac
from flask import Response as _Response


@app.before_request
def _protect_admin():
    if not request.path.startswith('/admin'):
        return None
    expected = os.getenv('ADMIN_PASSWORD', '')
    if not expected:
        return _Response('Admin is disabled. Set ADMIN_PASSWORD to enable it.', 403)
    auth = request.authorization
    if auth and auth.password and _hmac.compare_digest(auth.password.encode(), expected.encode()):
        return None
    return _Response('Admin login required', 401, {'WWW-Authenticate': 'Basic realm="admin"'})

# Vercel deployment configuration
if os.getenv('VERCEL_ENV'):
    # Production - use environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///duck_store.db')
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'  # Vercel uses /tmp for file storage
else:
    # Local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///duck_store.db'
    app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db = SQLAlchemy(app)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

class DuckPicture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order_items = db.relationship('OrderItem', backref='duck_picture', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_payment_intent_id = db.Column(db.String(255))
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    duck_picture_id = db.Column(db.Integer, db.ForeignKey('duck_picture.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)

# Routes
@app.route('/')
def index():
    """Home page with featured duck pictures"""
    try:
        featured_pictures = DuckPicture.query.filter_by(is_active=True).limit(6).all()
        categories = db.session.query(DuckPicture.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]
    except:
        featured_pictures = []
        categories = []
    
    return render_template('index.html', 
                         pictures=featured_pictures, 
                         categories=categories)

@app.route('/gallery')
def gallery():
    """Gallery page with all duck pictures"""
    try:
        page = request.args.get('page', 1, type=int)
        category = request.args.get('category', '')
        search = request.args.get('search', '')
        
        query = DuckPicture.query.filter_by(is_active=True)
        
        if category:
            query = query.filter_by(category=category)
        
        if search:
            query = query.filter(DuckPicture.title.contains(search) | 
                                DuckPicture.description.contains(search) |
                                DuckPicture.tags.contains(search))
        
        pictures = query.paginate(page=page, per_page=12, error_out=False)
        
        categories = db.session.query(DuckPicture.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]
        
        return render_template('gallery.html', 
                             pictures=pictures, 
                             categories=categories,
                             current_category=category,
                             search=search)
    except Exception as e:
        return render_template('gallery.html', 
                             pictures=None, 
                             categories=[],
                             current_category='',
                             search='')

@app.route('/cart')
def cart():
    """Shopping cart page"""
    cart_items = session.get('cart', {})
    pictures = []
    total = 0
    
    try:
        for picture_id, quantity in cart_items.items():
            picture = DuckPicture.query.get(picture_id)
            if picture and picture.is_active:
                pictures.append({
                    'id': picture.id,
                    'title': picture.title,
                    'filename': picture.filename,
                    'price': picture.price,
                    'quantity': quantity,
                    'subtotal': picture.price * quantity
                })
                total += picture.price * quantity
    except:
        pass
    
    return render_template('cart.html', cart_items=pictures, total=total)

@app.route('/admin')
def admin():
    """Admin dashboard"""
    try:
        total_pictures = DuckPicture.query.count()
        total_orders = Order.query.count()
        total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter_by(status='completed').scalar() or 0
        
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    except:
        total_pictures = 0
        total_orders = 0
        total_revenue = 0
        recent_orders = []
    
    return render_template('admin.html',
                         total_pictures=total_pictures,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/health')
def health_check():
    """Health check endpoint for Vercel"""
    return jsonify({"status": "healthy", "message": "Duck Store is running!"})

# Initialize database
def init_db():
    """Initialize database with sample data"""
    try:
        with app.app_context():
            db.create_all()
            
            # Check if we need to add sample data
            if DuckPicture.query.count() == 0:
                sample_pictures = [
                    {
                        'title': 'Majestic Mallard',
                        'description': 'A beautiful male mallard duck in full breeding plumage',
                        'filename': 'sample_mallard.jpg',
                        'price': 9.99,
                        'category': 'Wild Ducks',
                        'tags': 'mallard, wild, breeding, colorful'
                    },
                    {
                        'title': 'Cute Duckling',
                        'description': 'Adorable baby duck with fluffy yellow feathers',
                        'filename': 'sample_duckling.jpg',
                        'price': 7.99,
                        'category': 'Baby Ducks',
                        'tags': 'duckling, baby, cute, fluffy'
                    },
                    {
                        'title': 'Wood Duck Beauty',
                        'description': 'Stunning wood duck with iridescent feathers',
                        'filename': 'sample_wood_duck.jpg',
                        'price': 12.99,
                        'category': 'Wild Ducks',
                        'tags': 'wood duck, iridescent, colorful, rare'
                    }
                ]
                
                for pic_data in sample_pictures:
                    picture = DuckPicture(**pic_data)
                    db.session.add(picture)
                
                db.session.commit()
                print("Sample duck pictures added to database!")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize database when app starts
if __name__ == '__main__':
    init_db()
    app.run(debug=os.getenv('FLASK_DEBUG') == '1', host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '5000')))

# For Vercel deployment
app.debug = False
init_db()
