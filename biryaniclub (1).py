# Import necessary libraries and modules
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import json
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'ag3su65fiyv6i86i8eruijterie8teuitfwtu7d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biryani_club.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Models
class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    emoji = db.Column(db.String(10))
    in_stock = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    loyalty_points = db.Column(db.Integer, default=0)
    is_admin = db.Column(db.Boolean, default=False)
    is_delivery = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(15), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')
    coupon_code = db.Column(db.String(20))
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_delivery = db.Column(db.DateTime)

    def get_items(self):
        return json.loads(self.items_json) if self.items_json else []

# Menu data
MENU = {
    'Biryani': [
        {'name': 'Chicken Biryani', 'price': 299, 'description': 'Aromatic basmati rice with tender chicken', 'emoji': '🍛'},
        {'name': 'Mutton Biryani', 'price': 399, 'description': 'Premium mutton pieces with fragrant rice', 'emoji': '🍖'},
        {'name': 'Veg Biryani', 'price': 249, 'description': 'Mixed vegetables with saffron rice', 'emoji': '🥬'},
        {'name': 'Prawns Biryani', 'price': 349, 'description': 'Fresh prawns with coastal spices', 'emoji': '🦐'},
        {'name': 'Egg Biryani', 'price': 199, 'description': 'Boiled eggs with spiced rice', 'emoji': '🥚'}
    ],
    'Rolls & Snacks': [
        {'name': 'Chicken Roll', 'price': 149, 'description': 'Spicy chicken wrapped in soft paratha', 'emoji': '🌯'},
        {'name': 'Paneer Roll', 'price': 129, 'description': 'Cottage cheese with mint chutney', 'emoji': '🧀'},
        {'name': 'Seekh Kebab', 'price': 179, 'description': 'Grilled minced meat skewers', 'emoji': '🍢'},
        {'name': 'Samosa (2pcs)', 'price': 49, 'description': 'Crispy triangular pastries', 'emoji': '🥟'},
        {'name': 'Spring Roll', 'price': 89, 'description': 'Crispy vegetable rolls', 'emoji': '🥠'}
    ],
    'Beverages': [
        {'name': 'Lassi', 'price': 79, 'description': 'Traditional yogurt drink', 'emoji': '🥤'},
        {'name': 'Fresh Lime', 'price': 59, 'description': 'Refreshing lime water', 'emoji': '🍋'},
        {'name': 'Masala Chai', 'price': 39, 'description': 'Spiced Indian tea', 'emoji': '☕'},
        {'name': 'Cold Coffee', 'price': 99, 'description': 'Iced coffee with cream', 'emoji': '🧊'},
        {'name': 'Buttermilk', 'price': 69, 'description': 'Spiced yogurt drink', 'emoji': '🥛'}
    ]
}

# Store status (default to open)
store_status = {'open': True}

