#!/usr/bin/env python3
"""
Duck Picture Store
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///duck_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db = SQLAlchemy(app)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
    featured_pictures = DuckPicture.query.filter_by(is_active=True).limit(6).all()
    categories = db.session.query(DuckPicture.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('index.html', 
                         pictures=featured_pictures, 
                         categories=categories)

@app.route('/gallery')
def gallery():
    """Gallery page with all duck pictures"""
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

@app.route('/picture/<int:picture_id>')
def picture_detail(picture_id):
    """Individual picture detail page"""
    picture = DuckPicture.query.get_or_404(picture_id)
    related_pictures = DuckPicture.query.filter(
        DuckPicture.category == picture.category,
        DuckPicture.id != picture.id,
        DuckPicture.is_active == True
    ).limit(4).all()
    
    return render_template('picture_detail.html', 
                         picture=picture, 
                         related_pictures=related_pictures)

@app.route('/cart')
def cart():
    """Shopping cart page"""
    cart_items = session.get('cart', {})
    pictures = []
    total = 0
    
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
    
    return render_template('cart.html', cart_items=pictures, total=total)

@app.route('/add_to_cart/<int:picture_id>', methods=['POST'])
def add_to_cart(picture_id):
    """Add picture to shopping cart"""
    quantity = int(request.form.get('quantity', 1))
    
    if 'cart' not in session:
        session['cart'] = {}
    
    if str(picture_id) in session['cart']:
        session['cart'][str(picture_id)] += quantity
    else:
        session['cart'][str(picture_id)] = quantity
    
    session.modified = True
    flash('Picture added to cart!', 'success')
    return redirect(url_for('picture_detail', picture_id=picture_id))

@app.route('/remove_from_cart/<int:picture_id>')
def remove_from_cart(picture_id):
    """Remove picture from shopping cart"""
    if 'cart' in session and str(picture_id) in session['cart']:
        del session['cart'][str(picture_id)]
        session.modified = True
        flash('Picture removed from cart!', 'success')
    
    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    """Checkout page"""
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
    
    cart_items = session.get('cart', {})
    pictures = []
    total = 0
    
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
    
    return render_template('checkout.html', 
                         cart_items=pictures, 
                         total=total,
                         stripe_key=STRIPE_PUBLISHABLE_KEY)

@app.route('/create_payment_intent', methods=['POST'])
def create_payment_intent():
    """Create Stripe payment intent"""
    try:
        data = request.get_json()
        amount = int(float(data['amount']) * 100)  # Convert to cents
        
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            metadata={'integration_check': 'accept_a_payment'}
        )
        
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/payment_success')
def payment_success():
    """Handle successful payment"""
    payment_intent_id = request.args.get('payment_intent')
    
    if not payment_intent_id:
        flash('Payment verification failed!', 'error')
        return redirect(url_for('index'))
    
    try:
        # Verify payment with Stripe
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if payment_intent.status == 'succeeded':
            # Create order in database
            cart_items = session.get('cart', {})
            total = 0
            
            for picture_id, quantity in cart_items.items():
                picture = DuckPicture.query.get(picture_id)
                if picture:
                    total += picture.price * quantity
            
            # Create order (in a real app, you'd create a user account system)
            order = Order(
                user_id=1,  # Default user for demo
                stripe_payment_intent_id=payment_intent_id,
                total_amount=total,
                status='completed'
            )
            db.session.add(order)
            db.session.flush()
            
            # Create order items
            for picture_id, quantity in cart_items.items():
                picture = DuckPicture.query.get(picture_id)
                if picture:
                    order_item = OrderItem(
                        order_id=order.id,
                        duck_picture_id=picture.id,
                        quantity=quantity,
                        price=picture.price
                    )
                    db.session.add(order_item)
            
            db.session.commit()
            
            # Clear cart
            session.pop('cart', None)
            
            flash('Payment successful! Your duck pictures are ready for download.', 'success')
            return redirect(url_for('order_confirmation', order_id=order.id))
        else:
            flash('Payment failed! Please try again.', 'error')
            return redirect(url_for('checkout'))
            
    except Exception as e:
        flash(f'Payment verification error: {str(e)}', 'error')
        return redirect(url_for('checkout'))

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    """Order confirmation page"""
    order = Order.query.get_or_404(order_id)
    return render_template('order_confirmation.html', order=order)

# Admin routes
@app.route('/admin')
def admin():
    """Admin dashboard"""
    total_pictures = DuckPicture.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter_by(status='completed').scalar() or 0
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin.html',
                         total_pictures=total_pictures,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders)

@app.route('/admin/pictures')
def admin_pictures():
    """Admin pictures management"""
    pictures = DuckPicture.query.order_by(DuckPicture.created_at.desc()).all()
    return render_template('admin_pictures.html', pictures=pictures)

@app.route('/admin/add_picture', methods=['GET', 'POST'])
def admin_add_picture():
    """Add new picture"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        tags = request.form.get('tags')
        
        if 'picture' not in request.files:
            flash('No picture file selected!', 'error')
            return redirect(request.url)
        
        file = request.files['picture']
        if file.filename == '':
            flash('No picture file selected!', 'error')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            picture = DuckPicture(
                title=title,
                description=description,
                filename=filename,
                price=price,
                category=category,
                tags=tags
            )
            
            db.session.add(picture)
            db.session.commit()
            
            flash('Picture added successfully!', 'success')
            return redirect(url_for('admin_pictures'))
    
    return render_template('admin_add_picture.html')

@app.route('/admin/edit_picture/<int:picture_id>', methods=['GET', 'POST'])
def admin_edit_picture(picture_id):
    """Edit existing picture"""
    picture = DuckPicture.query.get_or_404(picture_id)
    
    if request.method == 'POST':
        picture.title = request.form.get('title')
        picture.description = request.form.get('description')
        picture.price = float(request.form.get('price'))
        picture.category = request.form.get('category')
        picture.tags = request.form.get('tags')
        picture.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash('Picture updated successfully!', 'success')
        return redirect(url_for('admin_pictures'))
    
    return render_template('admin_edit_picture.html', picture=picture)

@app.route('/admin/orders')
def admin_orders():
    """Admin orders management"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

def init_db():
    """Initialize database with sample data"""
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

if __name__ == '__main__':
    init_db()
    print("🦆 Duck Store is starting up...")
    print("📸 You can now sell your duck pictures!")
    print("💳 Credit card payments powered by Stripe")
    print("🌐 Visit http://localhost:5000 to start selling")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
