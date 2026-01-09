from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  
from flask_migrate import Migrate
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import os
from flask import jsonify, send_file
from io import BytesIO
# Add these imports at the top of your app.py
from flask import jsonify, send_file
from io import BytesIO
import csv
import json
from datetime import datetime, timedelta
from sqlalchemy import func, extract

from functools import wraps

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(16)





# Add these fields to your User/Buyer model:
# - google_id (String, unique)
# - profile_picture (String)
# - auth_method (String) - 'google' or 'email'

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shopmax.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add to your app configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-app@gmail.com'  # Your app's Gmail
app.config['MAIL_PASSWORD'] = 'your-app-password'   # Use App Password from Google
app.config['MAIL_DEFAULT_SENDER'] = 'your-app@gmail.com'

# Configure upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(200), nullable=True)
    user_type = db.Column(db.String(20), nullable=False)  # buyer, seller, admin
    delivery_address = db.Column(db.Text)
    business_name = db.Column(db.String(100))
    business_address = db.Column(db.Text)
    nin = db.Column(db.String(50))
    subscription_tier = db.Column(db.String(20), default='basic')
    subscription_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business_type = db.Column(db.String(50))
    business_description = db.Column(db.Text)
    business_phone = db.Column(db.String(20))
    business_email = db.Column(db.String(100))

    # Relationships
    products = db.relationship('Product', backref='seller', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    order_items = db.relationship('OrderItem', backref='seller', lazy=True)
    wishlists = db.relationship('Wishlist', backref='user', lazy=True)
    carts = db.relationship('Cart', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    
  

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    
    # New fields
    brand = db.Column(db.String(50), nullable=True)
    condition = db.Column(db.String(20), default='new', nullable=True)
    weight = db.Column(db.Float, nullable=True)
    dimensions = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.String(200), nullable=True)
    
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    wishlists = db.relationship('Wishlist', backref='product', lazy=True)
    carts = db.relationship('Cart', backref='product', lazy=True)
    reviews = db.relationship('Review', backref='product', lazy=True)
    
    def average_rating(self):
        if self.reviews:
            return sum(review.rating for review in self.reviews) / len(self.reviews)
        return 0
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    delivery_address = db.Column(db.Text)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='pending')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add these new fields for delivery tracking
    tracking_number = db.Column(db.String(100), unique=True)
    estimated_delivery = db.Column(db.DateTime)
    actual_delivery = db.Column(db.DateTime)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    tier = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    features = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Delivery and tracking models
class OrderTracking(db.Model):
    __tablename__ = 'order_tracking'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    order = db.relationship('Order', backref=db.backref('tracking_updates', lazy=True))