# Template context processor for current user
@app.context_processor
def inject_current_user():
    def get_current_user():
        if 'user_id' in session:
            return User.query.get(session['user_id'])
        return None
    return dict(get_current_user=get_current_user)

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_delivery:
            flash('Access denied. Delivery team privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Base HTML template with enhanced styling
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

    <style>
        :root {
            --primary: #ff6b35;
            --secondary: #f7931e;
            --success: #4ecdc4;
            --info: #667eea;
            --warning: #f093fb;
            --danger: #f5576c;
            --dark: #2c3e50;
            --gradient-1: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            --gradient-2: linear-gradient(135deg, #4ecdc4 0%, #38ef7d 100%);
            --gradient-3: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-4: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-5: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            --glass: rgba(255, 255, 255, 0.25);
            --glass-border: rgba(255, 255, 255, 0.18);
        }

        * { 
            font-family: 'Poppins', sans-serif; 
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #ff9a9e 75%, #fecfef 100%);
            background-attachment: fixed;
            min-height: 100vh;
        }

        .glass-effect {
            background: var(--glass);
            backdrop-filter: blur(15px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        }

        .navbar {
            background: var(--glass) !important;
            backdrop-filter: blur(20px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border-bottom: 1px solid var(--glass-border);
        }

        .navbar-brand {
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 2rem;
        }

        .nav-link {
            font-weight: 600;
            transition: all 0.3s ease;
            border-radius: 10px;
            margin: 0 5px;
        }

        .nav-link:hover {
            background: var(--glass);
            transform: translateY(-2px);
        }

        .card {
            border: none;
            border-radius: 25px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            transition: all 0.4s ease;
            background: var(--glass);
            backdrop-filter: blur(20px);
            overflow: hidden;
            border: 1px solid var(--glass-border);
        }

        .card:hover {
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 30px 60px rgba(0,0,0,0.2);
        }

        .btn {
            border-radius: 50px;
            padding: 12px 30px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            border: none;
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn-primary {
            background: var(--gradient-1);
            box-shadow: 0 8px 25px rgba(255, 107, 53, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(255, 107, 53, 0.4);
        }

        .btn-success {
            background: var(--gradient-2);
            box-shadow: 0 8px 25px rgba(78, 205, 196, 0.3);
        }

        .btn-info {
            background: var(--gradient-3);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .btn-warning {
            background: var(--gradient-4);
            box-shadow: 0 8px 25px rgba(240, 147, 251, 0.3);
        }

        .btn-dark {
            background: var(--gradient-5);
            box-shadow: 0 8px 25px rgba(44, 62, 80, 0.3);
        }

        .hero-section {
            background: var(--gradient-1);
            color: white;
            border-radius: 30px;
            padding: 100px 50px;
            margin: 30px 0;
            position: relative;
            overflow: hidden;
        }

        .hero-section::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: heroFloat 6s ease-in-out infinite;
        }

        @keyframes heroFloat {
            0%, 100% { transform: rotate(0deg); }
            50% { transform: rotate(180deg); }
        }

        .price-tag {
            background: var(--gradient-4);
            color: white;
            border-radius: 20px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 1.2rem;
            display: inline-block;
            transform: rotate(-10deg);
            box-shadow: 0 8px 25px rgba(245, 87, 108, 0.4);
            animation: wiggle 2s ease-in-out infinite;
        }

        @keyframes wiggle {
            0%, 100% { transform: rotate(-10deg); }
            50% { transform: rotate(-5deg) scale(1.05); }
        }

        .menu-item-card {
            border-radius: 25px;
            transition: all 0.4s ease;
            position: relative;
            overflow: hidden;
        }

        .menu-item-card:hover {
            transform: scale(1.08) rotate(2deg);
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }

        .item-emoji {
            font-size: 4rem;
            display: inline-block;
            animation: itemBounce 3s ease-in-out infinite;
        }

        @keyframes itemBounce {
            0%, 100% { transform: scale(1) rotate(0deg); }
            50% { transform: scale(1.1) rotate(5deg); }
        }

        .cart-count {
            background: var(--gradient-4) !important;
            animation: pulse 1.5s infinite;
            border: 3px solid white;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            70% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }

        .text-gradient {
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1050;
            min-width: 300px;
            border-radius: 15px;
            backdrop-filter: blur(20px);
        }

        .auth-form {
            max-width: 450px;
            margin: 50px auto;
            padding: 40px;
            background: var(--glass);
            backdrop-filter: blur(20px);
            border-radius: 25px;
            border: 1px solid var(--glass-border);
            box-shadow: 0 25px 50px rgba(0,0,0,0.2);
        }

        .form-control {
            background: rgba(255,255,255,0.1);
            border: 1px solid var(--glass-border);
            border-radius: 15px;
            padding: 15px 20px;
            color: white;
            font-weight: 500;
            backdrop-filter: blur(10px);
        }

        .form-control::placeholder {
            color: rgba(255,255,255,0.7);
        }

        .form-control:focus {
            background: rgba(255,255,255,0.2);
            border-color: var(--primary);
            box-shadow: 0 0 0 0.2rem rgba(255, 107, 53, 0.25);
            color: white;
        }

        .admin-panel, .delivery-panel {
            background: var(--gradient-5);
            border-radius: 25px;
            padding: 30px;
            margin: 20px 0;
            color: white;
        }

        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 1px;
        }

        .status-pending { background: var(--warning); }
        .status-preparing { background: var(--info); }
        .status-ready { background: var(--success); }
        .status-delivered { background: var(--dark); color: white; }

        .dashboard-card {
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            transition: all 0.3s ease;
        }

        .dashboard-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }

        .dashboard-icon {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 2rem;
            color: white;
        }

        .store-status-banner {
            padding: 15px;
            border-radius: 15px;
            text-align: center;
            font-weight: bold;
            margin-bottom: 30px;
            color: white;
        }

        .store-open {
            background: var(--gradient-2);
            box-shadow: 0 0 20px rgba(78, 205, 196, 0.4);
        }

        .store-closed {
            background: var(--gradient-4);
            box-shadow: 0 0 20px rgba(240, 147, 251, 0.4);
        }

    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-light sticky-top">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">
                <i class="fas fa-utensils me-2"></i>Biryani Club
            </a>

            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>

            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/"><i class="fas fa-home me-1"></i>Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/menu"><i class="fas fa-book me-1"></i>Menu</a>
                    </li>
                    {% if session.user_id %}
                        <li class="nav-item">
                            <a class="nav-link" href="/my-orders"><i class="fas fa-shopping-bag me-1"></i>My Orders</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/profile"><i class="fas fa-user me-1"></i>Profile</a>
                        </li>
                    {% endif %}
                </ul>

                <div class="d-flex align-items-center">
                    {% if session.user_id %}
                        {% if current_user and current_user.is_admin %}
                            <a href="/admin" class="btn btn-dark btn-sm me-2">
                                <i class="fas fa-shield-alt me-1"></i>Admin
                            </a>
                        {% endif %}
                        {% if current_user and current_user.is_delivery %}
                            <a href="/delivery" class="btn btn-info btn-sm me-2">
                                <i class="fas fa-truck me-1"></i>Delivery
                            </a>
                        {% endif %}
                        <button class="btn btn-outline-primary me-2" onclick="toggleCart()">
                            <i class="fas fa-shopping-cart me-1"></i>
                            Cart <span id="cart-count" class="badge cart-count">0</span>
                        </button>
                        <a href="/logout" class="btn btn-outline-danger">
                            <i class="fas fa-sign-out-alt me-1"></i>Logout
                        </a>
                    {% else %}
                        <button class="btn btn-outline-primary me-2" onclick="toggleCart()">
                            <i class="fas fa-shopping-cart me-1"></i>
                            Cart <span id="cart-count" class="badge cart-count">0</span>
                        </button>
                        <a href="/login" class="btn btn-primary me-2">
                            <i class="fas fa-sign-in-alt me-1"></i>Login
                        </a>
                        <a href="/signup" class="btn btn-outline-primary">
                            <i class="fas fa-user-plus me-1"></i>Sign Up
                        </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </nav>

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show notification" role="alert">
                    <i class="fas fa-{{ 'exclamation-triangle' if category == 'error' or category == 'danger' else 'check-circle' }} me-2"></i>
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <!-- Main Content -->
    <main>
        {{ content|safe }}
    </main>

    <!-- Cart Modal -->
    <div class="modal fade" id="cartModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content glass-effect">
                <div class="modal-header text-white" style="background: var(--gradient-1); border: none;">
                    <h5 class="modal-title"><i class="fas fa-shopping-cart me-2"></i>Your Cart</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="cart-items"></div>
                    <hr style="border-color: var(--glass-border);">
                    <div class="d-flex justify-content-between h5">
                        <span>Total: </span>
                        <span id="cart-total">₹0</span>
                    </div>
                </div>
                <div class="modal-footer" style="border: none;">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Continue Shopping</button>
                    <a href="/checkout" class="btn btn-primary" id="checkout-button">Proceed to Checkout</a>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    <script>
        let cart = JSON.parse(localStorage.getItem('cart') || '[]');
        const checkoutButton = document.getElementById('checkout-button');

        function updateCartCount() {
            const count = cart.reduce((sum, item) => sum + item.quantity, 0);
            document.getElementById('cart-count').textContent = count;
        }

        function addToCart(name, price, emoji) {
            const existingItem = cart.find(item => item.name === name);
            if (existingItem) {
                existingItem.quantity += 1;
            } else {
                cart.push({name, price, emoji, quantity: 1});
            }
            localStorage.setItem('cart', JSON.stringify(cart));
            updateCartCount();
            updateCartModal();
            showNotification(name + ' added to cart!', 'success');
        }

        function updateCartModal() {
            const cartItems = document.getElementById('cart-items');
            const cartTotal = document.getElementById('cart-total');

            if (cart.length === 0) {
                cartItems.innerHTML = '<p class="text-muted text-center">Your cart is empty</p>';
                cartTotal.textContent = '₹0';
                checkoutButton.classList.add('disabled');
                checkoutButton.removeAttribute('href');
                return;
            } else {
                checkoutButton.classList.remove('disabled');
                checkoutButton.setAttribute('href', '/checkout');
            }

            let html = '';
            let total = 0;

            cart.forEach((item, index) => {
                const itemTotal = item.price * item.quantity;
                total += itemTotal;
                html += `
                    <div class="d-flex justify-content-between align-items-center mb-3 p-3 rounded glass-effect">
                        <div>
                            <h6 class="mb-1">${item.emoji} ${item.name}</h6>
                            <small class="text-muted">₹${item.price} each</small>
                        </div>
                        <div class="d-flex align-items-center">
                            <button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${index}, -1)">-</button>
                            <span class="mx-3">${item.quantity}</span>
                            <button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${index}, 1)">+</button>
                            <div class="ms-3">
                                <strong>₹${itemTotal}</strong>
                                <button class="btn btn-sm btn-outline-danger ms-2" onclick="removeItem(${index})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });

            cartItems.innerHTML = html;
            cartTotal.textContent = '₹' + total;
        }

        function updateQuantity(index, change) {
            cart[index].quantity += change;
            if (cart[index].quantity <= 0) {
                cart.splice(index, 1);
            }
            localStorage.setItem('cart', JSON.stringify(cart));
            updateCartCount();
            updateCartModal();
        }

        function removeItem(index) {
            cart.splice(index, 1);
            localStorage.setItem('cart', JSON.stringify(cart));
            updateCartCount();
            updateCartModal();
        }

        function toggleCart() {
            updateCartModal();
            const cartModal = new bootstrap.Modal(document.getElementById('cartModal'));
            cartModal.show();
        }

        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} notification glass-effect`;
            notification.innerHTML = `
                <i class="fas fa-check-circle me-2"></i>${message}
                <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
            `;
            document.body.appendChild(notification);

            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 3000);
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            updateCartCount();
        });
    </script>

    {{ extra_scripts|safe }}
</body>
</html>
"""

# Authentication Routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        phone = data.get('phone')

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return jsonify({'success': False, 'error': 'Username already exists'}) if request.is_json else redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return jsonify({'success': False, 'error': 'Email already registered'}) if request.is_json else redirect(url_for('signup'))

        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            phone=phone
        )

        # Check for admin access
        if password == 'cupadmin':
            user.is_admin = True

        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username

        flash('Account created successfully!', 'success')
        return jsonify({'success': True}) if request.is_json else redirect(url_for('home'))

    content = """
<div class="container">
    <div class="auth-form">
        <div class="text-center mb-4">
            <div class="dashboard-icon mx-auto mb-3" style="background: var(--gradient-1);">
                <i class="fas fa-user-plus"></i>
            </div>
            <h2 class="fw-bold text-white">Join Biryani Club</h2>
            <p class="text-light">Create your account and start ordering!</p>
        </div>

        <form id="signup-form">
            <div class="mb-3">
                <input type="text" class="form-control" name="username" placeholder="Username" required>
            </div>
            <div class="mb-3">
                <input type="email" class="form-control" name="email" placeholder="Email Address" required>
            </div>
            <div class="mb-3">
                <input type="text" class="form-control" name="full_name" placeholder="Full Name" required>
            </div>
            <div class="mb-3">
                <input type="tel" class="form-control" name="phone" placeholder="Phone Number" required>
            </div>
            <div class="mb-4">
                <input type="password" class="form-control" name="password" placeholder="Password" required>
                <small class="text-light">Enter 'cupadmin' for admin access</small>
            </div>
            <button type="submit" class="btn btn-primary w-100 mb-3">
                <i class="fas fa-user-plus me-2"></i>Create Account
            </button>
        </form>

        <div class="text-center">
            <p class="text-light">Already have an account? 
                <a href="/login" class="text-warning fw-bold">Login here</a>
            </p>
        </div>
    </div>
</div>

<script>
document.getElementById('signup-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    fetch('/signup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/';
        } else {
            showNotification(data.error, 'danger');
        }
    })
    .catch(error => {
        showNotification('Error creating account', 'danger');
    });
});
</script>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="Sign Up - Biryani Club", 
                                content=content, 
                                extra_scripts="")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Welcome back!', 'success')
            return jsonify({'success': True}) if request.is_json else redirect(url_for('home'))
        else:
            flash('Invalid username or password!', 'danger')
            return jsonify({'success': False, 'error': 'Invalid credentials'}) if request.is_json else redirect(url_for('login'))

    content = """
<div class="container">
    <div class="auth-form">
        <div class="text-center mb-4">
            <div class="dashboard-icon mx-auto mb-3" style="background: var(--gradient-3);">
                <i class="fas fa-sign-in-alt"></i>
            </div>
            <h2 class="fw-bold text-white">Welcome Back</h2>
            <p class="text-light">Login to your Biryani Club account</p>
        </div>

        <form id="login-form">
            <div class="mb-3">
                <input type="text" class="form-control" name="username" placeholder="Username" required>
            </div>
            <div class="mb-4">
                <input type="password" class="form-control" name="password" placeholder="Password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100 mb-3">
                <i class="fas fa-sign-in-alt me-2"></i>Login
            </button>
        </form>

        <div class="text-center">
            <p class="text-light">Don't have an account? 
                <a href="/signup" class="text-warning fw-bold">Sign up here</a>
            </p>
        </div>
    </div>
</div>

<script>
document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/';
        } else {
            showNotification(data.error, 'danger');
        }
    })
    .catch(error => {
        showNotification('Login failed', 'danger');
    });
});
</script>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="Login - Biryani Club", 
                                content=content, 
                                extra_scripts="")

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/my-orders')
@login_required
def my_orders():
    user = User.query.get(session['user_id'])
    if not user:
        flash('Please log in to view your orders.', 'warning')
        return redirect(url_for('login'))
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    
    # Thank you messages for delivered orders
    thank_you_messages = [
        "Thank you for choosing Biryani Club! 🙏 Order again soon!",
        "We hope you enjoyed your meal! 😋 Come back for more deliciousness!",
        "Your satisfaction is our priority! 💖 See you again soon!",
        "Thanks for being our valued customer! 🌟 Order again anytime!",
        "We're grateful for your order! 🎉 Can't wait to serve you again!",
        "Hope the biryani was perfect! 🍛 Looking forward to your next order!",
        "Thank you for trusting us with your hunger! 😊 Order again soon!"
    ]

    content = f"""
<div class="container py-5">
    <div class="text-center mb-5">
        <h2 class="display-4 fw-bold text-gradient">My Orders 📦</h2>
        <p class="lead text-muted">Track your order history and current orders</p>
    </div>

    <div class="row">
        <div class="col-lg-8 mx-auto">
    """

    if orders:
        for order in orders:
            status_class = f"status-{order.status}"
            status_icons = {
                'pending': 'fas fa-clock',
                'preparing': 'fas fa-fire',
                'ready': 'fas fa-check-circle',
                'delivered': 'fas fa-truck'
            }
            
            # Show random thank you message for delivered orders
            thank_you_msg = ""
            if order.status == 'delivered':
                import random
                thank_you_msg = f'<div class="alert alert-success mt-3"><i class="fas fa-heart me-2"></i>{random.choice(thank_you_messages)}</div>'

            items_summary = ", ".join([f"{item['name']} x{item['quantity']}" for item in order.get_items()][:3])
            if len(order.get_items()) > 3:
                items_summary += "..."

            content += f"""
            <div class="card mb-4" id="order-{order.order_id}">
                <div class="card-header d-flex justify-content-between align-items-center" style="background: var(--gradient-1); color: white;">
                    <div>
                        <h5 class="mb-0">Order #{order.order_id}</h5>
                        <small class="opacity-75">{order.created_at.strftime('%B %d, %Y at %I:%M %p')}</small>
                    </div>
                    <div class="text-end">
                        <span class="status-badge {status_class}">
                            <i class="{status_icons.get(order.status, 'fas fa-info')} me-1"></i>{order.status.title()}
                        </span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h6 class="fw-bold text-primary mb-2">Items Ordered:</h6>
                            <p class="text-muted mb-2">{items_summary}</p>
                            <p class="mb-0"><strong>Total: ₹{order.total}</strong></p>
                        </div>
                        <div class="col-md-4 text-md-end">
                            <p class="mb-1"><i class="fas fa-credit-card me-1"></i>{order.payment_method.upper()}</p>
                            <p class="mb-0"><i class="fas fa-map-marker-alt me-1"></i>{order.customer_address[:30]}...</p>
                        </div>
                    </div>
                    {thank_you_msg}
                </div>
            </div>
            """
    else:
        content += """
            <div class="text-center py-5">
                <div class="dashboard-icon mx-auto mb-3" style="background: var(--gradient-2);">
                    <i class="fas fa-shopping-bag"></i>
                </div>
                <h4 class="fw-bold text-muted mb-3">No Orders Yet</h4>
                <p class="text-muted mb-4">You haven't placed any orders yet. Start by exploring our delicious menu!</p>
                <a href="/menu" class="btn btn-primary">
                    <i class="fas fa-utensils me-2"></i>Browse Menu
                </a>
            </div>
        """

    content += """
        </div>
    </div>
</div>

<script>
// Auto-refresh orders every 30 seconds to show real-time updates
setInterval(function() {
    fetch('/api/my-orders-status')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            data.orders.forEach(order => {
                const orderCard = document.getElementById('order-' + order.order_id);
                if (orderCard) {
                    const statusBadge = orderCard.querySelector('.status-badge');
                    if (statusBadge) {
                        statusBadge.className = 'status-badge status-' + order.status;
                        statusBadge.innerHTML = '<i class="fas fa-' + getStatusIcon(order.status) + ' me-1"></i>' + order.status.charAt(0).toUpperCase() + order.status.slice(1);
                    }
                }
            });
        }
    })
    .catch(error => console.log('Status update failed:', error));
}, 30000);

function getStatusIcon(status) {
    const icons = {
        'pending': 'clock',
        'preparing': 'fire',
        'ready': 'check-circle',
        'delivered': 'truck'
    };
    return icons[status] || 'info';
}
</script>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="My Orders - Biryani Club", 
                                content=content, 
                                current_user=user,
                                extra_scripts="")

@app.route('/api/my-orders-status')
@login_required
def api_my_orders_status():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'error': 'User not found'})
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
    
    orders_data = []
    for order in orders:
        orders_data.append({
            'order_id': order.order_id,
            'status': order.status
        })
    
    return jsonify({'success': True, 'orders': orders_data})

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if not user:
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('login'))
    orders = Order.query.filter_by(customer_phone=user.phone).order_by(Order.created_at.desc()).all()

    content = f"""
<div class="container py-5">
    <div class="row">
        <div class="col-lg-4">
            <div class="card text-center">
                <div class="card-body p-4">
                    <div class="dashboard-icon mx-auto mb-3" style="background: var(--gradient-1);">
                        <i class="fas fa-user"></i>
                    </div>
                    <h4 class="fw-bold">{user.full_name}</h4>
                    <p class="text-muted">@{user.username}</p>
                    <p><i class="fas fa-envelope me-2"></i>{user.email}</p>
                    <p><i class="fas fa-phone me-2"></i>{user.phone}</p>
                    <div class="mt-3">
                        <span class="badge" style="background: var(--gradient-2); font-size: 1rem; padding: 10px 20px;">
                            <i class="fas fa-star me-2"></i>{user.loyalty_points} Points
                        </span>
                    </div>
                    {"<div class='mt-3'><span class='badge bg-danger'>Admin User</span></div>" if user.is_admin else ""}
                    {"<div class='mt-2'><span class='badge bg-info'>Delivery Team</span></div>" if user.is_delivery else ""}
                </div>
            </div>
        </div>

        <div class="col-lg-8">
            <div class="card">
                <div class="card-header" style="background: var(--gradient-1); color: white;">
                    <h5 class="mb-0"><i class="fas fa-history me-2"></i>Order History</h5>
                </div>
                <div class="card-body">
    """

    if orders:
        for order in orders:
            status_class = f"status-{order.status}"
            content += f"""
                    <div class="d-flex justify-content-between align-items-center p-3 mb-3 rounded glass-effect">
                        <div>
                            <h6 class="mb-1">Order #{order.order_id}</h6>
                            <p class="mb-0 text-muted">{order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                        <div class="text-end">
                            <div class="mb-1">
                                <span class="status-badge {status_class}">{order.status}</span>
                            </div>
                            <strong>₹{order.total}</strong>
                        </div>
                    </div>
            """
    else:
        content += """
                    <p class="text-muted text-center">No orders yet. <a href="/menu">Start ordering!</a></p>
        """

    content += """
                </div>
            </div>
        </div>
    </div>
</div>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="Profile - Biryani Club", 
                                content=content, 
                                current_user=user,
                                extra_scripts="")

# Admin Panel
@app.route('/admin')
@admin_required
def admin():
    total_orders = Order.query.count()
    total_users = User.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    content = f"""