class DeliveryPerson(db.Model):
    __tablename__ = 'delivery_persons'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    vehicle_type = db.Column(db.String(50), default='motorcycle')
    vehicle_number = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    current_location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DeliveryAssignment(db.Model):
    __tablename__ = 'delivery_assignments'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('delivery_persons.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='assigned')
    
    order = db.relationship('Order', backref=db.backref('delivery_assignments', lazy=True))
    delivery_person = db.relationship('DeliveryPerson', backref=db.backref('assignments', lazy=True))

class DeliveryConfirmation(db.Model):
    __tablename__ = 'delivery_confirmations'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    buyer_signature = db.Column(db.String(500))
    items_correct = db.Column(db.Boolean, default=False)
    condition_good = db.Column(db.Boolean, default=False)
    received_complete = db.Column(db.Boolean, default=False)
    buyer_notes = db.Column(db.Text)
    confirmed_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_person_notes = db.Column(db.Text)
    
    order = db.relationship('Order', backref=db.backref('delivery_confirmation', uselist=False))

def initialize_database():
    """Initialize database tables and sample data"""
    with app.app_context():
        try:
            # Check if tables exist before creating them
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # List of all tables we need
            required_tables = [
                'users', 'products', 'orders', 'order_items', 
                'wishlists', 'carts', 'reviews', 'subscription_plans',
                'order_tracking', 'delivery_persons', 'delivery_assignments',
                'delivery_confirmations', 'email_verifications'
            ]
            
            # Create only missing tables
            tables_created = False
            for table in required_tables:
                if table not in existing_tables:
                    db.metadata.tables[table].create(db.engine)
                    print(f"✅ Created table: {table}")
                    tables_created = True
            
            if not tables_created:
                print("✅ All database tables already exist!")
            else:
                print("✅ Database tables created successfully!")
            
            # Create admin user if doesn't exist
            create_admin_user()
            
            # Initialize delivery persons
            initialize_delivery_persons()
            
            # Add some sample products if none exist
            if Product.query.count() == 0:
                create_sample_products()
                
        except Exception as e:
            print(f"❌ Error initializing database: {e}")


# Helper function to check if seller has active subscription
def has_active_subscription(user):
    if user.user_type != 'seller':
        return True  # Buyers don't need subscription
    
    if user.subscription_tier == 'basic' and user.subscription_expiry is None:
        return False  # Basic plan without expiry means not subscribed
    
    if user.subscription_expiry and user.subscription_expiry < datetime.utcnow():
        return False  # Subscription expired
    
    return True

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        
        user = get_current_user()
        if user.user_type != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


def merge_session_cart_with_user(user_id):
    """Merge session cart items into user's database cart after login"""
    if 'cart' in session and session['cart']:
        try:
            for product_id_str, quantity in session['cart'].items():
                try:
                    product_id = int(product_id_str)
                except ValueError:
                    continue  # Skip invalid product IDs
                
                # Check if product exists and is active
                product = Product.query.filter_by(id=product_id, is_active=True).first()
                if not product:
                    continue
                
                # Check if user already has this product in cart
                existing_cart_item = Cart.query.filter_by(
                    user_id=user_id, 
                    product_id=product_id
                ).first()
                
                if existing_cart_item:
                    # Update quantity, but don't exceed stock
                    new_quantity = existing_cart_item.quantity + quantity
                    if new_quantity > product.stock:
                        new_quantity = product.stock
                    existing_cart_item.quantity = new_quantity
                else:
                    # Add new cart item, but don't exceed stock
                    final_quantity = min(quantity, product.stock)
                    cart_item = Cart(
                        user_id=user_id, 
                        product_id=product_id, 
                        quantity=final_quantity
                    )
                    db.session.add(cart_item)
            
            db.session.commit()
            
            # Clear session cart after merging
            session.pop('cart', None)
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error merging cart: {e}")
            return False
    return True


# Helper functions for dashboard data
def get_total_sales(seller_id):
    return 0  # Placeholder

def get_unique_customers(seller_id):
    return 0  # Placeholder

def get_products_change(seller_id):
    return 5  # Placeholder

def get_sales_change(seller_id):
    return 12  # Placeholder

def get_customers_change(seller_id):
    return 8  # Placeholder

def get_today_revenue(seller_id):
    return 0  # Placeholder

def get_pending_orders_count(seller_id):
    return 0  # Placeholder

def get_store_rating(seller_id):
    return 4.5  # Placeholder

def get_products_sold_today(seller_id):
    return 0  # Placeholder

def get_wishlist_ids(user_id):
    wishlist_items = Wishlist.query.filter_by(user_id=user_id).all()
    return [item.product_id for item in wishlist_items]


def is_valid_email(email):
    """Check if email is valid (Gmail or UCU format)"""
    if not email:
        return False
    
    email = email.lower().strip()
    
    # Check for Gmail
    if email.endswith('@gmail.com'):
        import re
        gmail_pattern = r'^[a-z0-9]+[\._]?[a-z0-9]+[@]gmail[.]com$'
        return re.match(gmail_pattern, email) is not None
    
    # Check for UCU student email
    if email.endswith('@students.ucu.ac.ug'):
        import re
        ucu_pattern = r'^[ab][0-9]{5}[@]students[.]ucu[.]ac[.]ug$'
        return re.match(ucu_pattern, email) is not None
    
    return False

def get_user_type_by_email(email):
    """Determine if user is UCU student or regular user based on email"""
    email = email.lower().strip()
    if email.endswith('@students.ucu.ac.ug'):
        return 'ucu_student'
    else:
        return 'regular_user'


# ==================== INITIALIZATION FUNCTIONS ====================

def create_admin_user():
    """Create admin user if it doesn't exist"""
    admin_user = User.query.filter_by(email='shopmax4321@gmail.com').first()
    if not admin_user:
        admin_user = User(
            fullname='ShopMax Admin',
            email='shopmax4321@gmail.com',
            phone='0000000000',
            location='Admin Office',
            password=generate_password_hash('ShopMax1234'),
            user_type='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Admin user created successfully!")

def initialize_delivery_persons():
    """Create sample delivery persons if they don't exist"""
    delivery_persons = [
        {
            'name': 'John Boda',
            'phone': '0755123456',
            'vehicle_type': 'motorcycle',
            'vehicle_number': 'UBX123A'
        },
        {
            'name': 'David Rider', 
            'phone': '0755654321',
            'vehicle_type': 'motorcycle',
            'vehicle_number': 'UBX456B'
        },
        {
            'name': 'Sarah Express',
            'phone': '0755789123',
            'vehicle_type': 'bicycle',
            'vehicle_number': 'BIC789'
        }
    ]
    
    for dp_data in delivery_persons:
        existing = DeliveryPerson.query.filter_by(phone=dp_data['phone']).first()
        if not existing:
            delivery_person = DeliveryPerson(**dp_data)
            db.session.add(delivery_person)
    
    db.session.commit()
    print("✅ Delivery persons initialized!")

def create_sample_products():
    """Create sample products for testing"""
    try:
        # Get the admin user to use as seller
        admin = User.query.filter_by(email='shopmax4321@gmail.com').first()
        if not admin:
            print("❌ No admin user found for sample products")
            return
            
        sample_products = [
            {
                'name': 'Wireless Bluetooth Headphones',
                'description': 'High-quality wireless headphones with noise cancellation',
                'price': 25000.0,
                'category': 'electronics',
                'stock': 10,
                'brand': 'AudioTech',
                'condition': 'new'
            },
            {
                'name': 'Smart Watch Fitness Tracker',
                'description': 'Track your fitness goals with this advanced smartwatch',
                'price': 15000.0,
                'category': 'electronics', 
                'stock': 15,
                'brand': 'FitGadget',
                'condition': 'new'
            },
            {
                'name': 'Cotton T-Shirt',
                'description': 'Comfortable cotton t-shirt for everyday wear',
                'price': 5000.0,
                'category': 'fashion',
                'stock': 50,
                'brand': 'FashionWear',
                'condition': 'new'
            }
        ]
        
        for product_data in sample_products:
            product = Product(
                name=product_data['name'],
                description=product_data['description'],
                price=product_data['price'],
                category=product_data['category'],
                stock=product_data['stock'],
                brand=product_data['brand'],
                condition=product_data['condition'],
                seller_id=admin.id,
                is_active=True
            )
            db.session.add(product)
        
        db.session.commit()
        print("✅ Sample products created successfully!")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating sample products: {e}")

def initialize_database():
    """Initialize database tables and sample data"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Create admin user if doesn't exist
            create_admin_user()
            
            # Initialize delivery persons
            initialize_delivery_persons()
            
            # Add some sample products if none exist
            if Product.query.count() == 0:
                create_sample_products()
                
        except Exception as e:
            print(f"❌ Error initializing database: {e}")



@app.context_processor
def inject_user():
    """Make current user available to all templates"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return dict(user=user)
    return dict(user=None)


# ==================== ROUTES ====================
@app.route('/')
def home():
    try:
        # Get real-time platform statistics
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Current date for time-based queries
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Real platform analytics
        stats = {
            # User Analytics
            'total_users': User.query.count(),
            'active_users_week': User.query.filter(
                User.created_at >= week_ago
            ).count(),
            'new_users_week': User.query.filter(
                User.created_at >= week_ago
            ).count(),
            
            # Product Analytics
            'total_products': Product.query.filter_by(is_active=True).count(),
            'new_products_week': Product.query.filter(
                Product.created_at >= week_ago,
                Product.is_active == True
            ).count(),
            
            # Transaction Analytics
            'total_orders': Order.query.count(),
            'completed_orders': Order.query.filter_by(status='completed').count(),
            'pending_orders': Order.query.filter_by(status='pending').count(),
            
            # Category Distribution - Enhanced to include all categories
            'electronics_count': Product.query.filter_by(
                category='electronics', is_active=True
            ).count(),
            'clothing_count': Product.query.filter_by(
                category='clothing', is_active=True
            ).count(),
            'books_count': Product.query.filter_by(
                category='books', is_active=True
            ).count(),
            'home_count': Product.query.filter_by(
                category='home', is_active=True
            ).count(),
            'sports_count': Product.query.filter_by(
                category='sports', is_active=True
            ).count(),
            'fashion_count': Product.query.filter_by(
                category='clothing', is_active=True
            ).count(),  # Alias for clothing
            
            # Seller Analytics
            'active_sellers': User.query.filter_by(
                user_type='seller', is_active=True
            ).count(),
            'new_sellers_week': User.query.filter(
                User.created_at >= week_ago,
                User.user_type == 'seller'
            ).count()
        }
        
        # Recent platform activities
        recent_activities = []
        
        # Recent new products
        new_products = Product.query.filter_by(is_active=True).order_by(
            Product.created_at.desc()
        ).limit(6).all()
        
        # Recent user registrations (this week)
        recent_users = User.query.filter(
            User.created_at >= week_ago
        ).order_by(User.created_at.desc()).limit(5).all()
        
        # Recent orders
        recent_orders = Order.query.order_by(
            Order.created_at.desc()
        ).limit(5).all()
        
    except Exception as e:
        print(f"Error loading home stats: {e}")
        # Fallback empty stats
        stats = {
            'electronics_count': 0,
            'clothing_count': 0, 
            'books_count': 0,
            'home_count': 0,
            'sports_count': 0,
            'fashion_count': 0,
            'total_users': 0,
            'total_products': 0,
            'completed_orders': 0
        }
        new_products = []
        recent_users = []
        recent_orders = []
    
    return render_template('index.html',
                         stats=stats,
                         new_products=new_products,
                         recent_users=recent_users,
                         recent_orders=recent_orders)



@app.route('/verify-email/<token>')
def verify_email(token):
    """Verify email address using token"""
    try:
        verification = EmailVerification.query.filter_by(token=token).first()
        
        if not verification:
            flash('Invalid verification link.', 'danger')
            return redirect(url_for('register_buyer'))
        
        if verification.expires_at < datetime.utcnow():
            flash('Verification link has expired. Please register again.', 'danger')
            db.session.delete(verification)
            db.session.commit()
            return redirect(url_for('register_buyer'))
        
        if verification.is_verified:
            flash('Email already verified. Please login.', 'info')
            return redirect(url_for('login'))
        
        # Mark as verified
        verification.is_verified = True
        db.session.commit()
        
        # Check if we have pending user data
        pending_user = session.get('pending_user')
        if pending_user and pending_user['email'] == verification.email:
            # Create the actual user account
            new_user = User(
                fullname=pending_user['fullname'],
                email=pending_user['email'],
                phone=pending_user['phone'],
                location=pending_user['location'],
                password=pending_user['password'],
                user_type=pending_user['user_type']
            )
            
            # Add seller-specific fields if applicable
            if pending_user['user_type'] == 'seller':
                new_user.business_name = pending_user['business_name']
                new_user.business_address = pending_user['business_address']
                new_user.nin = pending_user['nin']
                new_user.subscription_tier = pending_user['subscription_tier']
            else:
                new_user.delivery_address = pending_user.get('delivery_address', '')
            
            db.session.add(new_user)
            db.session.commit()
            
            # Clean up
            session.pop('pending_user', None)
            db.session.delete(verification)
            db.session.commit()
            
            flash('Email verified successfully! Your account has been created.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email verified, but user data not found. Please complete registration.', 'warning')
            return redirect(url_for('register_buyer'))
            
    except Exception as e:
        db.session.rollback()
        flash('Error verifying email. Please try again.', 'danger')
        return redirect(url_for('register_buyer'))

@app.route('/verify-email-pending')
def verify_email_pending():
    """Show pending verification page"""
    return render_template('verify_email_pending.html')
@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    email = request.form.get('email')
    
    if not email or not is_gmail(email):
        flash('Please enter a valid Gmail address.', 'danger')
        return redirect(url_for('verify_email_pending'))
    
    try:
        # Delete old verification records for this email
        EmailVerification.query.filter_by(email=email).delete()
        
        # Create new verification
        token = generate_verification_token()
        verification = EmailVerification(
            email=email,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(verification)
        db.session.commit()
        
        # Resend email
        if send_verification_email(email, token):
            flash('Verification email resent! Please check your inbox.', 'success')
        else:
            flash('Failed to resend verification email. Please try again.', 'danger')
            
    except Exception as e:
        db.session.rollback()
        flash('Error resending verification. Please try again.', 'danger')
    
    return redirect(url_for('verify_email_pending'))



@app.route('/register/seller', methods=['GET', 'POST'])
def register_seller():
    """Seller registration route - single email field"""
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        location = request.form.get('location')
        business_name = request.form.get('business_name')
        business_address = request.form.get('business_address')
        nin = request.form.get('nin')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate email format
        if not is_valid_email(email):
            flash('Please use a valid email address. Gmail (user@gmail.com) or UCU student email (b00894@students.ucu.ac.ug)', 'danger')
            return render_template('register_seller.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('This email is already registered. Please login instead.', 'danger')
            return render_template('register_seller.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register_seller.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register_seller.html')
        
        if not nin:
            flash('NIN verification is required for seller accounts.', 'danger')
            return render_template('register_seller.html')
        
        try:
            new_user = User(
                fullname=fullname,
                email=email,
                phone=phone,
                location=location,
                business_name=business_name,
                business_address=business_address,
                nin=nin,
                password=generate_password_hash(password),
                user_type='seller',
                subscription_tier='basic'
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['user_name'] = new_user.fullname
            session['user_type'] = new_user.user_type
            
            # Determine user type for welcome message
            user_type = get_user_type_by_email(email)
            if user_type == 'ucu_student':
                flash('🎓 UCU student seller account created! Please choose a subscription plan.', 'success')
            else:
                flash('✅ Seller account created successfully! Please choose a subscription plan.', 'success')
                
            return redirect(url_for('seller_subscription'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating seller account: {e}")
            flash('Error creating account. Please try again.', 'danger')
    
    return render_template('register_seller.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if it's a valid email
        if not is_valid_email(email):
            flash('Please use a valid email address. Gmail or UCU student email.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.fullname
            session['user_type'] = user.user_type
            
            # Merge session cart with user cart after login (only for buyers)
            if user.user_type == 'buyer':
                merge_session_cart_with_user(user.id)
            
            # Determine user type for welcome message
            user_type = get_user_type_by_email(email)
            if user_type == 'ucu_student':
                flash(f'🎓 Welcome back, {user.fullname}! (UCU Student)', 'success')
            else:
                flash(f'✅ Welcome back, {user.fullname}!', 'success')
            
            # Redirect to next URL if set (e.g., checkout)
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            
            if user.user_type == 'seller':
                if not has_active_subscription(user):
                    return redirect(url_for('seller_subscription'))
                else:
                    return redirect(url_for('dashboard'))
            elif user.user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('products'))
        
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('home'))


@app.route('/place_order_manage', methods=['POST'])
@login_required
def place_order_manage():
    """Handle order management"""
    flash('Order management feature coming soon.', 'info')
    return redirect(url_for('checkout'))

# ==================== DASHBOARD ROUTES ====================
@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    
    if user.user_type != 'seller':
        flash('Dashboard is only available for sellers.', 'info')
        return redirect(url_for('products'))
    
    if not has_active_subscription(user):
        flash('Please subscribe to a plan to access the seller dashboard.', 'info')
        return redirect(url_for('seller_subscription'))
    
    # Real data calculations
    try:
        # Total products
        products_count = Product.query.filter_by(seller_id=user.id).count()
        
        # Total sales revenue (from completed orders)
        total_sales_result = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed'
        ).scalar()
        total_sales = float(total_sales_result) if total_sales_result else 0
        
        # Unique customers
        unique_customers = db.session.query(
            db.func.count(db.distinct(Order.user_id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed'
        ).scalar() or 0
        
        # Store rating
        store_rating_result = db.session.query(
            db.func.avg(Review.rating)
        ).join(Product).filter(
            Product.seller_id == user.id
        ).scalar()
        store_rating = round(float(store_rating_result), 1) if store_rating_result else 0
        
        # Calculate percentage changes (last 30 days vs previous 30 days)
        today = datetime.utcnow()
        current_period_start = today - timedelta(days=30)
        previous_period_start = today - timedelta(days=60)
        
        # Products change
        current_products = Product.query.filter(
            Product.seller_id == user.id,
            Product.created_at >= current_period_start
        ).count()
        previous_products = Product.query.filter(
            Product.seller_id == user.id,
            Product.created_at >= previous_period_start,
            Product.created_at < current_period_start
        ).count()
        products_change = calculate_percentage_change(current_products, previous_products)
        
        # Sales change
        current_sales = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed',
            Order.created_at >= current_period_start
        ).scalar() or 0
        previous_sales = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed',
            Order.created_at >= previous_period_start,
            Order.created_at < current_period_start
        ).scalar() or 0
        sales_change = calculate_percentage_change(current_sales, previous_sales)
        
        # Customers change
        current_customers = db.session.query(
            db.func.count(db.distinct(Order.user_id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed',
            Order.created_at >= current_period_start
        ).scalar() or 0
        previous_customers = db.session.query(
            db.func.count(db.distinct(Order.user_id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed',
            Order.created_at >= previous_period_start,
            Order.created_at < current_period_start
        ).scalar() or 0
        customers_change = calculate_percentage_change(current_customers, previous_customers)
        
        # Store stats for the main cards
        store_stats = {
            'products': products_count,
            'total_sales': total_sales,
            'customers': unique_customers,
            'rating': store_rating,
            'products_change': products_change,
            'sales_change': sales_change,
            'customers_change': customers_change
        }
        
        # Quick stats (today's data)
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Today's revenue
        today_revenue = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed',
            Order.created_at >= today_start
        ).scalar() or 0
        
        # Pending orders
        pending_orders = db.session.query(
            db.func.count(db.distinct(Order.id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == user.id,
            Order.status.in_(['pending', 'confirmed', 'processing'])
        ).scalar() or 0
        
        # Products sold today
        products_sold_today = db.session.query(
            db.func.sum(OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == user.id,
            Order.status == 'completed',
            Order.created_at >= today_start
        ).scalar() or 0
        
        quick_stats = {
            'today_revenue': today_revenue,
            'pending_orders': pending_orders,
            'rating': store_rating,
            'products_sold': products_sold_today
        }
        
        # Recent orders (last 5 orders)
        recent_orders = db.session.query(Order).join(OrderItem).filter(
            OrderItem.seller_id == user.id
        ).order_by(Order.created_at.desc()).limit(5).all()
        
        # Low stock products (stock <= 5)
        low_stock_products = Product.query.filter(
            Product.seller_id == user.id,
            Product.stock <= 5,
            Product.stock > 0
        ).order_by(Product.stock.asc()).limit(5).all()
        
        # Recent reviews (last 3 reviews)
        recent_reviews = db.session.query(Review).join(Product).filter(
            Product.seller_id == user.id
        ).order_by(Review.created_at.desc()).limit(3).all()
        
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
        # Fallback data in case of error
        store_stats = {
            'products': 0,
            'total_sales': 0,
            'customers': 0,
            'rating': 0,
            'products_change': 0,
            'sales_change': 0,
            'customers_change': 0
        }
        quick_stats = {
            'today_revenue': 0,
            'pending_orders': 0,
            'rating': 0,
            'products_sold': 0
        }
        recent_orders = []
        low_stock_products = []
        recent_reviews = []
    
    return render_template('seller_dashboard.html',
        user=user,
        store_stats=store_stats,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        quick_stats=quick_stats,
        recent_reviews=recent_reviews
    )

def calculate_percentage_change(current, previous):
    """Calculate percentage change between current and previous values"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)







# ==================== ADMIN ROUTES ====================


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not is_admin():  # Make sure you have an is_admin() function
        return redirect(url_for('index'))
    
    # Get real-time statistics
    total_users = User.query.count()
    total_sellers = User.query.filter_by(user_type='seller').count()
    total_buyers = User.query.filter_by(user_type='buyer').count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    
    # Recent activities
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    recent_products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    
    # Sales data (if you have orders with amounts)
    total_sales = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         total_sellers=total_sellers,
                         total_buyers=total_buyers,
                         total_products=total_products,
                         total_orders=total_orders,
                         total_sales=total_sales,
                         recent_users=recent_users,
                         recent_orders=recent_orders,
                         recent_products=recent_products)
@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract
    
    # Get current month and year
    now = datetime.utcnow()
    current_month = now.month
    current_year = now.year
    
    # Basic statistics
    total_sales = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    total_orders = Order.query.count()
    total_users = User.query.count()
    total_products = Product.query.count()
    total_sellers = User.query.filter_by(user_type='seller').count()
    total_buyers = User.query.filter_by(user_type='buyer').count()
    total_admins = User.query.filter_by(user_type='admin').count()
    
    # Current month revenue
    current_month_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        extract('month', Order.created_at) == current_month,
        extract('year', Order.created_at) == current_year
    ).scalar() or 0
    
    # Last month revenue for comparison
    last_month = current_month - 1 if current_month > 1 else 12
    last_month_year = current_year if current_month > 1 else current_year - 1
    
    last_month_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        extract('month', Order.created_at) == last_month,
        extract('year', Order.created_at) == last_month_year
    ).scalar() or 0
    
    # Revenue growth calculation
    revenue_growth = 0
    if last_month_revenue > 0:
        revenue_growth = ((current_month_revenue - last_month_revenue) / last_month_revenue) * 100
    
    # Order status distribution - FIXED: handle case where no orders exist
    order_status_counts = {}
    status_counts = db.session.query(
        Order.status, 
        func.count(Order.id)
    ).group_by(Order.status).all()
    
    for status, count in status_counts:
        order_status_counts[status or 'unknown'] = count
    
    # Set default statuses with 0 if they don't exist
    default_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    for status in default_statuses:
        if status not in order_status_counts:
            order_status_counts[status] = 0
    
    # Recent orders and users
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Daily revenue for current month (for chart) - FIXED: handle date conversion
    daily_revenue_data = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.total_amount).label('daily_total')
    ).filter(
        extract('month', Order.created_at) == current_month,
        extract('year', Order.created_at) == current_year
    ).group_by(func.date(Order.created_at)).order_by('date').all()
    
    # Prepare chart data - FIXED: handle date conversion properly
    revenue_labels = []
    revenue_data = []
    
    for day_data in daily_revenue_data:
        # Handle date conversion safely
        if hasattr(day_data.date, 'strftime'):
            # It's already a datetime object
            date_str = day_data.date.strftime('%b %d')
        else:
            # It's a string, convert to datetime first
            try:
                date_obj = datetime.strptime(str(day_data.date), '%Y-%m-%d')
                date_str = date_obj.strftime('%b %d')
            except (ValueError, AttributeError):
                # If conversion fails, use the raw string
                date_str = str(day_data.date)
        
        revenue_labels.append(date_str)
        revenue_data.append(float(day_data.daily_total or 0))
    
    # If no data for current month, create empty data for the current month days
    if not revenue_data:
        # Get number of days in current month
        if current_month == 12:
            next_month = 1
            next_year = current_year + 1
        else:
            next_month = current_month + 1
            next_year = current_year
            
        days_in_month = (datetime(next_year, next_month, 1) - timedelta(days=1)).day
        
        # Create labels for all days in current month
        revenue_labels = [f"{now.strftime('%b')} {i}" for i in range(1, days_in_month + 1)]
        revenue_data = [0] * days_in_month
    
    return render_template('admin_analytics.html',
                         total_sales=total_sales,
                         total_orders=total_orders,
                         total_users=total_users,
                         total_products=total_products,
                         total_sellers=total_sellers,
                         total_buyers=total_buyers,
                         total_admins=total_admins,
                         current_month_revenue=current_month_revenue,
                         revenue_growth=revenue_growth,
                         order_status_counts=order_status_counts,
                         recent_orders=recent_orders,
                         recent_users=recent_users,
                         revenue_labels=revenue_labels,
                         revenue_data=revenue_data)





@app.route('/seller/analytics')
@login_required
def seller_analytics():
    """Seller analytics dashboard"""
    user = get_current_user()
    if user.user_type != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get date range from query parameters (default to last 30 days)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.utcnow() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.utcnow()
    
    # Ensure end_date is not in the future
    if end_date > datetime.utcnow():
        end_date = datetime.utcnow()
    
    # Calculate previous period for comparison
    period_days = (end_date - start_date).days
    previous_start = start_date - timedelta(days=period_days)
    previous_end = start_date
    
    try:
        # 1. Total Revenue
        current_revenue = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            Order.seller_id == user.id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.payment_status == 'paid'
        ).scalar() or 0
        
        previous_revenue = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            Order.seller_id == user.id,
            Order.created_at >= previous_start,
            Order.created_at < previous_end,
            Order.payment_status == 'paid'
        ).scalar() or 0
        
        revenue_change = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
        
        # 2. Total Orders
        current_orders = Order.query.filter(
            Order.seller_id == user.id,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).count()
        
        previous_orders = Order.query.filter(
            Order.seller_id == user.id,
            Order.created_at >= previous_start,
            Order.created_at < previous_end
        ).count()
        
        orders_change = ((current_orders - previous_orders) / previous_orders * 100) if previous_orders > 0 else 0
        
        # 3. Products Sold
        products_sold = db.session.query(
            db.func.sum(OrderItem.quantity)
        ).join(Order).filter(
            Order.seller_id == user.id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.payment_status == 'paid'
        ).scalar() or 0
        
        # 4. Store Rating
        rating_result = db.session.query(
            db.func.avg(Review.rating).label('avg_rating'),
            db.func.count(Review.id).label('review_count')
        ).join(Product).filter(
            Product.seller_id == user.id
        ).first()
        
        store_rating = float(rating_result.avg_rating or 0)
        reviews_count = rating_result.review_count or 0
        
        # 5. Line Chart Data (Last 30 days)
        line_chart_labels = []
        line_chart_data = []
        
        for i in range(30):
            date = (datetime.utcnow() - timedelta(days=30-i)).date()
            day_start = datetime.combine(date, datetime.min.time())
            day_end = datetime.combine(date, datetime.max.time())
            
            daily_revenue = db.session.query(
                db.func.sum(OrderItem.price * OrderItem.quantity)
            ).join(Order).filter(
                Order.seller_id == user.id,
                Order.created_at >= day_start,
                Order.created_at <= day_end,
                Order.payment_status == 'paid'
            ).scalar() or 0
            
            line_chart_labels.append(date.strftime('%b %d'))
            line_chart_data.append(float(daily_revenue))
        
        # 6. Category Sales
        category_sales = db.session.query(
            Product.category,
            db.func.sum(OrderItem.price * OrderItem.quantity).label('revenue')
        ).join(OrderItem, Product.id == OrderItem.product_id
        ).join(Order, OrderItem.order_id == Order.id
        ).filter(
            Order.seller_id == user.id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.payment_status == 'paid'
        ).group_by(Product.category).all()
        
        category_data = [{'category': cat, 'revenue': float(rev or 0)} 
                        for cat, rev in category_sales]
        
        # 7. Top Products
        top_products = db.session.query(
            Product.name,
            db.func.sum(OrderItem.quantity).label('total_sold'),
            db.func.sum(OrderItem.price * OrderItem.quantity).label('revenue')
        ).join(OrderItem, Product.id == OrderItem.product_id
        ).join(Order, OrderItem.order_id == Order.id
        ).filter(
            Order.seller_id == user.id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.payment_status == 'paid'
        ).group_by(Product.id, Product.name
        ).order_by(db.desc('revenue')).limit(10).all()
        
        top_products_list = [
            {
                'name': name[:30] + '...' if len(name) > 30 else name,
                'total_sold': total_sold or 0,
                'revenue': float(revenue or 0)
            }
            for name, total_sold, revenue in top_products
        ]
        
        # 8. Recent Orders
        recent_orders = Order.query.filter_by(
            seller_id=user.id
        ).order_by(Order.created_at.desc()).limit(10).all()
        
        # Prepare analytics data
        analytics_data = {
            'total_revenue': float(current_revenue),
            'revenue_change': float(revenue_change),
            'total_orders': current_orders,
            'orders_change': float(orders_change),
            'products_sold': products_sold,
            'store_rating': store_rating,
            'reviews_count': reviews_count,
            'line_chart_labels': line_chart_labels,
            'line_chart_data': line_chart_data,
            'category_sales': category_data,
            'top_products': top_products_list,
            'recent_orders': recent_orders
        }
        
        return render_template('seller_analytics.html',
                             analytics_data=analytics_data,
                             start_date=start_date.strftime('%Y-%m-%d'),
                             end_date=end_date.strftime('%Y-%m-%d'))
        
    except Exception as e:
        print(f"Error in seller analytics: {str(e)}")
        flash('Error loading analytics data. Please try again.', 'error')
        
        # Return empty analytics data on error
        empty_data = {
            'total_revenue': 0,
            'revenue_change': 0,
            'total_orders': 0,
            'orders_change': 0,
            'products_sold': 0,
            'store_rating': 0,
            'reviews_count': 0,
            'line_chart_labels': [],
            'line_chart_data': [],
            'category_sales': [],
            'top_products': [],
            'recent_orders': []
        }
        
        return render_template('seller_analytics.html',
                             analytics_data=empty_data,
                             start_date=start_date.strftime('%Y-%m-%d'),
                             end_date=end_date.strftime('%Y-%m-%d'))






# Admin user management routes - Limited to password and email reset only
@app.route('/admin/users')
@admin_required
def admin_users():
    user = get_current_user()
    users = User.query.order_by(User.created_at.desc()).all()
    
    # Check if users have is_active attribute
    for user_item in users:
        if not hasattr(user_item, 'is_active'):
            user_item.is_active = True  # Set default value
    
    return render_template('admin_users.html', user=user, users=users)


@app.route('/admin/users/<int:user_id>/view')
@admin_required
def admin_view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('admin_view_user.html', user=user)

@app.route('/admin/users/<int:user_id>/reset-credentials', methods=['GET', 'POST'])
@admin_required
def admin_reset_user_credentials(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'reset_password':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                flash('Passwords do not match!', 'error')
                return render_template('admin_reset_credentials.html', user=user)
            
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long!', 'error')
                return render_template('admin_reset_credentials.html', user=user)
            
            user.set_password(new_password)
            flash('Password reset successfully!', 'success')
            
        elif action == 'reset_email':
            new_email = request.form.get('new_email')
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                flash('Email already exists!', 'error')
                return render_template('admin_reset_credentials.html', user=user)
            
            user.email = new_email
            flash('Email updated successfully!', 'success')
        
        try:
            db.session.commit()
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating user: ' + str(e), 'error')
    
    return render_template('admin_reset_credentials.html', user=user)

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    if user_id == session['user_id']:
        flash('You cannot deactivate your own account!', 'error')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    
    # Check if user has is_active attribute, if not, skip the toggle
    if not hasattr(user, 'is_active'):
        flash('User status toggle is not available at the moment.', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    
    try:
        db.session.commit()
        status = "activated" if user.is_active else "deactivated"
        flash(f'User {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating user status: ' + str(e), 'error')
    
    return redirect(url_for('admin_users'))

def is_admin():
    """Check if current user is admin"""
    if 'user_id' not in session:
        return False
    user = User.query.get(session['user_id'])
    return user and user.user_type == 'admin'

from datetime import datetime

@app.context_processor
def utility_processor():
    def get_current_time():
        return datetime.utcnow()
    return dict(now=get_current_time)


# ==================== ADMIN ORDER MANAGEMENT ====================
@app.route('/admin/orders')
def admin_orders():
    """Admin view all orders"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_current_user()
    if user.user_type != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('login'))
    
    from sqlalchemy.orm import joinedload
    
    # Get all orders with related data
    orders = Order.query.options(
        joinedload(Order.user),
        joinedload(Order.order_items).joinedload(OrderItem.product)
    ).order_by(Order.created_at.desc()).all()
    
    return render_template('admin_orders.html', orders=orders)

@app.route('/api/admin/orders/<int:order_id>/update_status', methods=['POST'])
def update_order_status(order_id):
    """Update order status (admin only)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login'})
    
    user = get_current_user()
    if user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'})
    
    try:
        data = request.get_json()
        status = data.get('status')
        
        order = Order.query.get_or_404(order_id)
        
        # Update status
        order.status = status
        
        # If marking as delivered, also update delivery info
        if status == 'delivered':
            order.delivered_at = datetime.utcnow()
            # If customer hasn't confirmed yet, set delivery_confirmed to False
            if not order.delivery_confirmed:
                order.delivery_confirmed = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {status}',
            'order_id': order.id,
            'status': order.status,
            'delivery_confirmed': order.delivery_confirmed
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/orders/<int:order_id>/mark_as_paid', methods=['POST'])
def mark_order_as_paid(order_id):
    """Mark order as paid (admin only)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login'})
    
    user = get_current_user()
    if user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'})
    
    try:
        order = Order.query.get_or_404(order_id)
        
        order.payment_status = 'paid'
        order.paid_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Order marked as paid',
            'order_id': order.id,
            'payment_status': order.payment_status
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/orders/<int:order_id>/delivery_confirmation', methods=['POST'])
def admin_check_delivery_confirmation(order_id):
    """Check or update delivery confirmation status"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login'})
    
    user = get_current_user()
    if user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'})
    
    try:
        order = Order.query.get_or_404(order_id)
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'delivery_confirmed': order.delivery_confirmed,
            'status': order.status,
            'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    


@app.route('/admin/sellers')
@admin_required
def admin_sellers():
    user = get_current_user()
    sellers = User.query.filter_by(user_type='seller').order_by(User.created_at.desc()).all()
    return render_template('admin_sellers.html', user=user, sellers=sellers)

@app.route('/admin/settings')
@admin_required
def admin_settings():
    user = get_current_user()
    return render_template('admin_settings.html', user=user)

@app.route('/admin/reports')
@admin_required
def admin_reports():
    user = get_current_user()
    return render_template('admin_reports.html', user=user)

@app.route('/admin/products')
@admin_required
def admin_products():
    user = get_current_user()
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin_products.html', user=user, products=products)


# Admin Products Management Routes
@app.route('/admin/products')
@admin_required
def admin_products_management():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = Product.query
    
    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) |
            (Product.description.ilike(f'%{search}%'))
        )
    
    if category:
        query = query.filter(Product.category == category)
    
    products = query.order_by(Product.created_at.desc()).all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/<int:product_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_product_status(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    
    try:
        db.session.commit()
        status = "activated" if product.is_active else "deactivated"
        flash(f'Product {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating product: {str(e)}', 'error')
    
    return redirect(url_for('admin_products_management'))

@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'error')
    
    return redirect(url_for('admin_products_management'))



@app.route('/admin/tracking')
@admin_required
def admin_tracking():
    """Simple admin tracking dashboard"""
    user = get_current_user()
    
    # Get active orders that need delivery
    active_orders = Order.query.filter(
        Order.status.in_(['confirmed', 'processing', 'shipped', 'in_transit'])
    ).order_by(Order.created_at.desc()).all()
    
    # Get available delivery persons
    delivery_persons = DeliveryPerson.query.filter_by(is_active=True).all()
    
    # Get orders with delivery assignments
    assigned_orders = []
    for order in active_orders:
        assignment = DeliveryAssignment.query.filter_by(order_id=order.id).first()
        if assignment:
            assigned_orders.append({
                'order': order,
                'assignment': assignment,
                'delivery_person': assignment.delivery_person
            })
    
    return render_template('admin_tracking.html',
                         user=user,
                         active_orders=active_orders,
                         delivery_persons=delivery_persons,
                         assigned_orders=assigned_orders)


@app.route('/admin/analytics')
@login_required
def admin_analytics_management():
    if not is_admin():
        return redirect(url_for('index'))
    
    # Basic analytics data - you can expand this later
    total_sales = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    total_orders = Order.query.count()
    total_users = User.query.count()
    total_products = Product.query.count()
    total_sellers = User.query.filter_by(user_type='seller').count()
    total_buyers = User.query.filter_by(user_type='buyer').count()
    
    # Recent data for charts
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    return render_template('admin_analytics.html',
                         total_sales=total_sales,
                         total_orders=total_orders,
                         total_users=total_users,
                         total_products=total_products,
                         total_sellers=total_sellers,
                         total_buyers=total_buyers,
                         recent_orders=recent_orders,
                         recent_users=recent_users)




@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def admin_edit_user(user_id):
    """Admin edit user details"""
    user = User.query.get_or_404(user_id)
    
    try:
        user.fullname = request.form.get('fullname')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.location = request.form.get('location')
        user.user_type = request.form.get('user_type')
        
        if user.user_type == 'seller':
            user.business_name = request.form.get('business_name')
            user.business_address = request.form.get('business_address')
            user.subscription_tier = request.form.get('subscription_tier')
        elif user.user_type == 'buyer':
            user.delivery_address = request.form.get('delivery_address')
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'User {user.fullname} updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'danger')
    
    return redirect(url_for('admin_users_management'))





# ==================== PROFILE ROUTES ====================

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    
    store_stats = {}
    
    if user.user_type == 'seller':
        if not has_active_subscription(user):
            flash('Please subscribe to a plan to access your profile.', 'info')
            return redirect(url_for('seller_subscription'))
        
        products_count = Product.query.filter_by(seller_id=user.id).count()
        orders_count = Order.query.join(OrderItem)\
            .filter(OrderItem.seller_id == user.id).count()
        
        store_stats = {
            'products': products_count,
            'orders': orders_count,
            'revenue': get_total_sales(user.id),
            'rating': get_store_rating(user.id)
        }
    
    return render_template('profile.html', user=user, store_stats=store_stats)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = get_current_user()
    
    if user.user_type == 'seller' and not has_active_subscription(user):
        flash('Please subscribe to a plan to update your profile.', 'info')
        return redirect(url_for('seller_subscription'))
    
    try:
        user.fullname = request.form.get('fullname')
        user.phone = request.form.get('phone')
        user.location = request.form.get('location')
        
        if user.user_type == 'buyer':
            user.delivery_address = request.form.get('delivery_address')
        else:
            user.business_name = request.form.get('business_name')
            user.business_address = request.form.get('business_address')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash('Error updating profile. Please try again.', 'danger')
    
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    user = get_current_user()
    
    if user.user_type == 'seller' and not has_active_subscription(user):
        flash('Please subscribe to a plan to change your password.', 'info')
        return redirect(url_for('seller_subscription'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not check_password_hash(user.password, current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('profile') + '#security')
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('profile') + '#security')
    
    if len(new_password) < 6:
        flash('Password must be at least 6 characters', 'danger')
        return redirect(url_for('profile') + '#security')
    
    try:
        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Password updated successfully!', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash('Error updating password. Please try again.', 'danger')
    
    return redirect(url_for('profile') + '#security')



# ==================== PRODUCT ROUTES ====================
@app.route('/products')
@app.route('/products/<category>')
def products(category=None):
    """Display products page with filtering by category"""
    from sqlalchemy.orm import joinedload
    from sqlalchemy import desc
    
    # Debug: Check total products in database
    total_products = Product.query.filter_by(is_active=True).count()
    print(f"DEBUG: Total active products in database: {total_products}")
    
    # Get products based on category
    if category and category != 'all':
        print(f"DEBUG: Filtering by category: {category}")
        items = Product.query.options(joinedload(Product.seller)).filter_by(
            category=category,
            is_active=True
        ).all()
    else:
        items = Product.query.options(joinedload(Product.seller)).filter_by(is_active=True).all()
    
    print(f"DEBUG: Found {len(items)} products for category: {category or 'all'}")
    
    # Get new arrivals (10 most recent products)
    new_arrivals = Product.query.filter_by(is_active=True)\
        .order_by(desc(Product.created_at))\
        .limit(10)\
        .all()
    
    print(f"DEBUG: New arrivals: {len(new_arrivals)} products")
    
    # Get trending products (show random products for now)
    # You can change this logic later - e.g., most viewed, most sold, etc.
    trending_products = Product.query.filter_by(is_active=True)\
        .order_by(db.func.random())\
        .limit(10)\
        .all()
    
    print(f"DEBUG: Trending products: {len(trending_products)} products")
    
    # Get wishlist IDs if user is logged in
    wishlist_ids = []
    if 'user_id' in session:
        try:
            from models import Wishlist
            wishlist = Wishlist.query.filter_by(user_id=session['user_id']).all()
            wishlist_ids = [item.product_id for item in wishlist]
            print(f"DEBUG: User has {len(wishlist_ids)} items in wishlist")
        except Exception as e:
            print(f"DEBUG: Error getting wishlist: {e}")
            wishlist_ids = []
    else:
        print("DEBUG: User not logged in, wishlist empty")
    
    # Debug: Print sample product info
    if items and len(items) > 0:
        sample = items[0]
        print(f"DEBUG: Sample product - ID: {sample.id}, Name: {sample.name}, Category: {sample.category}, Price: {sample.price}, Stock: {sample.stock}")
        if sample.seller:
            print(f"DEBUG: Sample product seller - ID: {sample.seller.id}, Name: {sample.seller.fullname}")
    
    return render_template('products.html', 
                         items=items, 
                         category=category or 'all',
                         new_arrivals=new_arrivals,
                         trending_products=trending_products,
                         wishlist_ids=wishlist_ids)



# ==================== SELLER PRODUCT MANAGEMENT ROUTES ====================

@app.route('/seller/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    user = get_current_user()
    
    if user.user_type != 'seller' or not has_active_subscription(user):
        flash('Please subscribe to a plan to add products.', 'info')
        return redirect(url_for('seller_subscription'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', '').strip()
            category = request.form.get('category', '').strip()
            stock = request.form.get('stock', '1').strip()
            brand = request.form.get('brand', '').strip()
            condition = request.form.get('condition', 'new')
            
            if not all([name, description, price, category]):
                flash('Please fill in all required fields: Name, Description, Price, and Category.', 'danger')
                return render_template('add_product.html')
            
            image_file = request.files.get('image')
            image_filename = None
            
            if image_file and image_file.filename:
                if allowed_file(image_file.filename):
                    ensure_upload_folder()
                    filename = secure_filename(image_file.filename)
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                    image_filename = timestamp + filename
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                    image_file.save(image_path)
                else:
                    flash('Please upload JPG, PNG, or GIF images only.', 'danger')
                    return render_template('add_product.html')
            
            new_product = Product(
                name=name,
                description=description,
                price=float(price),
                category=category,
                stock=int(stock) if stock else 1,
                image=image_filename,
                brand=brand if brand else None,
                condition=condition,
                seller_id=user.id,
                is_active=True
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            flash('🎉 Product added successfully!', 'success')
            return redirect(url_for('manage_products'))
            
        except ValueError as e:
            flash('Please enter valid price and stock values.', 'danger')
            return render_template('add_product.html')
        except Exception as e:
            db.session.rollback()
            flash('Error adding product. Please try again.', 'danger')
            return render_template('add_product.html')
    
    return render_template('add_product.html')

@app.route('/seller/products')
@login_required
def manage_products():
    user = get_current_user()
    
    if user.user_type != 'seller' or not has_active_subscription(user):
        flash('Please subscribe to a plan to manage products.', 'info')
        return redirect(url_for('seller_subscription'))
    
    products = Product.query.filter_by(seller_id=user.id).order_by(Product.created_at.desc()).all()
    
    active_products = sum(1 for p in products if p.is_active)
    low_stock_count = sum(1 for p in products if p.stock <= 5 and p.stock > 0)
    total_value = sum(p.price * p.stock for p in products if p.is_active)
    
    return render_template('manage_products.html', 
                         products=products,
                         active_products=active_products,
                         low_stock_count=low_stock_count,
                         total_value=total_value)

@app.route('/seller/products/<int:product_id>/toggle')
@login_required
def toggle_product(product_id):
    user = get_current_user()
    
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != user.id:
        flash('You can only manage your own products.', 'danger')
        return redirect(url_for('manage_products'))
    
    try:
        product.is_active = not product.is_active
        db.session.commit()
        
        status = "activated" if product.is_active else "deactivated"
        flash(f'Product {status} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error updating product status.', 'danger')
    
    return redirect(url_for('manage_products'))



@app.route('/product/<int:product_id>')
def product_detail(product_id):
    from sqlalchemy.orm import joinedload
    
    product = Product.query.options(joinedload(Product.seller)).get_or_404(product_id)
    
    related_products = Product.query.filter(
        Product.category == product.category,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()
    
    wishlist_ids = []
    if 'user_id' in session:
        wishlist_ids = get_wishlist_ids(session['user_id'])
    
    return render_template('product_detail.html', 
                         product=product, 
                         related_products=related_products,
                         wishlist_ids=wishlist_ids,
                         min=min)

@app.route('/seller/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    user = get_current_user()
    
    if user.user_type != 'seller' or not has_active_subscription(user):
        flash('Please subscribe to a plan to edit products.', 'info')
        return redirect(url_for('seller_subscription'))
    
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != user.id:
        flash('You can only edit your own products.', 'danger')
        return redirect(url_for('manage_products'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', '').strip()
            category = request.form.get('category', '').strip()
            stock = request.form.get('stock', '1').strip()
            brand = request.form.get('brand', '').strip()
            condition = request.form.get('condition', 'new')
            
            if not all([name, description, price, category]):
                flash('Please fill in all required fields: Name, Description, Price, and Category.', 'danger')
                return render_template('edit_product.html', product=product)
            
            image_file = request.files.get('image')
            
            if image_file and image_file.filename:
                if allowed_file(image_file.filename):
                    ensure_upload_folder()
                    filename = secure_filename(image_file.filename)
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                    image_filename = timestamp + filename
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                    image_file.save(image_path)
                    
                    if product.image:
                        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    product.image = image_filename
                else:
                    flash('Please upload JPG, PNG, or GIF images only.', 'danger')
                    return render_template('edit_product.html', product=product)
            
            product.name = name
            product.description = description
            product.price = float(price)
            product.category = category
            product.stock = int(stock) if stock else 1
            product.brand = brand if brand else None
            product.condition = condition
            product.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('✅ Product updated successfully!', 'success')
            return redirect(url_for('manage_products'))
            
        except ValueError as e:
            flash('Please enter valid price and stock values.', 'danger')
            return render_template('edit_product.html', product=product)
        except Exception as e:
            db.session.rollback()
            flash('Error updating product. Please try again.', 'danger')
            return render_template('edit_product.html', product=product)
    
    return render_template('edit_product.html', product=product)

@app.route('/seller/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    user = get_current_user()
    
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != user.id:
        flash('You can only delete your own products.', 'danger')
        return redirect(url_for('manage_products'))
    
    try:
        if product.image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(product)
        db.session.commit()
        
        flash('Product deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product. Please try again.', 'danger')
    
    return redirect(url_for('manage_products'))





# ==================== CART ROUTES ====================
@app.route('/cart')
def view_cart():
    """View cart - accessible to everyone"""
    # Check if user is logged in
    if 'user_id' in session:
        user = get_current_user()
        
        # Only buyers can access cart if logged in
        if user.user_type != 'buyer':
            flash('Cart is only available for buyers.', 'info')
            return redirect(url_for('products'))
        
        from sqlalchemy.orm import joinedload
        cart_items = db.session.query(Cart, Product).\
            join(Product, Cart.product_id == Product.id).\
            options(joinedload(Product.seller)).\
            filter(Cart.user_id == user.id).\
            all()
    else:
        # For non-logged-in users, use session-based cart
        session_cart = session.get('cart', {})
        cart_items = []
        
        if session_cart:
            product_ids = []
            for pid in session_cart.keys():
                try:
                    product_ids.append(int(pid))
                except ValueError:
                    continue  # Skip invalid product IDs
            
            if product_ids:
                from sqlalchemy.orm import joinedload
                products = Product.query.filter(Product.id.in_(product_ids)).\
                    options(joinedload(Product.seller)).all()
                
                for product in products:
                    quantity = session_cart.get(str(product.id), 0)
                    if quantity > 0:
                        # Create a simple dictionary for cart item
                        cart_item = {
                            'id': f"session_{product.id}",
                            'quantity': quantity
                        }
                        cart_items.append((cart_item, product))
    
    # Calculate totals
    subtotal = 0
    for cart_item, product in cart_items:
        if isinstance(cart_item, dict):
            quantity = cart_item['quantity']
        elif hasattr(cart_item, 'quantity'):
            quantity = cart_item.quantity
        else:
            quantity = 0
        subtotal += product.price * quantity
    
    delivery_fee = 0
    total = subtotal + delivery_fee
    
    return render_template('cart.html', 
                         cart_items=cart_items, 
                         subtotal=subtotal,
                         delivery_fee=delivery_fee,
                         total=total)


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """Add item to cart - works for both logged-in and guest users"""
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    try:
        product = Product.query.filter_by(id=product_id, is_active=True).first()
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})
        
        if product.stock < quantity:
            return jsonify({
                'success': False, 
                'message': f'Only {product.stock} items available in stock'
            })
        
        if 'user_id' in session:
            # User is logged in - use database cart
            user = get_current_user()
            
            # Only buyers can add to cart
            if user.user_type != 'buyer':
                return jsonify({'success': False, 'message': 'Only buyers can add items to cart.'})
            
            cart_item = Cart.query.filter_by(user_id=user.id, product_id=product_id).first()
            if cart_item:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > product.stock:
                    return jsonify({
                        'success': False, 
                        'message': f'Cannot add more than available stock. You have {cart_item.quantity} in cart, only {product.stock - cart_item.quantity} more available.'
                    })
                cart_item.quantity = new_quantity
            else:
                cart_item = Cart(user_id=user.id, product_id=product_id, quantity=quantity)
                db.session.add(cart_item)
            
            db.session.commit()
            cart_count = Cart.query.filter_by(user_id=user.id).count()
        else:
            # Guest user - use session cart
            cart = session.get('cart', {})
            product_key = str(product_id)
            
            current_qty = cart.get(product_key, 0)
            new_qty = current_qty + quantity
            
            if new_qty > product.stock:
                return jsonify({
                    'success': False,
                    'message': f'Cannot add more than available stock. You have {current_qty} in cart, only {product.stock - current_qty} more available.'
                })
            
            cart[product_key] = new_qty
            session['cart'] = cart
            cart_count = sum(cart.values())
        
        return jsonify({
            'success': True, 
            'message': 'Added to cart successfully',
            'cart_count': cart_count
        })
    
    except Exception as e:
        if 'user_id' in session:
            db.session.rollback()
        return jsonify({'success': False, 'message': 'Error adding to cart'})

@app.route('/api/cart/update', methods=['POST'])
def update_cart_item():
    """Update cart item quantity"""
    data = request.get_json()
    cart_item_id = data.get('cart_item_id')
    quantity = data.get('quantity')
    
    if 'user_id' in session:
        # User is logged in
        user = get_current_user()
        
        if user.user_type != 'buyer':
            return jsonify({'success': False, 'message': 'Cart is only available for buyers.'})
        
        try:
            cart_item = Cart.query.filter_by(id=cart_item_id, user_id=user.id).first()
            
            if not cart_item:
                return jsonify({'success': False, 'message': 'Cart item not found'})
            
            if quantity <= 0:
                db.session.delete(cart_item)
            else:
                product = Product.query.get(cart_item.product_id)
                if quantity > product.stock:
                    return jsonify({
                        'success': False, 
                        'message': f'Only {product.stock} items available in stock'
                    })
                cart_item.quantity = quantity
            
            db.session.commit()
            
            cart_count = Cart.query.filter_by(user_id=user.id).count()
            cart_items = Cart.query.filter_by(user_id=user.id).all()
            subtotal = sum(item.quantity * item.product.price for item in cart_items)
            
            return jsonify({
                'success': True, 
                'message': 'Cart updated successfully',
                'cart_count': cart_count,
                'subtotal': subtotal
            })
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Error updating cart'})
    else:
        # Guest user - update session cart
        try:
            cart = session.get('cart', {})
            
            # Find the product ID from cart_item_id (format: "session_{product_id}")
            if cart_item_id.startswith('session_'):
                product_id = cart_item_id.replace('session_', '')
                
                if quantity <= 0:
                    cart.pop(product_id, None)
                else:
                    product = Product.query.get(product_id)
                    if not product:
                        return jsonify({'success': False, 'message': 'Product not found'})
                    
                    if quantity > product.stock:
                        return jsonify({
                            'success': False, 
                            'message': f'Only {product.stock} items available in stock'
                        })
                    
                    cart[product_id] = quantity
                
                session['cart'] = cart
                
                # Calculate cart count and subtotal
                cart_count = sum(cart.values())
                subtotal = 0
                for pid, qty in cart.items():
                    product = Product.query.get(pid)
                    if product:
                        subtotal += product.price * qty
                
                return jsonify({
                    'success': True, 
                    'message': 'Cart updated successfully',
                    'cart_count': cart_count,
                    'subtotal': subtotal
                })
            else:
                return jsonify({'success': False, 'message': 'Invalid cart item'})
        
        except Exception as e:
            return jsonify({'success': False, 'message': 'Error updating cart'})

@app.route('/api/cart/remove', methods=['POST'])
def remove_cart_item():
    """Remove item from cart"""
    data = request.get_json()
    cart_item_id = data.get('cart_item_id')
    
    if 'user_id' in session:
        # User is logged in
        user = get_current_user()
        
        if user.user_type != 'buyer':
            return jsonify({'success': False, 'message': 'Cart is only available for buyers.'})
        
        try:
            cart_item = Cart.query.filter_by(id=cart_item_id, user_id=user.id).first()
            
            if cart_item:
                db.session.delete(cart_item)
                db.session.commit()
                
                cart_count = Cart.query.filter_by(user_id=user.id).count()
                
                return jsonify({
                    'success': True, 
                    'message': 'Item removed from cart',
                    'cart_count': cart_count
                })
            else:
                return jsonify({'success': False, 'message': 'Cart item not found'})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Error removing item from cart'})
    else:
        # Guest user - remove from session cart
        try:
            cart = session.get('cart', {})
            
            if cart_item_id.startswith('session_'):
                product_id = cart_item_id.replace('session_', '')
                cart.pop(product_id, None)
                session['cart'] = cart
                
                cart_count = sum(cart.values())
                
                return jsonify({
                    'success': True, 
                    'message': 'Item removed from cart',
                    'cart_count': cart_count
                })
            else:
                return jsonify({'success': False, 'message': 'Invalid cart item'})
        
        except Exception as e:
            return jsonify({'success': False, 'message': 'Error removing item from cart'})

@app.route('/api/cart/clear', methods=['POST'])
def clear_cart():
    """Clear entire cart"""
    if 'user_id' in session:
        # User is logged in
        user = get_current_user()
        
        if user.user_type != 'buyer':
            return jsonify({'success': False, 'message': 'Cart is only available for buyers.'})
        
        try:
            Cart.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Cart cleared successfully'})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Error clearing cart'})
    else:
        # Guest user - clear session cart
        try:
            session.pop('cart', None)
            return jsonify({'success': True, 'message': 'Cart cleared successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': 'Error clearing cart'})
@app.route('/checkout')
def checkout():
    """Checkout page - requires login"""
    # Check if user is logged in
    if 'user_id' not in session:
        # Check if there are items in cart
        session_cart = session.get('cart', {})
        if not session_cart:
            flash('Your cart is empty. Add some products before checkout.', 'info')
            return redirect(url_for('view_cart'))
        
        # Store the intended destination and redirect to login
        session['next_url'] = url_for('checkout')
        flash('Please login or create an account to proceed to checkout.', 'info')
        return redirect(url_for('login'))
    
    user = get_current_user()
    
    # Only buyers can checkout
    if user.user_type != 'buyer':
        flash('Checkout is only available for buyers.', 'info')
        return redirect(url_for('products'))
    
    from sqlalchemy.orm import joinedload
    
    # Get cart items from database
    cart_items = db.session.query(Cart, Product).\
        join(Product, Cart.product_id == Product.id).\
        options(joinedload(Product.seller)).\
        filter(Cart.user_id == user.id).\
        all()
    
    if not cart_items:
        flash('Your cart is empty. Add some products before checkout.', 'info')
        return redirect(url_for('view_cart'))
    
    # Check stock availability
    for cart_item, product in cart_items:
        if product.stock < cart_item.quantity:
            flash(f'Sorry, "{product.name}" only has {product.stock} items in stock. Please adjust your quantity.', 'danger')
            return redirect(url_for('view_cart'))
    
    subtotal = 0
    for cart_item, product in cart_items:
        subtotal += product.price * cart_item.quantity
    
    delivery_fee = 5000  # 5,000 UGX delivery fee
    total = subtotal + delivery_fee
    
    return render_template('checkout.html', 
                         cart_items=cart_items,
                         subtotal=subtotal,
                         delivery_fee=delivery_fee,
                         total=total,
                         user=user)

   
    

# ==================== ORDER MANAGEMENT ROUTES ====================
@app.route('/orders')
@login_required
def user_orders():
    user = get_current_user()
    
    try:
        if user.user_type == 'buyer':
            # Buyers see their own orders with proper data loading
            orders = Order.query.filter_by(user_id=user.id)\
                .options(
                    db.joinedload(Order.order_items).joinedload(OrderItem.product),
                    db.joinedload(Order.order_items).joinedload(OrderItem.seller)
                )\
                .order_by(Order.created_at.desc()).all()
        elif user.user_type == 'seller':
            # Sellers see orders for their products
            orders = Order.query.join(OrderItem).filter(
                OrderItem.seller_id == user.id
            )\
            .options(
                db.joinedload(Order.order_items).joinedload(OrderItem.product),
                db.joinedload(Order.order_items).joinedload(OrderItem.seller)
            )\
            .order_by(Order.created_at.desc()).all()
        else:
            # Admin sees all orders
            orders = Order.query\
                .options(
                    db.joinedload(Order.order_items).joinedload(OrderItem.product),
                    db.joinedload(Order.order_items).joinedload(OrderItem.seller)
                )\
                .order_by(Order.created_at.desc()).all()
        
        return render_template('user_orders.html', orders=orders, user=user)
    
    except Exception as e:
        print(f"Error loading orders: {str(e)}")
        flash('Error loading your orders. Please try again.', 'danger')
        return render_template('user_orders.html', orders=[], user=user)


@app.route('/my-orders')
@login_required
def my_orders():
    """Alias for user_orders to fix template errors"""
    return user_orders()

@app.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    user = get_current_user()
    order = Order.query.get_or_404(order_id)
    
    # Check if user has permission to view this order
    if user.user_type == 'buyer' and order.user_id != user.id:
        flash('You can only view your own orders.', 'danger')
        return redirect(url_for('user_orders'))
    
    if user.user_type == 'seller':
        seller_order_items = OrderItem.query.filter_by(
            order_id=order_id, 
            seller_id=user.id
        ).all()
        if not seller_order_items:
            flash('You can only view orders for your products.', 'danger')
            return redirect(url_for('user_orders'))
    
    order_items = OrderItem.query.filter_by(order_id=order_id).all()
    tracking_updates = OrderTracking.query.filter_by(order_id=order_id).order_by(OrderTracking.created_at).all()
    
    # Get delivery assignment if exists
    delivery_assignment = DeliveryAssignment.query.filter_by(order_id=order_id).first()
    delivery_confirmation = DeliveryConfirmation.query.filter_by(order_id=order_id).first()
    
    return render_template('order_details.html',
                         order=order,
                         order_items=order_items,
                         tracking_updates=tracking_updates,
                         delivery_assignment=delivery_assignment,
                         delivery_confirmation=delivery_confirmation,
                         user=user)






@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    user = get_current_user()
    
    # Only buyers can place orders
    if user.user_type != 'buyer':
        flash('Only buyers can place orders.', 'danger')
        return redirect(url_for('products'))
    
    from sqlalchemy.orm import joinedload
    
    # Get cart items
    cart_items = db.session.query(Cart, Product).\
        join(Product, Cart.product_id == Product.id).\
        options(joinedload(Product.seller)).\
        filter(Cart.user_id == user.id).\
        all()
    
    if not cart_items:
        flash('Your cart is empty.', 'danger')
        return redirect(url_for('view_cart'))
    
    # Validate delivery address
    delivery_address = request.form.get('delivery_address', '').strip()
    if not delivery_address:
        flash('Please provide a delivery address.', 'danger')
        return redirect(url_for('checkout'))
    
    # Validate phone number
    phone = request.form.get('phone', '').strip()
    if not phone:
        flash('Please provide your phone number.', 'danger')
        return redirect(url_for('checkout'))
    
    # Check stock availability
    for cart_item, product in cart_items:
        if product.stock < cart_item.quantity:
            flash(f'Sorry, "{product.name}" only has {product.stock} items in stock. Please adjust your quantity.', 'danger')
            return redirect(url_for('view_cart'))
    
    # Calculate total
    subtotal = 0
    for cart_item, product in cart_items:
        subtotal += product.price * cart_item.quantity
    
    delivery_fee = 5000  # 5,000 UGX delivery fee
    total = subtotal + delivery_fee
    
    payment_method = request.form.get('payment_method', 'cash_on_delivery')
    delivery_instructions = request.form.get('delivery_instructions', '')
    order_notes = request.form.get('order_notes', '')
    
    try:
        # Update user's phone and delivery address
        user.phone = phone
        user.delivery_address = delivery_address
        user.updated_at = datetime.utcnow()
        
        # Create order
        new_order = Order(
            total_amount=total,
            delivery_address=delivery_address,
            payment_method=payment_method,
            payment_status='pending',
            user_id=user.id,
            status='confirmed'
        )
        db.session.add(new_order)
        db.session.flush()  # To get the order ID
        
        # Create order items
        for cart_item, product in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                seller_id=product.seller_id,
                quantity=cart_item.quantity,
                price=product.price
            ) 
            db.session.add(order_item)
            
            # Update product stock
            product.stock -= cart_item.quantity
        
        # Clear cart
        Cart.query.filter_by(user_id=user.id).delete()
        
        db.session.commit()
        
        # Get order items for confirmation page
        order_items = OrderItem.query.filter_by(order_id=new_order.id).all()
        
        # Create initial tracking update
        tracking_update = OrderTracking(
            order_id=new_order.id,
            status='confirmed',
            notes='Order placed successfully. Preparing for processing.'
        )
        db.session.add(tracking_update)
        db.session.commit()
        
        # Send notifications
        send_order_notifications(new_order, order_items)
        
        return render_template('order_confirmation.html', 
                             order=new_order, 
                             order_items=order_items,
                             user=user)
    
    except Exception as e:
        db.session.rollback()
        print(f"Error placing order: {str(e)}")
        flash('We encountered an issue while processing your order. Please try again or contact support if the problem persists.', 'danger')
        return redirect(url_for('checkout'))



@app.route('/api/order/<int:order_id>/tracking', methods=['POST'])
@login_required
def update_order_tracking(order_id):
    user = get_current_user()
    
    # Only admin and sellers can update tracking
    if user.user_type not in ['admin', 'seller']:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.get_json()
    status = data.get('status')
    location = data.get('location')
    notes = data.get('notes')
    
    try:
        # Create tracking update
        tracking_update = OrderTracking(
            order_id=order_id,
            status=status,
            location=location,
            notes=notes
        )
        db.session.add(tracking_update)
        
        # Update order status
        order = Order.query.get(order_id)
        order.status = status
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Tracking updated successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error updating tracking'})

# ==================== DELIVERY MANAGEMENT ROUTES ====================
# Delivery Management Routes
@app.route('/admin/delivery')
@admin_required
def delivery_management():
    delivery_persons = DeliveryPerson.query.all()
    active_deliveries = DeliveryAssignment.query.filter(
        DeliveryAssignment.status.in_(['assigned', 'picked_up', 'in_transit'])
    ).order_by(DeliveryAssignment.assigned_at.desc()).all()
    
    return render_template('delivery_management.html', 
                         delivery_persons=delivery_persons,
                         active_deliveries=active_deliveries)

@app.route('/admin/delivery/person/add', methods=['POST'])
@admin_required
def add_delivery_person():
    name = request.form.get('name')
    phone = request.form.get('phone')
    vehicle_type = request.form.get('vehicle_type')
    vehicle_number = request.form.get('vehicle_number')
    
    # Check if phone already exists
    existing = DeliveryPerson.query.filter_by(phone=phone).first()
    if existing:
        flash('Delivery person with this phone number already exists!', 'error')
        return redirect(url_for('delivery_management'))
    
    delivery_person = DeliveryPerson(
        name=name,
        phone=phone,
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number
    )
    
    try:
        db.session.add(delivery_person)
        db.session.commit()
        flash('Delivery person added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding delivery person: {str(e)}', 'error')
    
    return redirect(url_for('delivery_management'))

@app.route('/admin/delivery/person/<int:person_id>/toggle', methods=['POST'])
@admin_required
def toggle_delivery_person_status(person_id):
    person = DeliveryPerson.query.get_or_404(person_id)
    person.is_active = not person.is_active
    
    try:
        db.session.commit()
        status = "activated" if person.is_active else "deactivated"
        flash(f'Delivery person {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating delivery person: {str(e)}', 'error')
    
    return redirect(url_for('delivery_management'))

@app.route('/admin/delivery/track/<int:delivery_id>')
@admin_required
def track_delivery(delivery_id):
    delivery = DeliveryAssignment.query.get_or_404(delivery_id)
    tracking_history = OrderTracking.query.filter_by(
        order_id=delivery.order_id
    ).order_by(OrderTracking.created_at.desc()).all()
    
    return render_template('track_delivery.html',
                         delivery=delivery,
                         tracking_history=tracking_history)

@app.route('/admin/delivery/<int:delivery_id>/update-status', methods=['POST'])
@admin_required
def update_delivery_status(delivery_id):
    delivery = DeliveryAssignment.query.get_or_404(delivery_id)
    new_status = request.form.get('status')
    
    if new_status in ['assigned', 'picked_up', 'in_transit', 'delivered']:
        delivery.status = new_status
        
        # Update timestamps
        if new_status == 'picked_up' and not delivery.assigned_at:
            delivery.assigned_at = datetime.utcnow()
        elif new_status == 'delivered' and not delivery.completed_at:
            delivery.completed_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash(f'Delivery status updated to {new_status.replace("_", " ")}!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating delivery status: {str(e)}', 'error')
    
    return redirect(url_for('track_delivery', delivery_id=delivery_id))


# ==================== SIMPLE BODA TRACKING ROUTES ====================

@app.route('/api/order/<int:order_id>/assign-boda', methods=['POST'])
@admin_required
def assign_boda_to_order(order_id):
    """Assign a boda rider to an order"""
    try:
        boda_id = request.json.get('boda_id')
        order = Order.query.get_or_404(order_id)
        boda = DeliveryPerson.query.get_or_404(boda_id)
        
        # Check if already assigned
        existing = DeliveryAssignment.query.filter_by(order_id=order_id).first()
        if existing:
            existing.delivery_person_id = boda_id
            existing.status = 'assigned'
        else:
            assignment = DeliveryAssignment(
                order_id=order_id,
                delivery_person_id=boda_id,
                status='assigned'
            )
            db.session.add(assignment)
        
        # Update order status
        order.status = 'shipped'
        
        # Add tracking update
        tracking = OrderTracking(
            order_id=order_id,
            status='assigned_to_boda',
            location='Warehouse',
            notes=f'Assigned to boda rider: {boda.name} ({boda.phone})'
        )
        db.session.add(tracking)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order assigned to {boda.name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/boda/<int:boda_id>/update-location', methods=['POST'])
def update_boda_location(boda_id):
    """Boda rider updates their location (can be called via USSD or simple form)"""
    try:
        boda = DeliveryPerson.query.get_or_404(boda_id)
        location = request.json.get('location', '')
        order_id = request.json.get('order_id')
        
        boda.current_location = location
        
        if order_id:
            # Add tracking update for the order
            tracking = OrderTracking(
                order_id=order_id,
                status='in_transit',
                location=location,
                notes=f'Boda rider location: {location}'
            )
            db.session.add(tracking)
            
            # Update assignment status
            assignment = DeliveryAssignment.query.filter_by(
                order_id=order_id, 
                delivery_person_id=boda_id
            ).first()
            if assignment:
                assignment.status = 'in_transit'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Location updated'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/order/<int:order_id>/boda-status', methods=['POST'])
def update_boda_delivery_status(order_id):
    """Update delivery status (picked_up, delivered, etc.)"""
    try:
        status = request.json.get('status')
        notes = request.json.get('notes', '')
        boda_id = request.json.get('boda_id')
        
        order = Order.query.get_or_404(order_id)
        
        # Add tracking update
        tracking = OrderTracking(
            order_id=order_id,
            status=status,
            location=order.delivery_address,
            notes=notes
        )
        db.session.add(tracking)
        
        # Update order status based on boda status
        status_map = {
            'picked_up': 'shipped',
            'in_transit': 'in_transit', 
            'delivered': 'delivered'
        }
        
        if status in status_map:
            order.status = status_map[status]
            if status == 'delivered':
                order.actual_delivery = datetime.utcnow()
        
        # Update assignment status
        if boda_id:
            assignment = DeliveryAssignment.query.filter_by(
                order_id=order_id,
                delivery_person_id=boda_id
            ).first()
            if assignment:
                assignment.status = status
                if status == 'delivered':
                    assignment.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Status updated to {status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/boda/simple-update/<int:boda_id>')
def boda_simple_update(boda_id):
    """Simple page for boda riders to update status (works on basic phones)"""
    boda = DeliveryPerson.query.get_or_404(boda_id)
    
    # Get current assignments
    current_assignments = DeliveryAssignment.query.filter_by(
        delivery_person_id=boda_id,
        status='assigned'
    ).all()
    
    return render_template('boda_simple_update.html',
                         boda=boda,
                         assignments=current_assignments)

@app.route('/api/boda/simple-update', methods=['POST'])
def boda_simple_update_api():
    """Simple API for boda status updates"""
    try:
        boda_id = request.form.get('boda_id')
        assignment_id = request.form.get('assignment_id')
        status = request.form.get('status')
        location = request.form.get('location', '')
        
        boda = DeliveryPerson.query.get_or_404(boda_id)
        assignment = DeliveryAssignment.query.get_or_404(assignment_id)
        
        # Update boda location
        if location:
            boda.current_location = location
        
        # Update assignment and order status
        assignment.status = status
        
        # Add tracking update
        tracking = OrderTracking(
            order_id=assignment.order_id,
            status=status,
            location=location or boda.current_location,
            notes=f'Boda: {boda.name}'
        )
        db.session.add(tracking)
        
        # Update order status
        order = assignment.order
        if status == 'picked_up':
            order.status = 'shipped'
        elif status == 'delivered':
            order.status = 'delivered'
            order.actual_delivery = datetime.utcnow()
            assignment.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Status updated successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# Simple delivery person management
@app.route('/admin/boda-riders')
@admin_required
def boda_riders():
    """Manage boda riders"""
    user = get_current_user()
    riders = DeliveryPerson.query.all()
    
    return render_template('boda_riders.html',
                         user=user,
                         riders=riders)

@app.route('/admin/add-boda', methods=['POST'])
@admin_required
def add_boda_rider():
    """Add new boda rider"""
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        vehicle_type = request.form.get('vehicle_type', 'motorcycle')
        
        # Check if phone exists
        existing = DeliveryPerson.query.filter_by(phone=phone).first()
        if existing:
            flash('Boda rider with this phone already exists!', 'danger')
            return redirect(url_for('boda_riders'))
        
        rider = DeliveryPerson(
            name=name,
            phone=phone,
            vehicle_type=vehicle_type,
            is_active=True
        )
        
        db.session.add(rider)
        db.session.commit()
        
        flash('Boda rider added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding boda rider: {str(e)}', 'danger')
    
    return redirect(url_for('boda_riders'))

# ==================== DELIVERY CONFIRMATION ROUTES ====================

@app.route('/order/<int:order_id>/delivery-confirmation', methods=['GET', 'POST'])
@login_required
def delivery_confirmation(order_id):
    """Delivery confirmation page for buyers"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user owns the order
    if order.user_id != session['user_id']:
        flash('You are not authorized to confirm delivery for this order.', 'error')
        return redirect(url_for('home'))
    
    # Check if order is in a state that can be confirmed
    if order.status not in ['shipped', 'delivered']:
        flash('This order is not ready for delivery confirmation.', 'error')
        return redirect(url_for('order_details', order_id=order_id))
    
    if request.method == 'POST':
        try:
            confirmation_type = request.form.get('confirmation_type')
            
            if confirmation_type == 'success':
                # Successful delivery confirmation
                order.status = 'completed'
                order.delivery_confirmed_at = datetime.utcnow()
                order.delivery_confirmed_by = session['user_id']
                order.buyer_rating = int(request.form.get('rating', 5))
                order.buyer_feedback = request.form.get('feedback', '')
                order.delivery_notes = request.form.get('delivery_notes', '')
                
                # Handle file upload
                if 'delivery_proof' in request.files:
                    file = request.files['delivery_proof']
                    if file and file.filename != '' and allowed_file(file.filename):
                        # Create uploads directory if it doesn't exist
                        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                        
                        filename = secure_filename(f"proof_{order_id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(file_path)
                        order.delivery_proof = file_path
                
                db.session.commit()
                flash('✅ Delivery confirmed successfully! Thank you for your feedback.', 'success')
                
            elif confirmation_type == 'issue':
                # Report delivery issue
                order.issues_reported = True
                order.issue_description = request.form.get('issue_description', '')
                order.status = 'issue_reported'
                db.session.commit()
                
                flash('⚠️ Issue reported successfully. Our support team will contact you shortly.', 'warning')
            
            return redirect(url_for('order_details', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error processing your confirmation. Please try again.', 'error')
            print(f"Error in delivery confirmation: {e}")
    
    return render_template('delivery_confirmation.html', order=order)

@app.route('/admin/orders/<int:order_id>/mark-shipped', methods=['POST'])
@login_required
def mark_order_shipped(order_id):
    """Admin marks order as shipped"""
    if not is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    order.status = 'shipped'
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Order #{order_id} marked as shipped.', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/<int:order_id>/resolve-issue', methods=['POST'])
@login_required
def resolve_order_issue(order_id):
    """Admin resolves order issues"""
    if not is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    resolution = request.form.get('resolution', '')
    admin_notes = request.form.get('admin_notes', '')
    
    order.issues_reported = False
    order.status = 'resolved'
    if not order.delivery_notes:
        order.delivery_notes = ''
    order.delivery_notes += f"\n\nAdmin Resolution ({datetime.utcnow().strftime('%Y-%m-%d')}): {resolution}\nNotes: {admin_notes}"
    db.session.commit()
    
    flash('Order issue resolved successfully.', 'success')
    return redirect(url_for('admin_orders_management'))



# ==================== SELLER SUBSCRIPTION ROUTES ====================

@app.route('/seller/subscription')
@login_required
def seller_subscription():
    user = get_current_user()
    if user.user_type != 'seller':
        flash('This page is for sellers only.', 'danger')
        return redirect(url_for('products'))
    
    plans = [
        {
            'id': 1,
            'name': 'Starter Plan',
            'tier': 'starter',
            'price': 50000,
            'duration': 'monthly',
            'features': 'Up to 20 products\nBasic store analytics\nEmail support\nUCU campus reach\nMobile money payments'
        },
        {
            'id': 2,
            'name': 'Business Plan',
            'tier': 'business',
            'price': 120000,
            'duration': 'quarterly',
            'features': 'Up to 100 products\nAdvanced analytics\nPriority support\nMukono area coverage\nCustom store URL\nBank transfer payments'
        },
        {
            'id': 3,
            'name': 'Enterprise Plan',
            'tier': 'enterprise',
            'price': 400000,
            'duration': 'yearly',
            'features': 'Unlimited products\nPremium analytics\n24/7 phone support\nRegional coverage\nAPI access\nDedicated account manager\nMultiple payment options'
        }
    ]
    
    has_subscription = has_active_subscription(user)
    
    return render_template('seller_subscription.html', 
                         plans=plans, 
                         user=user, 
                         has_subscription=has_subscription)

@app.route('/seller/payment/<int:plan_id>')
@login_required
def seller_payment(plan_id):
    user = get_current_user()
    if user.user_type != 'seller':
        flash('This page is for sellers only.', 'danger')
        return redirect(url_for('products'))
    
    plans = {
        1: {'id': 1, 'name': 'Starter Plan', 'tier': 'starter', 'price': 50000, 'duration': 'monthly'},
        2: {'id': 2, 'name': 'Business Plan', 'tier': 'business', 'price': 120000, 'duration': 'quarterly'},
        3: {'id': 3, 'name': 'Enterprise Plan', 'tier': 'enterprise', 'price': 400000, 'duration': 'yearly'}
    }
    
    plan = plans.get(plan_id)
    if not plan:
        flash('Invalid subscription plan.', 'danger')
        return redirect(url_for('seller_subscription'))
    
    return render_template('seller_payment.html', plan=plan, user=user)

@app.route('/process_payment/<int:plan_id>', methods=['POST'])
@login_required
def process_payment(plan_id):
    user = get_current_user()
    if user.user_type != 'seller':
        flash('This page is for sellers only.', 'danger')
        return redirect(url_for('products'))
    
    payment_method = request.form.get('payment_method')
    
    if not payment_method:
        flash('Please select a payment method.', 'danger')
        return redirect(url_for('seller_payment', plan_id=plan_id))
    
    plans = {
        1: {'tier': 'starter', 'duration_days': 30},
        2: {'tier': 'business', 'duration_days': 90},
        3: {'tier': 'enterprise', 'duration_days': 365}
    }
    
    plan = plans.get(plan_id)
    if not plan:
        flash('Invalid subscription plan.', 'danger')
        return redirect(url_for('seller_subscription'))
    
    try:
        user.subscription_tier = plan['tier']
        user.subscription_expiry = datetime.utcnow() + timedelta(days=plan['duration_days'])
        
        db.session.commit()
        
        flash(f'Subscription activated successfully! You are now on the {plan["tier"].title()} plan. Welcome to Seller Hub!', 'success')
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        db.session.rollback()
        flash('Error processing payment. Please try again.', 'danger')
        return redirect(url_for('seller_payment', plan_id=plan_id))


@app.route('/seller/orders')
@login_required
def seller_orders():
    """Redirect seller orders to main orders page"""
    user = get_current_user()
    
    if user.user_type != 'seller' or not has_active_subscription(user):
        flash('Please subscribe to a plan to view orders.', 'info')
        return redirect(url_for('seller_subscription'))
    
    # Redirect to main orders page which shows seller-specific orders
    return redirect(url_for('user_orders'))

    

def send_order_notifications(order, order_items):
    """
    Send notifications to admin and sellers about the new order
    In a real application, this would send emails, SMS, or push notifications
    """
    try:
        # Get admin users
        admin_users = User.query.filter_by(user_type='admin').all()
        
        # Get unique sellers from order items
        seller_ids = set(item.seller_id for item in order_items)
        sellers = User.query.filter(User.id.in_(seller_ids)).all()
        
        # In a real app, you would:
        # 1. Send email to admin
        # 2. Send email to each seller
        # 3. Send SMS/WhatsApp notifications
        # 4. Create in-app notifications
        
        print(f"📦 New Order #{order.id} placed by {order.user.fullname}")
        print(f"💰 Total: ₦{order.total_amount:,.0f}")
        print(f"👥 Notifying {len(admin_users)} admin(s) and {len(sellers)} seller(s)")
        
        # You can implement actual email sending here
        # For now, we'll just log it
        for seller in sellers:
            seller_items = [item for item in order_items if item.seller_id == seller.id]
            total_seller_amount = sum(item.quantity * item.price for item in seller_items)
            print(f"   📧 Seller {seller.business_name}: {len(seller_items)} items, Total: ₦{total_seller_amount:,.0f}")
            
    except Exception as e:
        print(f"Error sending notifications: {str(e)}")



        

# ==================== API ROUTES ====================
@app.route('/wishlist')
@login_required
def wishlist():
    user = get_current_user()
    
    # Only buyers can access wishlist
    if user.user_type != 'buyer':
        flash('Wishlist is only available for buyers.', 'info')
        return redirect(url_for('products'))
    
    from sqlalchemy.orm import joinedload
    
    # Get wishlist items with product details
    wishlist_items = db.session.query(Wishlist, Product).\
        join(Product, Wishlist.product_id == Product.id).\
        options(joinedload(Product.seller)).\
        filter(Wishlist.user_id == user.id).\
        order_by(Wishlist.created_at.desc()).\
        all()
    
    # Calculate total value
    total_value = sum(product.price for _, product in wishlist_items)
    
    return render_template('wishlist.html', 
                         wishlist_items=wishlist_items,
                         user=user,
                         total_value=total_value)



@app.route('/api/wishlist/toggle', methods=['POST'])
@login_required
def toggle_wishlist():
    """Toggle product in wishlist - add if not present, remove if present"""
    user = get_current_user()
    data = request.get_json()
    product_id = data.get('product_id')
    
    try:
        # Check if product exists and is active
        product = Product.query.filter_by(id=product_id, is_active=True).first()
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})
        
        # Check if already in wishlist
        existing = Wishlist.query.filter_by(user_id=user.id, product_id=product_id).first()
        
        if existing:
            # Remove from wishlist
            db.session.delete(existing)
            action = 'removed'
            in_wishlist = False
        else:
            # Add to wishlist
            wishlist_item = Wishlist(user_id=user.id, product_id=product_id)
            db.session.add(wishlist_item)
            action = 'added'
            in_wishlist = True
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Product {action} from wishlist',
            'in_wishlist': in_wishlist,
            'action': action
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling wishlist: {e}")
        return jsonify({'success': False, 'message': 'Error updating wishlist'})


@app.route('/api/wishlist/remove', methods=['POST'])
@login_required
def remove_from_wishlist():
    user = get_current_user()
    data = request.get_json()
    product_id = data.get('product_id')
    
    try:
        wishlist_item = Wishlist.query.filter_by(user_id=user.id, product_id=product_id).first()
        if wishlist_item:
            db.session.delete(wishlist_item)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Removed from wishlist'})
        else:
            return jsonify({'success': False, 'message': 'Item not found in wishlist'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error removing from wishlist: {e}")
        return jsonify({'success': False, 'message': 'Error removing from wishlist'})

@app.route('/api/wishlist/clear', methods=['POST'])
@login_required
def clear_wishlist():
    user = get_current_user()
    
    try:
        # Delete all wishlist items for this user
        Wishlist.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Wishlist cleared successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing wishlist: {e}")
        return jsonify({'success': False, 'message': 'Error clearing wishlist'})



@app.route('/api/wishlist/status')
@login_required
def get_wishlist_status():
    """Get wishlist status for multiple products"""
    user = get_current_user()
    product_ids = request.args.getlist('product_ids[]')
    
    try:
        wishlist_items = Wishlist.query.filter_by(user_id=user.id).filter(
            Wishlist.product_id.in_(product_ids)
        ).all()
        
        wishlist_ids = [item.product_id for item in wishlist_items]
        
        return jsonify({
            'success': True,
            'wishlist_ids': wishlist_ids
        })
        
    except Exception as e:
        print(f"Error getting wishlist status: {e}")
        return jsonify({'success': False, 'wishlist_ids': []})
    
    
# ==================== ADDITIONAL ROUTES ====================

@app.route('/delivery/tracking')
@login_required
def delivery_tracking():
    return render_template('delivery_tracking.html')



def get_seller_analytics_data(seller_id):
    """Get real analytics data for the seller with proper line chart data"""
    try:
        # Total revenue from completed orders
        total_revenue = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed'
        ).scalar() or 0

        # Total orders for this seller
        total_orders = db.session.query(
            db.func.count(db.distinct(Order.id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id
        ).scalar() or 0

        # Total products sold
        products_sold = db.session.query(
            db.func.sum(OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed'
        ).scalar() or 0

        # Store rating from reviews
        store_rating_result = db.session.query(
            db.func.avg(Review.rating)
        ).join(Product).filter(
            Product.seller_id == seller_id
        ).scalar()
        store_rating = float(store_rating_result) if store_rating_result else 0

        # Recent orders (last 10)
        recent_orders = db.session.query(Order).join(OrderItem).filter(
            OrderItem.seller_id == seller_id
        ).order_by(Order.created_at.desc()).limit(10).all()

        # Sales by category (for pie chart)
        category_sales_result = db.session.query(
            Product.category,
            db.func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(OrderItem, Product.id == OrderItem.product_id
        ).join(Order).filter(
            Product.seller_id == seller_id,
            Order.status == 'completed'
        ).group_by(Product.category).all()
        
        # Convert to safe format
        category_sales = []
        for category, revenue in category_sales_result:
            category_sales.append({
                'category': category or 'Uncategorized',
                'revenue': float(revenue) if revenue else 0
            })

        # Top products by sales
        top_products_result = db.session.query(
            Product.name,
            db.func.sum(OrderItem.quantity).label('total_sold'),
            db.func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(OrderItem, Product.id == OrderItem.product_id
        ).join(Order).filter(
            Product.seller_id == seller_id,
            Order.status == 'completed'
        ).group_by(Product.id, Product.name
        ).order_by(db.desc('total_sold')).limit(5).all()
        
        # Convert to safe format
        top_products = []
        for name, total_sold, revenue in top_products_result:
            top_products.append({
                'name': name or 'Unknown Product',
                'total_sold': total_sold or 0,
                'revenue': float(revenue) if revenue else 0
            })

        # Order status distribution
        status_distribution_result = db.session.query(
            Order.status,
            db.func.count(db.distinct(Order.id)).label('count')
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id
        ).group_by(Order.status).all()
        
        # Convert to safe format
        status_distribution = []
        for status, count in status_distribution_result:
            status_distribution.append({
                'status': status or 'unknown',
                'count': count or 0
            })

        # Revenue by date for line chart (last 30 days with proper formatting)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        revenue_by_date_result = db.session.query(
            db.func.date(Order.created_at).label('date'),
            db.func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= thirty_days_ago
        ).group_by(db.func.date(Order.created_at)
        ).order_by('date').all()

        # Prepare line chart data
        line_chart_labels = []
        line_chart_data = []
        
        # Create a complete date range for the last 30 days
        date_range = []
        for i in range(30):
            date = (datetime.utcnow() - timedelta(days=29-i)).date()
            date_range.append(date)
        
        # Convert query results to dictionary for easy lookup
        revenue_dict = {}
        for item in revenue_by_date_result:
            if item.date:
                date_str = str(item.date)
                revenue_dict[date_str] = float(item.revenue) if item.revenue else 0
        
        # Build the line chart data with all dates
        for date in date_range:
            date_str = str(date)
            line_chart_labels.append(date.strftime('%b %d'))
            line_chart_data.append(revenue_dict.get(date_str, 0))

        # Calculate growth percentages (last 7 days vs previous 7 days)
        current_week_start = datetime.utcnow() - timedelta(days=7)
        previous_week_start = datetime.utcnow() - timedelta(days=14)
        
        # Current week revenue
        current_week_revenue = db.session.query(
            db.func.sum(OrderItem.quantity * OrderItem.price)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= current_week_start
        ).scalar() or 0

        # Previous week revenue
        previous_week_revenue = db.session.query(
            db.func.sum(OrderItem.quantity * OrderItem.price)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= previous_week_start,
            Order.created_at < current_week_start
        ).scalar() or 0

        # Calculate percentage changes
        revenue_change = 0
        if previous_week_revenue > 0:
            revenue_change = ((current_week_revenue - previous_week_revenue) / previous_week_revenue) * 100

        # Orders change
        current_week_orders = db.session.query(
            db.func.count(db.distinct(Order.id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= current_week_start
        ).scalar() or 0

        previous_week_orders = db.session.query(
            db.func.count(db.distinct(Order.id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= previous_week_start,
            Order.created_at < current_week_start
        ).scalar() or 0

        orders_change = 0
        if previous_week_orders > 0:
            orders_change = ((current_week_orders - previous_week_orders) / previous_week_orders) * 100

        # Reviews count
        reviews_count = db.session.query(Review).join(Product).filter(
            Product.seller_id == seller_id
        ).count()

        return {
            'total_revenue': float(total_revenue),
            'total_orders': int(total_orders),
            'products_sold': int(products_sold),
            'store_rating': float(store_rating),
            'reviews_count': int(reviews_count),
            'revenue_change': float(round(revenue_change, 1)),
            'orders_change': float(round(orders_change, 1)),
            'products_change': 0,  # You can implement similar logic for products
            'recent_orders': recent_orders or [],
            'category_sales': category_sales or [],
            'top_products': top_products or [],
            'status_distribution': status_distribution or [],
            'line_chart_labels': line_chart_labels or [],
            'line_chart_data': line_chart_data or [],
            'current_week_revenue': float(current_week_revenue)
        }

    except Exception as e:
        print(f"Error getting analytics data: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Return empty line chart data with safe defaults
        date_range = []
        for i in range(30):
            date = (datetime.utcnow() - timedelta(days=29-i)).date()
            date_range.append(date.strftime('%b %d'))
        
        return {
            'total_revenue': 0,
            'total_orders': 0,
            'products_sold': 0,
            'store_rating': 0,
            'reviews_count': 0,
            'revenue_change': 0,
            'orders_change': 0,
            'products_change': 0,
            'recent_orders': [],
            'category_sales': [],
            'top_products': [],
            'status_distribution': [],
            'line_chart_labels': date_range,
            'line_chart_data': [0] * 30,
            'current_week_revenue': 0
        }

def get_seller_analytics_data(seller_id):
    """Get real analytics data for the seller"""
    try:
        # Total revenue from completed orders
        total_revenue = db.session.query(
            db.func.sum(OrderItem.price * OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed'
        ).scalar() or 0

        # Total orders for this seller
        total_orders = db.session.query(
            db.func.count(db.distinct(Order.id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id
        ).scalar() or 0

        # Total products sold
        products_sold = db.session.query(
            db.func.sum(OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed'
        ).scalar() or 0

        # Store rating from reviews
        store_rating = db.session.query(
            db.func.avg(Review.rating)
        ).join(Product).filter(
            Product.seller_id == seller_id
        ).scalar() or 0

        # Recent orders (last 10)
        recent_orders = db.session.query(Order).join(OrderItem).filter(
            OrderItem.seller_id == seller_id
        ).order_by(Order.created_at.desc()).limit(10).all()

        # Sales by category
        category_sales = db.session.query(
            Product.category,
            db.func.sum(OrderItem.quantity * OrderItem.price).label('revenue'),
            db.func.sum(OrderItem.quantity).label('quantity')
        ).join(OrderItem, Product.id == OrderItem.product_id
        ).join(Order).filter(
            Product.seller_id == seller_id,
            Order.status == 'completed'
        ).group_by(Product.category).all()

        # Top products by sales
        top_products = db.session.query(
            Product.name,
            db.func.sum(OrderItem.quantity).label('total_sold'),
            db.func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(OrderItem, Product.id == OrderItem.product_id
        ).join(Order).filter(
            Product.seller_id == seller_id,
            Order.status == 'completed'
        ).group_by(Product.id, Product.name
        ).order_by(db.desc('total_sold')).limit(5).all()

        # Order status distribution
        status_distribution = db.session.query(
            Order.status,
            db.func.count(db.distinct(Order.id)).label('count')
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id
        ).group_by(Order.status).all()

        # Revenue by date (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        revenue_by_date = db.session.query(
            db.func.date(Order.created_at).label('date'),
            db.func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= thirty_days_ago
        ).group_by(db.func.date(Order.created_at)
        ).order_by('date').all()

        # Calculate changes (last 30 days vs previous 30 days)
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        
        # Current period revenue
        current_period_revenue = db.session.query(
            db.func.sum(OrderItem.quantity * OrderItem.price)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= thirty_days_ago
        ).scalar() or 0

        # Previous period revenue
        previous_period_revenue = db.session.query(
            db.func.sum(OrderItem.quantity * OrderItem.price)
        ).join(Order).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= sixty_days_ago,
            Order.created_at < thirty_days_ago
        ).scalar() or 0

        # Calculate percentage changes
        revenue_change = 0
        if previous_period_revenue > 0:
            revenue_change = ((current_period_revenue - previous_period_revenue) / previous_period_revenue) * 100

        # Similar calculations for orders and products
        current_period_orders = db.session.query(
            db.func.count(db.distinct(Order.id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= thirty_days_ago
        ).scalar() or 0

        previous_period_orders = db.session.query(
            db.func.count(db.distinct(Order.id))
        ).join(OrderItem).filter(
            OrderItem.seller_id == seller_id,
            Order.status == 'completed',
            Order.created_at >= sixty_days_ago,
            Order.created_at < thirty_days_ago
        ).scalar() or 0

        orders_change = 0
        if previous_period_orders > 0:
            orders_change = ((current_period_orders - previous_period_orders) / previous_period_orders) * 100

        return {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'products_sold': products_sold,
            'store_rating': float(store_rating) if store_rating else 0,
            'reviews_count': Review.query.join(Product).filter(Product.seller_id == seller_id).count(),
            'revenue_change': round(revenue_change, 1),
            'orders_change': round(orders_change, 1),
            'products_change': 0,  # You can implement similar logic for products
            'recent_orders': recent_orders,
            'category_sales': category_sales,
            'top_products': top_products,
            'status_distribution': status_distribution,
            'revenue_by_date': revenue_by_date
        }

    except Exception as e:
        print(f"Error getting analytics data: {e}")
        return {
            'total_revenue': 0,
            'total_orders': 0,
            'products_sold': 0,
            'store_rating': 0,
            'reviews_count': 0,
            'revenue_change': 0,
            'orders_change': 0,
            'products_change': 0,
            'recent_orders': [],
            'category_sales': [],
            'top_products': [],
            'status_distribution': [],
            'revenue_by_date': []
        }


@app.route('/store_settings')
@login_required
def store_settings():
    user = get_current_user()
    if user.user_type != 'seller' or not has_active_subscription(user):
        flash('Please subscribe to a plan to access store settings.', 'info')
        return redirect(url_for('seller_subscription'))
    return render_template('store_settings.html')



class EmailVerification(db.Model):
    __tablename__ = 'email_verifications'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

def send_verification_email(email, token):
    """Send verification email to Gmail address"""
    try:
        # Email configuration - you'll need to set up SMTP
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = "your-app@gmail.com"  # Your app's Gmail
        password = "your-app-password"  # Use App Password
        
        # Create verification link
        verification_link = f"http://yourdomain.com/verify-email/{token}"
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify Your Gmail for ShopMax"
        message["From"] = sender_email
        message["To"] = email
        
        # Create HTML content
        html = f"""
        <html>
          <body>
            <h2>Welcome to ShopMax!</h2>
            <p>Please verify your Gmail address to complete your registration.</p>
            <p><a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px;">Verify Email</a></p>
            <p>Or copy this link: {verification_link}</p>
            <p>This link will expire in 1 hour.</p>
          </body>
        </html>
        """
        
        # Add HTML to message
        message.attach(MIMEText(html, "html"))
        
        # Send email
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def is_gmail(email):
    """Check if email is a Gmail address"""
    return email.lower().endswith('@gmail.com')

def generate_verification_token():
    return secrets.token_urlsafe(32)




def check_and_create_tables():
    """Check and create missing tables only"""
    with app.app_context():
        try:
            from sqlalchemy import inspect, text
            
            # Check if email_verifications table exists
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'email_verifications' not in existing_tables:
                print("🔄 Creating email_verifications table...")
                db.create_all()
            else:
                print("✅ email_verifications table already exists")
                
        except Exception as e:
            print(f"❌ Error checking tables: {e}")




# ==================== FOOTER ROUTES ====================

@app.route('/about-us')
def about_us():
    """About Us page"""
    return render_template('about_us.html')

@app.route('/careers')
def careers():
    """Careers page"""
    return render_template('careers.html')

@app.route('/terms-of-service')
def terms_of_service():
    """Terms of Service page"""
    return render_template('terms_of_service.html')

@app.route('/privacy-policy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy_policy.html')

@app.route('/cookie-policy')
def cookie_policy():
    """Cookie Policy page"""
    return render_template('cookie_policy.html')

@app.route('/help-center')
def help_center():
    """Help Center page"""
    return render_template('help_center.html')

@app.route('/contact-us')
def contact_us():
    """Contact Us page"""
    return render_template('contact_us.html')

@app.route('/report-issue')
def report_issue():
    """Report Issue page"""
    return render_template('report_issue.html')

@app.route('/safety-tips')
def safety_tips():
    """Safety Tips page"""
    return render_template('safety_tips.html')

@app.route('/faqs')
def faqs():
    """FAQs page"""
    return render_template('faqs.html')

@app.route('/how-to-buy')
def how_to_buy():
    """How to Buy guide"""
    return render_template('how_to_buy.html')

@app.route('/delivery-info')
def delivery_info():
    """Delivery Information page"""
    return render_template('delivery_info.html')

@app.route('/buyer-protection')
def buyer_protection():
    """Buyer Protection page"""
    return render_template('buyer_protection.html')

@app.route('/payment-methods')
def payment_methods():
    """Payment Methods page"""
    return render_template('payment_methods.html')

@app.route('/seller-guidelines')
def seller_guidelines():
    """Seller Guidelines page"""
    return render_template('seller_guidelines.html')

@app.route('/pricing-fees')
def pricing_fees():
    """Pricing & Fees page"""
    return render_template('pricing_fees.html')

@app.route('/success-stories')
def success_stories():
    """Success Stories page"""
    return render_template('success_stories.html')

@app.route('/seller-resources')
def seller_resources():
    """Seller Resources page"""
    return render_template('seller_resources.html')


@app.route('/under-construction')
def under_construction():
    """Generic placeholder page used while content is being authored.

    Templates: templates/under_construction.html
    Used by footer links for pages that don't yet have a full template.
    """
    return render_template('under_construction.html')




# Add these routes to your Flask app
# ==================== ADMIN REPORTS API ROUTES ====================

@app.route('/api/reports/quick-stats')
@admin_required
def get_quick_stats():
    """Get real quick statistics for admin dashboard"""
    try:
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Total revenue (all completed orders)
        total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
            Order.status == 'completed'
        ).scalar() or 0
        
        # Recent orders (last 7 days)
        recent_orders = Order.query.filter(
            Order.created_at >= week_ago,
            Order.status == 'completed'
        ).count()
        
        # New customers (last 30 days)
        new_customers = User.query.filter(
            User.created_at >= month_ago,
            User.user_type == 'buyer'
        ).count()
        
        # Active sellers (sellers with active products)
        active_sellers = db.session.query(func.count(func.distinct(Product.seller_id))).filter(
            Product.is_active == True
        ).scalar() or 0
        
        return jsonify({
            'total_revenue': float(total_revenue),
            'recent_orders': recent_orders,
            'new_customers': new_customers,
            'active_sellers': active_sellers
        })
        
    except Exception as e:
        print(f"Error getting quick stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500



@app.route('/api/reports/sales-data')
@admin_required
def get_sales_data():
    """Get sales data for charts with proper date handling"""
    try:
        days = int(request.args.get('days', 7))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query sales data by date
        sales_data = db.session.query(
            func.date(Order.created_at).label('date'),
            func.sum(Order.total_amount).label('total_sales'),
            func.count(Order.id).label('order_count')
        ).filter(
            Order.created_at >= start_date,
            Order.status == 'completed'
        ).group_by(func.date(Order.created_at)).order_by('date').all()
        
        # Create complete date range to fill missing dates
        date_range = []
        current_date = start_date.date()
        today = datetime.utcnow().date()
        
        while current_date <= today:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # Convert query results to dictionary for easy lookup
        sales_dict = {}
        for data in sales_data:
            if data.date:
                date_str = str(data.date)
                sales_dict[date_str] = {
                    'sales': float(data.total_sales or 0),
                    'orders': data.order_count or 0
                }
        
        # Build complete data arrays
        labels = []
        sales_amounts = []
        order_counts = []
        
        for date in date_range:
            date_str = str(date)
            labels.append(date.strftime('%b %d'))
            if date_str in sales_dict:
                sales_amounts.append(sales_dict[date_str]['sales'])
                order_counts.append(sales_dict[date_str]['orders'])
            else:
                sales_amounts.append(0)
                order_counts.append(0)
        
        return jsonify({
            'labels': labels,
            'sales': sales_amounts,
            'orders': order_counts
        })
        
    except Exception as e:
        print(f"Error getting sales data: {e}")
        return jsonify({'error': 'Failed to fetch sales data'}), 500




@app.route('/api/reports/top-products')
@admin_required
def get_top_products():
    """Get top products by sales"""
    try:
        top_products = db.session.query(
            Product.name,
            func.sum(OrderItem.quantity).label('total_sold'),
            func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        ).join(OrderItem, Product.id == OrderItem.product_id
        ).join(Order).filter(
            Order.status == 'completed'
        ).group_by(Product.id, Product.name
        ).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
        
        products_data = []
        for product in top_products:
            products_data.append({
                'name': product.name or 'Unknown Product',
                'sales': product.total_sold or 0,
                'revenue': float(product.revenue or 0)
            })
        
        return jsonify(products_data)
        
    except Exception as e:
        print(f"Error getting top products: {e}")
        return jsonify({'error': 'Failed to fetch top products'}), 500

@app.route('/api/reports/sales-details')
@admin_required
def get_sales_details():
    """Get detailed sales data for the table"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Query orders with related data
        orders_query = Order.query.options(
            db.joinedload(Order.user),
            db.joinedload(Order.order_items)
        ).order_by(Order.created_at.desc())
        
        orders = orders_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        orders_data = []
        for order in orders.items:
            # Count items in this order
            items_count = len(order.order_items)
            
            orders_data.append({
                'id': order.id,
                'customer_name': order.user.fullname if order.user else 'Unknown',
                'date': order.created_at.strftime('%Y-%m-%d'),
                'amount': float(order.total_amount),
                'status': order.status,
                'payment_method': order.payment_method or 'Not specified',
                'items_count': items_count
            })
        
        return jsonify({
            'orders': orders_data,
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page
        })
        
    except Exception as e:
        print(f"Error getting sales details: {e}")
        return jsonify({'error': 'Failed to fetch sales details'}), 500

@app.route('/api/reports/user-analytics')
@admin_required
def get_user_analytics():
    """Get user analytics data for pie chart"""
    try:
        user_types = db.session.query(
            User.user_type,
            func.count(User.id).label('count')
        ).group_by(User.user_type).all()
        
        user_data = {
            'buyers': 0,
            'sellers': 0,
            'admins': 0
        }
        
        for user_type, count in user_types:
            if user_type == 'buyer':
                user_data['buyers'] = count
            elif user_type == 'seller':
                user_data['sellers'] = count
            elif user_type == 'admin':
                user_data['admins'] = count
        
        return jsonify(user_data)
        
    except Exception as e:
        print(f"Error getting user analytics: {e}")
        return jsonify({'error': 'Failed to fetch user analytics'}), 500

@app.route('/api/reports/order-status')
@admin_required
def get_order_status_distribution():
    """Get order status distribution for pie chart"""
    try:
        status_counts = db.session.query(
            Order.status,
            func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        
        # Format data for chart
        labels = []
        counts = []
        for status, count in status_counts:
            if status:  # Ensure status is not None
                labels.append(status.title())
                counts.append(count)
        
        # If no data, provide default structure
        if not labels:
            labels = ['No Orders']
            counts = [1]
        
        return jsonify({
            'labels': labels,
            'counts': counts
        })
        
    except Exception as e:
        print(f"Error getting order status distribution: {e}")
        return jsonify({'error': 'Failed to fetch order status data'}), 500

@app.route('/api/reports/recent-activity')
@admin_required
def get_recent_activity():
    """Get recent platform activity"""
    try:
        # Get recent orders (last 5)
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        
        # Get recent user registrations (last 5)
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        activities = []
        
        # Add order activities
        for order in recent_orders:
            activities.append({
                'type': 'order',
                'description': f'New order #{order.id} placed',
                'user_name': order.user.fullname if order.user else 'Unknown',
                'time': order.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        # Add user registration activities
        for user in recent_users:
            activities.append({
                'type': 'user',
                'description': f'New {user.user_type} registered: {user.fullname}',
                'user_name': user.fullname,
                'time': user.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        # Sort by time (newest first) and limit to 10
        activities.sort(key=lambda x: x['time'], reverse=True)
        activities = activities[:10]
        
        return jsonify({'activities': activities})
        
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return jsonify({'error': 'Failed to fetch recent activity'}), 500

@app.route('/api/reports/generate-report')
@admin_required
def generate_report():
    """Generate and download report in CSV format"""
    try:
        report_type = request.args.get('type', 'sales')
        format_type = request.args.get('format', 'csv')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Build date filters
        filters = []
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            filters.append(Order.created_at >= start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            filters.append(Order.created_at <= end_date)
        
        if report_type == 'sales':
            orders = Order.query.filter(*filters).all()
            
            if format_type == 'csv':
                # Create CSV in memory
                output = BytesIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow(['Order ID', 'Customer', 'Date', 'Amount (UGX)', 'Status', 'Payment Method', 'Delivery Address'])
                
                # Write data
                for order in orders:
                    writer.writerow([
                        order.id,
                        order.user.fullname if order.user else 'Unknown',
                        order.created_at.strftime('%Y-%m-%d'),
                        order.total_amount,
                        order.status,
                        order.payment_method or 'Not specified',
                        order.delivery_address or 'Not specified'
                    ])
                
                output.seek(0)
                return send_file(
                    output,
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=f'sales_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
                )
        
        elif report_type == 'users':
            users = User.query.filter(*filters).all()
            
            if format_type == 'csv':
                output = BytesIO()
                writer = csv.writer(output)
                
                writer.writerow(['User ID', 'Name', 'Email', 'User Type', 'Phone', 'Location', 'Registration Date'])
                
                for user in users:
                    writer.writerow([
                        user.id,
                        user.fullname,
                        user.email,
                        user.user_type,
                        user.phone or 'Not specified',
                        user.location or 'Not specified',
                        user.created_at.strftime('%Y-%m-%d')
                    ])
                
                output.seek(0)
                return send_file(
                    output,
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=f'users_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
                )
        
        return jsonify({'error': 'Report type not implemented'}), 400
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'error': 'Failed to generate report'}), 500



# Add this route to handle multiple pages
@app.route('/page/<page_name>')
def dynamic_page(page_name):
    # Map page names to template files
    page_templates = {
        'how-to-buy': 'how_to_buy.html',
        'delivery-info': 'delivery_info.html',
        'buyer-protection': 'buyer_protection.html',
        # Add all other pages here
    }
    
    template_name = page_templates.get(page_name)
    if template_name:
        return render_template(template_name)
    else:
        return "Page not found", 404




@app.route('/register/buyer', methods=['GET', 'POST'])
def register_buyer():
    """Buyer registration route - single email field"""
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        location = request.form.get('location')
        delivery_address = request.form.get('delivery_address')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate email format
        if not is_valid_email(email):
            flash('Please use a valid email address. Gmail (user@gmail.com) or UCU student email (b00894@students.ucu.ac.ug)', 'danger')
            return render_template('register_buyer.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('This email is already registered. Please login instead.', 'danger')
            return render_template('register_buyer.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register_buyer.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register_buyer.html')
        
        try:
            new_user = User(
                fullname=fullname,
                email=email,
                phone=phone,
                location=location,
                delivery_address=delivery_address,
                password=generate_password_hash(password),
                user_type='buyer'
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['user_name'] = new_user.fullname
            session['user_type'] = new_user.user_type
            
            # Merge session cart with new user's cart after registration
            if hasattr(app, 'merge_session_cart_with_user'):
                merge_session_cart_with_user(new_user.id)
            
            # Determine user type for welcome message
            user_type = get_user_type_by_email(email)
            if user_type == 'ucu_student':
                flash('🎓 UCU student account created successfully! Welcome to ShopMax!', 'success')
            else:
                flash('✅ Account created successfully! Welcome to ShopMax!', 'success')
                
            # Check if there's a next URL (like checkout)
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            else:
                return redirect(url_for('products'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating buyer account: {e}")
            flash('Error creating account. Please try again.', 'danger')
    
    return render_template('register_buyer.html')







# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def inject_user():
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return dict(current_user=current_user)
    return dict(current_user=None)

@app.context_processor
def inject_cart_count():
    cart_count = 0
    if 'user_id' in session and session.get('user_type') == 'buyer':
        cart_count = Cart.query.filter_by(user_id=session['user_id']).count()
    return dict(cart_count=cart_count)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ==================== MAIN ====================
if __name__ == '__main__':
    # First check and create tables safely
  
    
    # Then initialize with sample data
    initialize_database()
    
    # Run the app
    app.run(debug=True)


    