<div class="container py-5">
    <div class="text-center mb-5">
        <h2 class="display-4 fw-bold text-gradient">Admin Dashboard</h2>
        <p class="lead text-muted">Manage your Biryani Club operations</p>
    </div>

    <!-- Store Status Toggle -->
    <div class="text-center mb-5">
        <button class="btn btn-lg {'btn-success' if store_status['open'] else 'btn-danger'}" onclick="toggleStore()">
            <i class="fas fa-{ 'check-circle' if store_status['open'] else 'times-circle'} me-2"></i>
            Store is currently {'Open' if store_status['open'] else 'Closed'}
        </button>
    </div>

    <!-- Quick Actions -->
    <div class="row g-3 mb-5">
        <div class="col-md-4">
            <button class="btn btn-info w-100" onclick="showStockManagement()">
                <i class="fas fa-boxes me-2"></i>Manage Stock
            </button>
        </div>
        <div class="col-md-4">
            <button class="btn btn-warning w-100" onclick="showAssignDelivery()">
                <i class="fas fa-truck me-2"></i>Assign Delivery
            </button>
        </div>
        <div class="col-md-4">
            <button class="btn btn-secondary w-100" onclick="refreshOrders()">
                <i class="fas fa-refresh me-2"></i>Refresh Orders
            </button>
        </div>
    </div>

    <!-- Stats Cards -->
    <div class="row g-4 mb-5">
        <div class="col-lg-3 col-md-6">
            <div class="dashboard-card">
                <div class="dashboard-icon mx-auto" style="background: var(--gradient-1);">
                    <i class="fas fa-shopping-cart"></i>
                </div>
                <h3 class="fw-bold">{total_orders}</h3>
                <p class="text-muted">Total Orders</p>
            </div>
        </div>
        <div class="col-lg-3 col-md-6">
            <div class="dashboard-card">
                <div class="dashboard-icon mx-auto" style="background: var(--gradient-2);">
                    <i class="fas fa-users"></i>
                </div>
                <h3 class="fw-bold">{total_users}</h3>
                <p class="text-muted">Total Users</p>
            </div>
        </div>
        <div class="col-lg-3 col-md-6">
            <div class="dashboard-card">
                <div class="dashboard-icon mx-auto" style="background: var(--gradient-4);">
                    <i class="fas fa-clock"></i>
                </div>
                <h3 class="fw-bold">{pending_orders}</h3>
                <p class="text-muted">Pending Orders</p>
            </div>
        </div>
        <div class="col-lg-3 col-md-6">
            <div class="dashboard-card">
                <div class="dashboard-icon mx-auto" style="background: var(--gradient-3);">
                    <i class="fas fa-rupee-sign"></i>
                </div>
                <h3 class="fw-bold">₹{total_revenue:,.0f}</h3>
                <p class="text-muted">Total Revenue</p>
            </div>
        </div>
    </div>

    <!-- Recent Orders -->
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center" style="background: var(--gradient-5); color: white;">
            <h5 class="mb-0"><i class="fas fa-list me-2"></i>Recent Orders</h5>
            <button class="btn btn-light btn-sm" onclick="refreshOrders()">
                <i class="fas fa-refresh me-1"></i>Refresh
            </button>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Customer</th>
                            <th>Items</th>
                            <th>Total</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for order in recent_orders:
        items = order.get_items()
        items_summary = f"{len(items)} items"
        status_class = f"status-{order.status}"

        content += f"""
                        <tr>
                            <td><strong>#{order.order_id}</strong></td>
                            <td>{order.customer_name}<br><small class="text-muted">{order.customer_phone}</small></td>
                            <td>{items_summary}</td>
                            <td><strong>₹{order.total}</strong></td>
                            <td><span class="status-badge {status_class}">{order.status}</span></td>
                            <td>{order.created_at.strftime('%m/%d/%Y %H:%M')}</td>
                            <td>
                                <div class="btn-group" role="group">
                                    <button class="btn btn-info btn-sm" onclick="updateOrderStatus('{order.order_id}', 'preparing')">
                                        <i class="fas fa-fire"></i>
                                    </button>
                                    <button class="btn btn-success btn-sm" onclick="updateOrderStatus('{order.order_id}', 'ready')">
                                        <i class="fas fa-check"></i>
                                    </button>
                                    <button class="btn btn-primary btn-sm" onclick="updateOrderStatus('{order.order_id}', 'delivered')">
                                        <i class="fas fa-truck"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
        """

    content += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Stock Management Modal -->
    <div class="modal fade" id="stockModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content glass-effect">
                <div class="modal-header text-white" style="background: var(--gradient-2);">
                    <h5 class="modal-title"><i class="fas fa-boxes me-2"></i>Stock Management</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="stock-items"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Assign Delivery Modal -->
    <div class="modal fade" id="deliveryModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content glass-effect">
                <div class="modal-header text-white" style="background: var(--gradient-3);">
                    <h5 class="modal-title"><i class="fas fa-truck me-2"></i>Assign Delivery Person</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="delivery-assignments"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function updateOrderStatus(orderId, status) {
    fetch('/admin/update_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            order_id: orderId,
            status: status
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Order status updated!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Error updating status', 'danger');
        }
    });
}

function refreshOrders() {
    location.reload();
}

function toggleStore() {
    fetch('/admin/toggle_store', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Store status updated!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Error updating store status', 'danger');
        }
    });
}

function showStockManagement() {
    fetch('/admin/stock_items')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let html = '';
            data.items.forEach(item => {
                const stockStatus = item.in_stock ? 'In Stock' : 'Out of Stock';
                const btnClass = item.in_stock ? 'btn-danger' : 'btn-success';
                const btnText = item.in_stock ? 'Mark Out of Stock' : 'Mark In Stock';
                const btnIcon = item.in_stock ? 'times' : 'check';
                
                html += `
                    <div class="d-flex justify-content-between align-items-center p-3 mb-3 rounded glass-effect">
                        <div>
                            <h6 class="mb-1">${item.emoji} ${item.name}</h6>
                            <small class="text-muted">₹${item.price} - ${item.category}</small><br>
                            <span class="badge ${item.in_stock ? 'bg-success' : 'bg-danger'}">${stockStatus}</span>
                        </div>
                        <button class="btn ${btnClass} btn-sm" onclick="toggleStock('${item.name}', ${!item.in_stock})">
                            <i class="fas fa-${btnIcon} me-1"></i>${btnText}
                        </button>
                    </div>
                `;
            });
            document.getElementById('stock-items').innerHTML = html;
            const stockModal = new bootstrap.Modal(document.getElementById('stockModal'));
            stockModal.show();
        }
    });
}

function toggleStock(itemName, inStock) {
    fetch('/admin/toggle_stock', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            item_name: itemName,
            in_stock: inStock
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Stock status updated!', 'success');
            showStockManagement(); // Refresh the modal
        } else {
            showNotification('Error updating stock', 'danger');
        }
    });
}

function showAssignDelivery() {
    fetch('/admin/delivery_assignments')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let html = '';
            data.ready_orders.forEach(order => {
                html += `
                    <div class="card mb-3">
                        <div class="card-body">
                            <h6>Order #${order.order_id}</h6>
                            <p class="mb-2">${order.customer_name} - ₹${order.total}</p>
                            <select class="form-select mb-2" id="delivery-${order.order_id}">
                                <option value="">Select Delivery Person</option>
                `;
                
                data.delivery_persons.forEach(person => {
                    html += `<option value="${person.id}">${person.full_name}</option>`;
                });
                
                html += `
                            </select>
                            <button class="btn btn-primary btn-sm" onclick="assignDelivery('${order.order_id}')">
                                <i class="fas fa-truck me-1"></i>Assign
                            </button>
                        </div>
                    </div>
                `;
            });
            
            if (data.ready_orders.length === 0) {
                html = '<p class="text-muted text-center">No orders ready for delivery assignment.</p>';
            }
            
            document.getElementById('delivery-assignments').innerHTML = html;
            const deliveryModal = new bootstrap.Modal(document.getElementById('deliveryModal'));
            deliveryModal.show();
        }
    });
}

function assignDelivery(orderId) {
    const selectElement = document.getElementById('delivery-' + orderId);
    const deliveryPersonId = selectElement.value;
    
    if (!deliveryPersonId) {
        showNotification('Please select a delivery person', 'warning');
        return;
    }
    
    fetch('/admin/assign_delivery', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            order_id: orderId,
            delivery_person_id: deliveryPersonId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Delivery person assigned!', 'success');
            showAssignDelivery(); // Refresh the modal
        } else {
            showNotification('Error assigning delivery person', 'danger');
        }
    });
}
</script>
"""

    user = User.query.get(session['user_id'])
    return render_template_string(BASE_TEMPLATE, 
                                title="Admin Panel - Biryani Club", 
                                content=content, 
                                current_user=user,
                                extra_scripts="")

@app.route('/admin/update_order', methods=['POST'])
@admin_required
def update_order_status():
    try:
        data = request.json
        order_id = data.get('order_id')
        status = data.get('status')

        order = Order.query.filter_by(order_id=order_id).first()
        if order:
            order.status = status
            if status == 'ready':
                order.estimated_delivery = datetime.now() + timedelta(minutes=30)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Order not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/toggle_store', methods=['POST'])
@admin_required
def toggle_store_status():
    global store_status
    store_status['open'] = not store_status['open']
    return jsonify({'success': True, 'open': store_status['open']})

@app.route('/admin/stock_items')
@admin_required
def get_stock_items():
    try:
        # Get items from database, or create them if they don't exist
        db_items = MenuItem.query.all()
        
        if not db_items:
            # Initialize database with menu items
            for category, items in MENU.items():
                for item in items:
                    menu_item = MenuItem(
                        name=item['name'],
                        category=category,
                        price=item['price'],
                        description=item['description'],
                        emoji=item['emoji'],
                        in_stock=True
                    )
                    db.session.add(menu_item)
            db.session.commit()
            db_items = MenuItem.query.all()
        
        items_data = []
        for item in db_items:
            items_data.append({
                'name': item.name,
                'category': item.category,
                'price': item.price,
                'description': item.description,
                'emoji': item.emoji,
                'in_stock': item.in_stock
            })
        
        return jsonify({'success': True, 'items': items_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/toggle_stock', methods=['POST'])
@admin_required
def toggle_stock():
    try:
        data = request.json
        item_name = data.get('item_name')
        in_stock = data.get('in_stock')
        
        item = MenuItem.query.filter_by(name=item_name).first()
        if item:
            item.in_stock = in_stock
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Item not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/delivery_assignments')
@admin_required
def get_delivery_assignments():
    try:
        ready_orders = Order.query.filter_by(status='ready', delivery_person_id=None).all()
        delivery_persons = User.query.filter_by(is_delivery=True).all()
        
        orders_data = []
        for order in ready_orders:
            orders_data.append({
                'order_id': order.order_id,
                'customer_name': order.customer_name,
                'total': order.total
            })
        
        persons_data = []
        for person in delivery_persons:
            persons_data.append({
                'id': person.id,
                'full_name': person.full_name
            })
        
        return jsonify({
            'success': True,
            'ready_orders': orders_data,
            'delivery_persons': persons_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/assign_delivery', methods=['POST'])
@admin_required
def assign_delivery_person():
    try:
        data = request.json
        order_id = data.get('order_id')
        delivery_person_id = data.get('delivery_person_id')
        
        order = Order.query.filter_by(order_id=order_id).first()
        if order:
            order.delivery_person_id = delivery_person_id
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Order not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Delivery Panel
@app.route('/delivery')
@delivery_required
def delivery_panel():
    delivery_person = User.query.get(session['user_id'])
    assigned_orders = Order.query.filter_by(delivery_person_id=delivery_person.id, status='ready').all()
    available_orders = Order.query.filter_by(status='ready', delivery_person_id=None).all()

    content = f"""
<div class="container py-5">
    <div class="text-center mb-5">
        <h2 class="display-4 fw-bold text-gradient">Delivery Dashboard</h2>
        <p class="lead text-muted">Welcome back, {delivery_person.full_name}!</p>
    </div>

    <!-- Stats -->
    <div class="row g-4 mb-5">
        <div class="col-md-6">
            <div class="dashboard-card">
                <div class="dashboard-icon mx-auto" style="background: var(--gradient-1);">
                    <i class="fas fa-truck"></i>
                </div>
                <h3 class="fw-bold">{len(assigned_orders)}</h3>
                <p class="text-muted">My Deliveries</p>
            </div>
        </div>
        <div class="col-md-6">
            <div class="dashboard-card">
                <div class="dashboard-icon mx-auto" style="background: var(--gradient-2);">
                    <i class="fas fa-clock"></i>
                </div>
                <h3 class="fw-bold">{len(available_orders)}</h3>
                <p class="text-muted">Available Orders</p>
            </div>
        </div>
    </div>

    <!-- My Deliveries -->
    <div class="card mb-4">
        <div class="card-header" style="background: var(--gradient-1); color: white;">
            <h5 class="mb-0"><i class="fas fa-truck me-2"></i>My Deliveries</h5>
        </div>
        <div class="card-body">
    """

    if assigned_orders:
        for order in assigned_orders:
            content += f"""
            <div class="d-flex justify-content-between align-items-center p-3 mb-3 rounded glass-effect">
                <div>
                    <h6 class="mb-1">Order #{order.order_id}</h6>
                    <p class="mb-1"><i class="fas fa-user me-1"></i>{order.customer_name} - {order.customer_phone}</p>
                    <p class="mb-0"><i class="fas fa-map-marker-alt me-1"></i>{order.customer_address}</p>
                </div>
                <div class="text-end">
                    <div class="mb-2">
                        <strong>₹{order.total}</strong>
                    </div>
                    <button class="btn btn-success btn-sm" onclick="completeDelivery('{order.order_id}')">
                        <i class="fas fa-check me-1"></i>Delivered
                    </button>
                </div>
            </div>
            """
    else:
        content += """
            <p class="text-muted text-center">No current deliveries assigned.</p>
        """

    content += """
        </div>
    </div>

    <!-- Available Orders -->
    <div class="card">
        <div class="card-header" style="background: var(--gradient-2); color: white;">
            <h5 class="mb-0"><i class="fas fa-list me-2"></i>Available Orders</h5>
        </div>
        <div class="card-body">
    """

    if available_orders:
        for order in available_orders:
            content += f"""
            <div class="d-flex justify-content-between align-items-center p-3 mb-3 rounded glass-effect">
                <div>
                    <h6 class="mb-1">Order #{order.order_id}</h6>
                    <p class="mb-1"><i class="fas fa-user me-1"></i>{order.customer_name} - {order.customer_phone}</p>
                    <p class="mb-0"><i class="fas fa-map-marker-alt me-1"></i>{order.customer_address}</p>
                </div>
                <div class="text-end">
                    <div class="mb-2">
                        <strong>₹{order.total}</strong>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="acceptDelivery('{order.order_id}')">
                        <i class="fas fa-truck me-1"></i>Accept
                    </button>
                </div>
            </div>
            """
    else:
        content += """
            <p class="text-muted text-center">No orders available for delivery.</p>
        """

    content += """
        </div>
    </div>
</div>

<script>
function acceptDelivery(orderId) {
    fetch('/delivery/accept', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            order_id: orderId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Delivery accepted!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Error accepting delivery', 'danger');
        }
    });
}

function completeDelivery(orderId) {
    fetch('/delivery/complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            order_id: orderId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Delivery completed!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Error completing delivery', 'danger');
        }
    });
}
</script>
"""

    user = User.query.get(session['user_id'])
    return render_template_string(BASE_TEMPLATE, 
                                title="Delivery Panel - Biryani Club", 
                                content=content, 
                                current_user=user,
                                extra_scripts="")

@app.route('/delivery/accept', methods=['POST'])
@delivery_required
def accept_delivery():
    try:
        data = request.json
        order_id = data.get('order_id')

        order = Order.query.filter_by(order_id=order_id).first()
        if order:
            order.delivery_person_id = session['user_id']
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Order not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delivery/complete', methods=['POST'])
@delivery_required
def complete_delivery():
    try:
        data = request.json
        order_id = data.get('order_id')

        order = Order.query.filter_by(order_id=order_id).first()
        if order:
            order.status = 'delivered'
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Order not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Main Routes (Updated)
@app.route('/')
def home():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None

    store_status_banner = ""
    if not store_status['open']:
        store_status_banner = """
        <div class="container">
            <div class="store-status-banner store-closed">
                <i class="fas fa-times-circle me-2"></i>The store is currently closed. Orders are not being accepted.
            </div>
        </div>
        """
    else:
        store_status_banner = """
        <div class="container">
            <div class="store-status-banner store-open">
                <i class="fas fa-check-circle me-2"></i>Welcome! The store is open and accepting orders.
            </div>
        </div>
        """

    content = f"""
<!-- Store Status Banner -->
{store_status_banner}

<!-- Hero Section -->
<section class="hero-section position-relative text-white text-center overflow-hidden">
    <div class="container position-relative">
        <div class="row align-items-center">
            <div class="col-lg-8 mx-auto">
                <h1 class="display-2 fw-bold mb-4">
                    <span class="item-emoji">🍛</span> Welcome to <br>
                    <span style="background: linear-gradient(45deg, #ffd700, #ffec8c); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Biryani Club</span>
                    <span class="item-emoji">✨</span>
                </h1>
                <p class="lead mb-5 fs-3">Authentic, mouth-watering biryani and delicious treats, delivered fresh to your doorstep in <strong>30 minutes</strong>!</p>

                <div class="d-grid gap-3 d-md-flex justify-content-md-center">
                    <a href="/menu" class="btn btn-light btn-lg px-5 py-3" style="background: linear-gradient(45deg, #ff6b35, #f7931e); color: white; font-weight: bold;">
                        <i class="fas fa-fire me-2"></i>Order Now
                    </a>
                    <a href="tel:+919876543210" class="btn btn-outline-light btn-lg px-4 py-3">
                        <i class="fas fa-phone me-2"></i>Call Us
                    </a>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Features Section -->
<section class="py-5">
    <div class="container">
        <div class="text-center mb-5">
            <h2 class="display-5 fw-bold text-gradient">Why Choose Biryani Club?</h2>
            <p class="lead text-muted">Experience the magic of authentic flavors</p>
        </div>

        <div class="row g-4">
            <div class="col-lg-4">
                <div class="card text-center h-100">
                    <div class="card-body p-4">
                        <div class="dashboard-icon mx-auto mb-3" style="background: var(--gradient-2);">
                            <i class="fas fa-rocket"></i>
                        </div>
                        <h4 class="fw-bold mb-3">Lightning Fast ⚡</h4>
                        <p class="text-muted">Fresh, hot biryani delivered within 30-45 minutes guaranteed!</p>
                    </div>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="card text-center h-100">
                    <div class="card-body p-4">
                        <div class="dashboard-icon mx-auto mb-3" style="background: var(--gradient-2);">
                            <i class="fas fa-seedling"></i>
                        </div>
                        <h4 class="fw-bold mb-3">Fresh Ingredients 🌿</h4>
                        <p class="text-muted">Only the freshest ingredients and authentic spices for perfect taste.</p>
                    </div>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="card text-center h-100">
                    <div class="card-body p-4">
                        <div class="dashboard-icon mx-auto mb-3" style="background: var(--gradient-2);">
                            <i class="fas fa-heart"></i>
                        </div>
                        <h4 class="fw-bold mb-3">Made with Love ❤️</h4>
                        <p class="text-muted">Every dish prepared with love and traditional recipes.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Footer Section -->
<footer class="py-4 mt-5">
    <div class="container">
        <div class="text-center">
            <div class="glass-effect p-4 rounded">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <h5 class="fw-bold text-gradient mb-2">Biryani Club</h5>
                        <p class="text-muted mb-0">Authentic flavors delivered fresh</p>
                    </div>
                    <div class="col-md-6">
                        <p class="text-muted mb-0">
                            <i class="fas fa-copyright me-1"></i>2024 Biryani Club. All rights reserved.
                        </p>
                        <small class="text-muted">Made with ❤️ for food lovers</small>
                    </div>
                </div>
            </div>
        </div>
    </div>
</footer>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="Biryani Club - Delicious Food Delivered", 
                                content=content, 
                                current_user=user,
                                extra_scripts="")

@app.route('/menu')
def menu():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None

    if not store_status['open']:
        return render_template_string(BASE_TEMPLATE,
                                    title="Store Closed",
                                    content="""
                                    <div class="container text-center py-5">
                                        <h1 class="display-1 text-danger"><i class="fas fa-times-circle"></i></h1>
                                        <h2 class="fw-bold text-gradient mb-3">Store is Closed</h2>
                                        <p class="lead text-muted">We are sorry, but the store is currently closed. Please check back later or contact us for updates.</p>
                                        <a href="/" class="btn btn-primary mt-4"><i class="fas fa-home me-2"></i>Go to Home</a>
                                    </div>
                                    """,
                                    current_user=user)

    # Get menu items from database, fallback to static menu
    db_items = MenuItem.query.all()
    menu_dict = {}
    
    if db_items:
        for item in db_items:
            if item.category not in menu_dict:
                menu_dict[item.category] = []
            menu_dict[item.category].append({
                'name': item.name,
                'price': item.price,
                'description': item.description,
                'emoji': item.emoji,
                'in_stock': item.in_stock
            })
    else:
        # Use static menu if no items in database
        for category, items in MENU.items():
            menu_dict[category] = []
            for item in items:
                menu_dict[category].append({
                    'name': item['name'],
                    'price': item['price'],
                    'description': item['description'],
                    'emoji': item['emoji'],
                    'in_stock': True
                })

    content = """
<div class="container py-5">
    <div class="text-center mb-5">
        <h2 class="display-4 fw-bold text-gradient">Our Delicious Menu 🍽️</h2>
        <p class="lead text-muted">Authentic flavors that will make you crave for more</p>
    </div>

    """

    for category, items in menu_dict.items():
        content += f"""
    <div class="mb-5">
        <h3 class="fw-bold mb-4 text-center" style="color: var(--primary);">
            <i class="fas fa-utensils me-2"></i>{category}
        </h3>
        <div class="row g-4">
        """

        for item in items:
            stock_class = "" if item['in_stock'] else "opacity-50"
            stock_badge = "" if item['in_stock'] else '<span class="badge bg-danger mb-2">Out of Stock</span><br>'
            button_html = f"""
                <button class="btn btn-primary btn-sm" onclick="addToCart('{item['name']}', {item['price']}, '{item['emoji']}')">
                    <i class="fas fa-plus me-2"></i>Add
                </button>
            """ if item['in_stock'] else '<button class="btn btn-secondary btn-sm" disabled><i class="fas fa-times me-2"></i>Unavailable</button>'

            content += f"""
            <div class="col-lg-4 col-md-6">
                <div class="menu-item-card card {stock_class}">
                    <div class="card-body p-4">
                        <div class="text-center mb-3">
                            <span class="item-emoji">{item['emoji']}</span>
                        </div>
                        <div class="text-center mb-2">
                            {stock_badge}
                        </div>
                        <h5 class="fw-bold text-center mb-2">{item['name']}</h5>
                        <p class="text-muted text-center small mb-3">{item['description']}</p>

                        <div class="d-flex justify-content-between align-items-center">
                            <div class="price-tag">₹{item['price']}</div>
                            {button_html}
                        </div>
                    </div>
                </div>
            </div>
            """

        content += """
        </div>
    </div>
        """

    content += """
</div>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="Menu - Biryani Club", 
                                content=content, 
                                current_user=user,
                                extra_scripts="")

@app.route('/checkout')
def checkout():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None

    if not store_status['open']:
        return render_template_string(BASE_TEMPLATE,
                                    title="Store Closed",
                                    content="""
                                    <div class="container text-center py-5">
                                        <h1 class="display-1 text-danger"><i class="fas fa-times-circle"></i></h1>
                                        <h2 class="fw-bold text-gradient mb-3">Store is Closed</h2>
                                        <p class="lead text-muted">We are sorry, but the store is currently closed. Please check back later or contact us for updates.</p>
                                        <a href="/" class="btn btn-primary mt-4"><i class="fas fa-home me-2"></i>Go to Home</a>
                                    </div>
                                    """,
                                    current_user=user)

    content = """
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <div class="text-center mb-5">
                <h2 class="display-5 fw-bold text-gradient">Checkout 🛒</h2>
                <p class="lead text-muted">Complete your order in just a few steps</p>
            </div>

            <form id="checkout-form">
                <div class="card mb-4">
                    <div class="card-header text-white" style="background: var(--gradient-1);">
                        <h5 class="mb-0"><i class="fas fa-user me-2"></i>Customer Details</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="customer_name" class="form-label">Full Name *</label>
                                <input type="text" class="form-control form-control-lg" id="customer_name" required style="background: rgba(255,255,255,0.9); color: var(--dark);">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="customer_phone" class="form-label">Phone Number *</label>
                                <input type="tel" class="form-control form-control-lg" id="customer_phone" required style="background: rgba(255,255,255,0.9); color: var(--dark);">
                            </div>
                            <div class="col-12 mb-3">
                                <label for="customer_address" class="form-label">Delivery Address *</label>
                                <textarea class="form-control form-control-lg" id="customer_address" rows="3" required style="background: rgba(255,255,255,0.9); color: var(--dark);"></textarea>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card mb-4">
                    <div class="card-header text-white" style="background: var(--gradient-2);">
                        <h5 class="mb-0"><i class="fas fa-credit-card me-2"></i>Payment Method</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="payment_method" id="payment_cash" value="cash" checked>
                                    <label class="form-check-label w-100" for="payment_cash">
                                        <div class="card text-center glass-effect">
                                            <div class="card-body py-3">
                                                <i class="fas fa-money-bill-wave fa-2x text-success mb-2"></i>
                                                <h6>Cash on Delivery</h6>
                                            </div>
                                        </div>
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="payment_method" id="payment_upi" value="upi">
                                    <label class="form-check-label w-100" for="payment_upi">
                                        <div class="card text-center glass-effect">
                                            <div class="card-body py-3">
                                                <i class="fab fa-google-pay fa-2x text-primary mb-2"></i>
                                                <h6>UPI Payment</h6>
                                            </div>
                                        </div>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card mb-4">
                    <div class="card-header text-white" style="background: var(--gradient-3);">
                        <h5 class="mb-0"><i class="fas fa-shopping-bag me-2"></i>Order Summary</h5>
                    </div>
                    <div class="card-body">
                        <div id="order-summary"></div>
                        <hr style="border-color: var(--glass-border);">
                        
                        {% if session.user_id %}
                            {% set current_user = get_current_user() %}
                            {% if current_user and current_user.loyalty_points >= 2 %}
                                <div class="mb-3 p-3 rounded glass-effect">
                                    <h6 class="fw-bold text-success mb-2">
                                        <i class="fas fa-star me-2"></i>Loyalty Points Available: {{ current_user.loyalty_points }}
                                    </h6>
                                    <p class="small text-muted mb-2">2 points = ₹1 discount</p>
                                    <div class="d-flex align-items-center">
                                        <label for="loyalty-points" class="form-label me-2 mb-0">Use points:</label>
                                        <input type="number" id="loyalty-points" class="form-control form-control-sm me-2" 
                                               min="0" max="{{ current_user.loyalty_points }}" value="0" 
                                               style="width: 100px; background: rgba(255,255,255,0.9); color: var(--dark);"
                                               onchange="updateLoyaltyDiscount()">
                                        <button type="button" class="btn btn-success btn-sm" onclick="useMaxPoints()">
                                            <i class="fas fa-coins me-1"></i>Use Max
                                        </button>
                                    </div>
                                </div>
                            {% endif %}
                        {% endif %}
                        
                        <div class="d-flex justify-content-between mb-2">
                            <span>Subtotal:</span>
                            <span id="subtotal">₹0</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2" id="loyalty-discount-row" style="display: none !important;">
                            <span class="text-success">Loyalty Discount:</span>
                            <span class="text-success" id="loyalty-discount">-₹0</span>
                        </div>
                        <hr style="border-color: var(--glass-border);">
                        <div class="d-flex justify-content-between h5 text-primary">
                            <span>Total:</span>
                            <span id="final-total">₹0</span>
                        </div>
                    </div>
                </div>

                <div class="text-center">
                    <button type="submit" class="btn btn-primary btn-lg px-5 py-3">
                        <i class="fas fa-shopping-cart me-2"></i>Place Order
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
"""

    scripts = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    updateOrderSummary();

    document.getElementById('checkout-form').addEventListener('submit', function(e) {
        e.preventDefault();
        placeOrder();
    });
});

function updateOrderSummary() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const summaryDiv = document.getElementById('order-summary');
    const subtotalDiv = document.getElementById('subtotal');
    const totalDiv = document.getElementById('final-total');

    if (cart.length === 0) {
        summaryDiv.innerHTML = '<p class="text-muted">No items in cart</p>';
        if (subtotalDiv) subtotalDiv.textContent = '₹0';
        totalDiv.textContent = '₹0';
        return;
    }

    let html = '';
    let subtotal = 0;

    cart.forEach(item => {
        const itemTotal = item.price * item.quantity;
        subtotal += itemTotal;
        html += `
            <div class="d-flex justify-content-between mb-2">
                <span>${item.emoji} ${item.name} x ${item.quantity}</span>
                <span>₹${itemTotal}</span>
            </div>
        `;
    });

    summaryDiv.innerHTML = html;
    if (subtotalDiv) subtotalDiv.textContent = '₹' + subtotal;
    
    // Calculate final total with loyalty discount
    updateLoyaltyDiscount();
}

function updateLoyaltyDiscount() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    let subtotal = 0;
    cart.forEach(item => {
        subtotal += item.price * item.quantity;
    });

    const loyaltyPointsInput = document.getElementById('loyalty-points');
    const loyaltyDiscountRow = document.getElementById('loyalty-discount-row');
    const loyaltyDiscountSpan = document.getElementById('loyalty-discount');
    const finalTotalSpan = document.getElementById('final-total');
    
    if (loyaltyPointsInput) {
        const pointsUsed = parseInt(loyaltyPointsInput.value) || 0;
        const discount = Math.floor(pointsUsed / 2); // 2 points = ₹1
        
        if (discount > 0) {
            loyaltyDiscountRow.style.display = 'flex';
            loyaltyDiscountSpan.textContent = '-₹' + discount;
        } else {
            loyaltyDiscountRow.style.display = 'none';
        }
        
        const finalTotal = Math.max(0, subtotal - discount);
        finalTotalSpan.textContent = '₹' + finalTotal;
    } else {
        finalTotalSpan.textContent = '₹' + subtotal;
    }
}

function useMaxPoints() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    let subtotal = 0;
    cart.forEach(item => {
        subtotal += item.price * item.quantity;
    });

    const loyaltyPointsInput = document.getElementById('loyalty-points');
    if (loyaltyPointsInput) {
        const maxPoints = parseInt(loyaltyPointsInput.getAttribute('max'));
        const maxUsablePoints = Math.min(maxPoints, subtotal * 2); // Can't use more points than order value
        loyaltyPointsInput.value = maxUsablePoints;
        updateLoyaltyDiscount();
    }
}

function placeOrder() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');

    if (cart.length === 0) {
        alert('Your cart is empty!');
        return;
    }

    const loyaltyPointsInput = document.getElementById('loyalty-points');
    const loyaltyPointsUsed = loyaltyPointsInput ? parseInt(loyaltyPointsInput.value) || 0 : 0;

    const formData = {
        customer_name: document.getElementById('customer_name').value,
        customer_phone: document.getElementById('customer_phone').value,
        customer_address: document.getElementById('customer_address').value,
        payment_method: document.querySelector('input[name="payment_method"]:checked').value,
        items: cart,
        loyalty_points_used: loyaltyPointsUsed
    };

    fetch('/place_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            localStorage.removeItem('cart');
            window.location.href = '/order_confirmation/' + data.order_id;
        } else {
            alert('Error placing order: ' + data.error);
        }
    })
    .catch(error => {
        alert('Error: ' + error.message);
    });
}
</script>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="Checkout - Biryani Club", 
                                content=content, 
                                current_user=user,
                                extra_scripts=scripts)

@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        data = request.json

        # Generate order ID
        order_id = 'ORD' + str(int(datetime.now().timestamp()))[-8:]

        # Calculate totals
        cart = data['items']
        subtotal = sum(item['price'] * item['quantity'] for item in cart)
        
        # Handle loyalty points redemption
        loyalty_points_used = data.get('loyalty_points_used', 0)
        loyalty_discount = 0
        
        if loyalty_points_used > 0 and 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user and user.loyalty_points >= loyalty_points_used:
                loyalty_discount = loyalty_points_used // 2  # 2 points = ₹1
                # Ensure discount doesn't exceed order value
                loyalty_discount = min(loyalty_discount, subtotal)
        
        total = subtotal - loyalty_discount

        # Create order
        order = Order(
            order_id=order_id,
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            customer_address=data['customer_address'],
            items_json=json.dumps(cart),
            subtotal=subtotal,
            discount=loyalty_discount,
            total=total,
            payment_method=data['payment_method'],
            user_id=session.get('user_id')  # Associate order with logged-in user
        )

        db.session.add(order)

        # Update user's loyalty points
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                # Deduct used points
                user.loyalty_points -= loyalty_points_used
                # Add new points based on final amount (1 point per ₹10)
                user.loyalty_points += int(total / 10)

        db.session.commit()

        return jsonify({'success': True, 'order_id': order_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/order_confirmation/<order_id>')
def order_confirmation(order_id):
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    order = Order.query.filter_by(order_id=order_id).first()

    if not order:
        return "Order not found", 404

    content = f"""
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <div class="text-center mb-5">
                <div style="width: 100px; height: 100px; border-radius: 50%; background: var(--gradient-2); display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; animation: scaleIn 0.5s ease;">
                    <i class="fas fa-check fa-3x text-white"></i>
                </div>
                <h1 class="display-4 fw-bold text-success mb-3">Order Confirmed! 🎉</h1>
                <p class="lead text-muted">Thank you for choosing Biryani Club. Your delicious meal is being prepared!</p>
            </div>

            <div class="card mb-4">
                <div class="card-header text-center py-4 text-white" style="background: var(--gradient-1);">
                    <h3 class="mb-0"><i class="fas fa-receipt me-2"></i>Order #{order.order_id}</h3>
                    <p class="mb-0 opacity-75">{order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>

                <div class="card-body p-4">
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <h6 class="fw-bold text-primary mb-3"><i class="fas fa-user me-2"></i>Customer Details</h6>
                            <p class="mb-1"><strong>Name:</strong> {order.customer_name}</p>
                            <p class="mb-1"><strong>Phone:</strong> {order.customer_phone}</p>
                            <p class="mb-0"><strong>Payment:</strong> 
                                <span class="badge" style="background: var(--gradient-2);">{order.payment_method.upper()}</span>
                            </p>
                        </div>
                        <div class="col-md-6">
                            <h6 class="fw-bold text-primary mb-3"><i class="fas fa-map-marker-alt me-2"></i>Delivery Address</h6>
                            <p class="mb-0">{order.customer_address}</p>
                        </div>
                    </div>

                    <h6 class="fw-bold text-primary mb-3"><i class="fas fa-shopping-bag me-2"></i>Your Order</h6>
    """

    for item in order.get_items():
        content += f"""
                    <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                        <div>
                            <h6 class="mb-1">{item['emoji']} {item['name']}</h6>
                            <small class="text-muted">Quantity: {item['quantity']}</small>
                        </div>
                        <div class="text-end">
                            <strong>₹{item['price'] * item['quantity']}</strong>
                        </div>
                    </div>
        """

    content += f"""
                    <div class="mt-4 p-3 rounded glass-effect">
                        {"<div class='d-flex justify-content-between mb-2'><span>Subtotal:</span><span>₹" + str(order.subtotal) + "</span></div>" if order.discount > 0 else ""}
                        {"<div class='d-flex justify-content-between mb-2 text-success'><span>Loyalty Discount:</span><span>-₹" + str(order.discount) + "</span></div>" if order.discount > 0 else ""}
                        {"<hr style='border-color: var(--glass-border);'>" if order.discount > 0 else ""}
                        <div class="d-flex justify-content-between h5 text-primary mb-0">
                            <span>Total:</span>
                            <span>₹{order.total}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card mb-4">
                <div class="card-body text-center py-4">
                    <h5 class="fw-bold text-primary mb-3"><i class="fas fa-clock me-2"></i>Estimated Delivery Time</h5>
                    <div style="font-size: 2rem; font-weight: bold; background: var(--gradient-1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;">30-45 Minutes</div>
                    <p class="text-muted mb-0">Our chef is already working on your order!</p>
                </div>
            </div>

            <div class="text-center">
                <h4 class="fw-bold text-gradient mb-3">Thank You for Choosing Biryani Club! 🙏</h4>
                <p class="text-muted mb-4">We're preparing your order with love and care.</p>
                <div class="d-flex justify-content-center gap-3">
                    <a href="/menu" class="btn btn-primary"><i class="fas fa-utensils me-2"></i>Order More</a>
                    <a href="/" class="btn btn-outline-primary"><i class="fas fa-home me-2"></i>Home</a>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
@keyframes scaleIn {{
    0% {{ transform: scale(0); }}
    100% {{ transform: scale(1); }}
}}
</style>
"""

    return render_template_string(BASE_TEMPLATE, 
                                title="Order Confirmation - Biryani Club", 
                                content=content, 
                                current_user=user,
                                extra_scripts="")

# Create admin user on startup
def create_admin_user():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@biryaniclub.com',
            password_hash=generate_password_hash('cupadmin'),
            full_name='Admin User',
            phone='1234567890',
            is_admin=True
        )
        db.session.add(admin)

    # Create delivery user
    delivery = User.query.filter_by(username='delivery').first()
    if not delivery:
        delivery = User(
            username='delivery',
            email='delivery@biryaniclub.com',
            password_hash=generate_password_hash('delivery123'),
            full_name='Delivery Person',
            phone='9876543210',
            is_delivery=True
        )
        db.session.add(delivery)

    # Initialize menu items in database
    if MenuItem.query.count() == 0:
        for category, items in MENU.items():
            for item in items:
                menu_item = MenuItem(
                    name=item['name'],
                    category=category,
                    price=item['price'],
                    description=item['description'],
                    emoji=item['emoji'],
                    in_stock=True
                )
                db.session.add(menu_item)

    db.session.commit()

# Initialize database and create tables
with app.app_context():
    db.create_all()
    create_admin_user()

if __name__ == '__main__':
    print("🍛 Biryani Club Professional App is starting...")
    print("📱 Features: User Auth, Admin Panel, Delivery Management")
    print("🎨 Professional UI with Glass Effects")
    print("👨‍💼 Admin: username='admin', password='cupadmin'")
    print("🚚 Delivery: username='delivery', password='delivery123'")

    app.run(debug=True, host='0.0.0.0', port=5000)
