import os
import re
import random
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from flask import Flask, flash, jsonify, redirect, render_template_string, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.utils import secure_filename

# =========================================================================
# ส่วนที่ 1: การตั้งค่าเริ่มต้นแอปพลิเคชัน Flask และฐานข้อมูล SQLite
# =========================================================================
BASE_DIR = r"D:\EDCOM\PythonTuta\Project"

app = Flask(__name__)
app.secret_key = os.urandom(24)

# กำหนดเส้นทางฐานข้อมูล SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'AdminData1.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# กำหนดโฟลเดอร์สำหรับเก็บไฟล์รูปภาพอัปโหลด
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'images'), exist_ok=True)

db = SQLAlchemy(app)

# =========================================================================
# การตั้งค่าระบบส่งอีเมล (สำหรับฟังก์ชันส่ง OTP)
# =========================================================================
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USERNAME = 'chawanakorn2243@gmail.com'
MAIL_PASSWORD = 'rqqw hhvt vtvx xcpu'


# =========================================================================
# ฟังก์ชันตรวจสอบเงื่อนไขรหัสผ่านกลาง
# =========================================================================
def is_valid_password(password):
    if len(password) < 6:
        return 'รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษรขึ้นไป'
    if not re.search(r'[A-Z]', password):
        return 'รหัสผ่านต้องมีตัวอักษรภาษาอังกฤษพิมพ์ใหญ่อย่างน้อย 1 ตัว'
    return None


# =========================================================================
# ส่วนที่ 2: โครงสร้างตารางฐานข้อมูล (Database Models)
# =========================================================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), default='user')
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    profile_image = db.Column(db.String(100), nullable=True)
    otp_code = db.Column(db.String(10), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    image_file = db.Column(db.String(100), nullable=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    slip_image = db.Column(db.String(100), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='รอดำเนินการ')
    date_ordered = db.Column(db.DateTime, default=datetime.now)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    order = db.relationship('Order', backref=db.backref('items', lazy=True))


# =========================================================================
# ส่วนที่ 3: เทมเพลต HTML
# =========================================================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --card-bg: rgba(30, 41, 59, 0.85); --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; padding: 40px 20px; color: var(--text-main); }
        .container { background: rgba(15, 23, 42, 0.85); padding: 35px; max-width: 1200px; margin: auto; border-radius: 24px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 20px; margin-bottom: 25px; flex-wrap: wrap; gap: 15px; }
        .brand { display: flex; align-items: center; gap: 20px; text-decoration: none; cursor: pointer; }
        .brand img { width: 110px; height: 110px; object-fit: contain; border-radius: 16px; background: #1e293b; padding: 8px; border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .brand h1 { margin: 0; font-size: 32px; font-weight: 600; color: #ffffff; letter-spacing: 0.5px; }
        .nav-links { display: flex; align-items: center; gap: 12px; }
        .nav-links a { text-decoration: none; font-weight: 500; padding: 10px 20px; border-radius: 12px; transition: all 0.3s ease; font-size: 14px; }
        .cart-btn { background: var(--primary-color); color: white !important; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); }
        .auth-btn { color: #ffffff; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.15); display: inline-flex; align-items: center; gap: 8px; padding: 8px 18px; border-radius: 12px; }
        .auth-btn img { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; border: 1px solid rgba(255,255,255,0.3); }
        .user-dropdown { position: relative; display: inline-block; cursor: pointer; }
        .user-dropdown::after { content: ''; position: absolute; top: 100%; left: 0; width: 100%; height: 20px; }
        .dropdown-content { display: none; position: absolute; right: 0; top: calc(100% + 15px); background-color: #1e293b; min-width: 200px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-radius: 12px; overflow: hidden; z-index: 100; border: 1px solid rgba(255, 255, 255, 0.1); }
        .dropdown-content a { color: #f8fafc; padding: 12px 16px; text-decoration: none; display: block; font-weight: 500; text-align: left; border-radius: 0; }
        .dropdown-content a:hover { background-color: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .user-dropdown:hover .dropdown-content { display: block; }
        .category-menu { display: flex; gap: 12px; margin-bottom: 35px; flex-wrap: wrap; }
        .category-menu a { text-decoration: none; color: var(--text-secondary); padding: 10px 22px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(30, 41, 59, 0.6); font-size: 14px; }
        .category-menu a:hover { background: var(--primary-color); color: white; border-color: var(--primary-color); }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 25px; }
        .product-card { background: var(--card-bg); border-radius: 18px; padding: 20px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.3); border: 1px solid rgba(255, 255, 255, 0.08); display: flex; flex-direction: column; justify-content: space-between; cursor: pointer; transition: 0.3s; }
        .product-card:hover { transform: translateY(-6px); border-color: rgba(239, 68, 68, 0.4); }
        .product-card img { width: 100%; height: 170px; object-fit: contain; margin-bottom: 15px; }
        .product-card h4 { margin: 0 0 8px 0; font-size: 15px; color: #ffffff; height: 42px; overflow: hidden; }
        .badge { display: inline-block; padding: 4px 12px; background: rgba(255, 255, 255, 0.08); border-radius: 20px; font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; }
        .price { font-size: 22px; font-weight: 600; color: #4ade80; margin: 8px 0; }
        .stock { font-size: 12px; color: var(--text-secondary); margin-bottom: 15px; }
        .add-btn { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 12px; width: 100%; border-radius: 12px; cursor: pointer; font-weight: 500; font-family: 'Prompt'; font-size: 14px; }
        .add-btn:disabled { background: #334155; color: #64748b; cursor: not-allowed; }
        .alert { background: #064e3b; color: #34d399; padding: 14px; border-radius: 14px; margin-bottom: 25px; text-align: center; border: 1px solid #10b981; font-weight: 500; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="{{ url_for('index') }}" class="brand">
                <img src="{{ url_for('static', filename='Logo.png') }}" alt="logo" onerror="this.src='{{ url_for('static', filename='images/logo.png') }}'">
                <h1>WHEY STATION</h1>
            </a>
            <div class="nav-links">
                <a href="{{ url_for('cart') }}" class="cart-btn">🛒 ตะกร้า (<span id="cart-count">{{ cart_count }}</span>)</a>
                {% if session.get('username') %}
                    <div class="user-dropdown">
                        <span class="auth-btn">
                            {% if session.get('profile_image') %}
                                <img src="{{ url_for('static', filename='uploads/' + session.profile_image) }}" alt="profile">
                            {% else %}
                                👤
                            {% endif %}
                            {{ session.username }} ▾
                        </span>
                        <div class="dropdown-content">
                            <a href="{{ url_for('profile') }}">⚙️ โปรไฟล์ของฉัน</a>
                            <a href="{{ url_for('my_orders') }}">📋 ตรวจสอบสถานะ</a>
                            {% if session.get('role') == 'admin' %}
                                <a href="{{ url_for('admin') }}" style="color: #ef4444; font-weight: 600;">⚡ ไปหน้าแอดมิน</a>
                            {% endif %}
                            <a href="{{ url_for('logout') }}" style="color: #ef4444;">🚪 ออกจากระบบ</a>
                        </div>
                    </div>
                {% else %}
                    <a href="{{ url_for('login') }}" class="auth-btn">เข้าสู่ระบบ</a>
                {% endif %}
            </div>
        </div>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        <div class="category-menu">
            <a href="/?category=All">ทั้งหมด</a>
            <a href="/?category=เวย์">เวย์โปรตีน</a>
            <a href="/?category=ครีเอทีน">ครีเอทีน</a>
            <a href="/?category=วิตามิน">วิตามิน</a>
            <a href="/?category=แอลคาเนทีน">แอลคาเนทีน</a>
        </div>
        <div class="product-grid">
            {% for product in products %}
            <div class="product-card" onclick="window.location='{{ url_for('product_detail', product_id=product.id) }}'">
                <div>
                    {% if product.image_file %}
                        <img src="{{ url_for('static', filename='images/' + product.image_file) }}" alt="{{ product.name }}">
                    {% endif %}
                    <h4>{{ product.name }}</h4>
                    <span class="badge">{{ product.category }}</span>
                </div>
                <div>
                    <div class="price">฿{{ "{:,.0f}".format(product.price) }}<br><span style="font-size: 11px; color: var(--text-secondary); font-weight: normal;">(ราคารวม Vat 7%)</span></div>
                    <div class="stock">สินค้าคงเหลือ: {{ product.stock }} ชิ้น</div>
                    {% if product.stock > 0 %}
                        <a href="{{ url_for('add_to_cart', product_id=product.id) }}" style="text-decoration: none;" onclick="event.stopPropagation();">
                            <button class="add-btn">เพิ่มลงตะกร้า</button>
                        </a>
                    {% else %}
                        <button class="add-btn" disabled onclick="event.stopPropagation();">สินค้าหมด</button>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

HTML_LOGIN = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>เข้าสู่ระบบ - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; color: #f8fafc; }
        .auth-card { background: rgba(15, 23, 42, 0.9); padding: 40px; border-radius: 20px; width: 350px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); backdrop-filter: blur(12px); text-align: center; border: 1px solid rgba(255, 255, 255, 0.1); }
        .auth-card h2 { color: #ef4444; font-size: 28px; margin-bottom: 10px; }
        .auth-card p { color: #94a3b8; margin-bottom: 30px; font-size: 14px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 15px; margin-bottom: 15px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 14px; color: #fff; }
        .btn-main { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); margin-bottom: 15px; }
        .password-container { position: relative; width: 100%; }
        .toggle-password { position: absolute; right: 15px; top: 15px; cursor: pointer; color: #94a3b8; }
        .forgot-link { display: block; text-align: right; margin-bottom: 15px; color: #60a5fa; text-decoration: none; font-size: 13px; }
        .forgot-link:hover { text-decoration: underline; }
        .register-link { display: block; padding: 15px; border: 2px solid #10b981; color: #34d399; text-decoration: none; border-radius: 10px; font-weight: 600; background: rgba(16, 185, 129, 0.1); }
        .admin-link-text { display: block; margin-top: 15px; color: #ef4444; text-decoration: none; font-size: 14px; font-weight: 600; }
        .admin-link-text:hover { text-decoration: underline; }
        .home-link { display: inline-block; margin-top: 20px; color: #cbd5e1; text-decoration: none; background: rgba(15, 23, 42, 0.8); padding: 8px 20px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1); }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(239, 68, 68, 0.4); }
    </style>
</head>
<body>
    <div class="auth-card">
        <h2>เข้าสู่ระบบ</h2>
        <p>ยินดีต้อนรับกลับสู่ Whey Station</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="ชื่อผู้ใช้งาน" required>
            <div class="password-container">
                <input type="password" name="password" id="password" placeholder="รหัสผ่าน" required>
                <span class="toggle-password" onclick="toggleVisibility('password', this)">👁️</span>
            </div>
            <a href="{{ url_for('forgot_password') }}" class="forgot-link">ลืมรหัสผ่าน?</a>
            <button type="submit" class="btn-main">เข้าสู่ระบบ</button>
        </form>
        <a href="{{ url_for('admin_login') }}" class="admin-link-text">⚡ เข้าสู่ระบบแอดมิน</a>
        <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 25px 0;">
        <p style="margin-bottom: 15px; color: #94a3b8;">ยังไม่มีบัญชีใช่ไหม?</p>
        <a href="{{ url_for('register') }}" class="register-link">สมัครสมาชิกใหม่</a>
    </div>
    <a href="{{ url_for('index') }}" class="home-link">กลับหน้าแรก</a>
    <script>
        function toggleVisibility(inputId, icon) {
            var x = document.getElementById(inputId);
            if (x.type === "password") { x.type = "text"; icon.innerHTML = "👁️‍🗨️"; }
            else { x.type = "password"; icon.innerHTML = "👁️"; }
        }
    </script>
</body>
</html>
"""

HTML_REGISTER = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>สมัครสมาชิก - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; color: #f8fafc; padding: 30px 0; }
        .auth-card { background: rgba(15, 23, 42, 0.9); padding: 35px 40px; border-radius: 20px; width: 450px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); backdrop-filter: blur(12px); border-top: 6px solid #10b981; border: 1px solid rgba(255, 255, 255, 0.1); }
        .auth-card h2 { color: #34d399; font-size: 26px; margin-bottom: 5px; margin-top: 0; text-align: center; }
        .auth-card p { color: #94a3b8; margin-bottom: 20px; font-size: 13px; text-align: center; line-height: 1.5; }
        
        .profile-pic-wrapper { text-align: center; margin-bottom: 25px; }
        .preview-circle { width: 120px; height: 120px; border-radius: 50%; background: rgba(30, 41, 59, 0.8); border: 3px solid #10b981; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.4); position: relative; }
        .preview-circle span { font-size: 50px; color: #64748b; }
        
        #preview-canvas { display: none; width: 100%; height: 100%; cursor: grab; object-fit: cover; }
        #preview-canvas:active { cursor: grabbing; }

        .upload-btn { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #fff; padding: 8px 20px; border-radius: 20px; cursor: pointer; font-size: 13px; transition: 0.3s; display: inline-block; font-family: 'Prompt'; }
        .upload-btn:hover { background: #10b981; border-color: #10b981; }
        input[type="file"] { display: none; }

        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .form-group { margin-bottom: 15px; text-align: left; }
        .form-group.full-width { grid-column: span 2; }
        .form-group label { display: block; font-size: 13px; font-weight: 500; color: #cbd5e1; margin-bottom: 6px; }
        .form-control { width: 100%; padding: 12px 15px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 14px; color: #fff; }
        .form-control:focus { outline: none; border-color: #34d399; box-shadow: 0 0 8px rgba(52, 211, 153, 0.3); }
        .btn-main { background: linear-gradient(135deg, #10b981, #059669); color: white; width: 100%; padding: 14px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4); margin-top: 10px; margin-bottom: 15px; }
        .password-container { position: relative; width: 100%; }
        .toggle-password { position: absolute; right: 15px; top: 12px; cursor: pointer; color: #94a3b8; }
        .login-link { display: block; padding: 12px; border: 2px solid #3b82f6; color: #60a5fa; text-decoration: none; border-radius: 10px; font-weight: 600; background: rgba(59, 130, 246, 0.1); font-size: 14px; text-align: center; }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid rgba(239, 68, 68, 0.4); font-size: 13px; text-align: left; line-height: 1.5; word-break: break-word; }
    </style>
</head>
<body>
    <div class="auth-card">
        <h2>สมัครสมาชิกใหม่</h2>
        <p>กรอกข้อมูลรายละเอียดด้านล่างให้ครบถ้วน<br>(รหัสผ่านอย่างน้อย 6 ตัว และมีตัวพิมพ์ใหญ่ 1 ตัว)</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        
        <form method="POST" enctype="multipart/form-data">
            
            <div class="profile-pic-wrapper">
                <div class="preview-circle">
                    <span id="default-icon">👤</span>
                    <canvas id="preview-canvas" width="400" height="400"></canvas>
                </div>
                <input type="hidden" name="cropped_image" id="cropped_image">
                <p id="drag-hint" style="font-size: 11px; color: #fcd34d; margin-top: 0; margin-bottom: 10px; display: none;">* ลากหรือใช้นิ้วเลื่อนเพื่อขยับรูปได้</p>
                <label for="profile_image" class="upload-btn">📷 เลือกรูปโปรไฟล์</label>
                <input type="file" name="profile_image" id="profile_image" accept="image/*">
            </div>

            <div class="form-grid">
                <div class="form-group full-width">
                    <label>ชื่อผู้ใช้งาน (Username)</label>
                    <input type="text" name="username" class="form-control" placeholder="อย่างน้อย 4 ตัวอักษรขึ้นไป" minlength="4" required>
                </div>
                <div class="form-group full-width">
                    <label>รหัสผ่าน (Password)</label>
                    <div class="password-container">
                        <input type="password" name="password" id="reg-password" class="form-control" placeholder="6 ตัวขึ้นไป (ต้องมีตัวใหญ่อย่างน้อย 1 ตัว)" minlength="6" required>
                        <span class="toggle-password" onclick="toggleVisibility('reg-password', this)">👁️</span>
                    </div>
                </div>
                <div class="form-group">
                    <label>ชื่อจริง</label>
                    <input type="text" name="first_name" class="form-control" placeholder="ชื่อจริง" required>
                </div>
                <div class="form-group">
                    <label>นามสกุล</label>
                    <input type="text" name="last_name" class="form-control" placeholder="นามสกุล" required>
                </div>
                <div class="form-group">
                    <label>เบอร์โทรศัพท์ (10 หลัก)</label>
                    <input type="tel" name="phone" class="form-control" placeholder="เช่น 0812345678" pattern="[0-9]{10}" maxlength="10" title="กรุณากรอกเบอร์โทรศัพท์ตัวเลข 10 หลักเท่านั้น" required>
                </div>
                <div class="form-group">
                    <label>อีเมล</label>
                    <input type="email" name="email" class="form-control" placeholder="example@email.com" required>
                </div>
            </div>
            
            <button type="submit" class="btn-main">ยืนยันการสมัครสมาชิก</button>
        </form>
        <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0;">
        <p style="margin-bottom: 10px; color: #94a3b8; font-size: 13px; text-align: center;">มีบัญชีอยู่แล้ว?</p>
        <a href="{{ url_for('login') }}" class="login-link">เข้าสู่ระบบที่นี่</a>
    </div>
    
    <script>
        function toggleVisibility(inputId, icon) {
            var x = document.getElementById(inputId);
            if (x.type === "password") { x.type = "text"; icon.innerHTML = "👁️‍🗨️"; }
            else { x.type = "password"; icon.innerHTML = "👁️"; }
        }

        const input = document.getElementById('profile_image');
        const canvas = document.getElementById('preview-canvas');
        const ctx = canvas.getContext('2d');
        const defaultIcon = document.getElementById('default-icon');
        const croppedInput = document.getElementById('cropped_image');
        const dragHint = document.getElementById('drag-hint');

        let img = new Image();
        let scale = 1;
        let imgX = 0, imgY = 0;
        let isDragging = false;
        let startX, startY;

        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    img.onload = function() {
                        scale = Math.max(canvas.width / img.width, canvas.height / img.height);
                        imgX = (canvas.width - img.width * scale) / 2;
                        imgY = (canvas.height - img.height * scale) / 2;
                        defaultIcon.style.display = 'none';
                        canvas.style.display = 'block';
                        dragHint.style.display = 'block';
                        drawImage();
                    }
                    img.src = event.target.result;
                }
                reader.readAsDataURL(file);
            }
        });

        function drawImage() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, imgX, imgY, img.width * scale, img.height * scale);
            croppedInput.value = canvas.toDataURL('image/jpeg', 0.9);
        }

        function restrictMovement() {
            if (imgX > 0) imgX = 0;
            if (imgX < canvas.width - img.width * scale) imgX = canvas.width - img.width * scale;
            if (imgY > 0) imgY = 0;
            if (imgY < canvas.height - img.height * scale) imgY = canvas.height - img.height * scale;
        }

        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.offsetX - imgX;
            startY = e.offsetY - imgY;
        });

        canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            imgX = e.offsetX - startX;
            imgY = e.offsetY - startY;
            restrictMovement();
            drawImage();
        });

        window.addEventListener('mouseup', () => isDragging = false);

        canvas.addEventListener('touchstart', (e) => {
            isDragging = true;
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            startX = (touch.clientX - rect.left) * scaleX - imgX;
            startY = (touch.clientY - rect.top) * scaleY - imgY;
        }, {passive: true});

        canvas.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            imgX = (touch.clientX - rect.left) * scaleX - startX;
            imgY = (touch.clientY - rect.top) * scaleY - startY;
            restrictMovement();
            drawImage();
            e.preventDefault(); 
        }, {passive: false});

        window.addEventListener('touchend', () => isDragging = false);
    </script>
</body>
</html>
"""

# -------------------------------------------------------------------------
# ปรับปรุง HTML_PROFILE: จัดรูปแบบเต็มจอแบบ 2 คอลัมน์ (ซ้าย-ขวา) ไม่ให้ยาวเกินไป
# -------------------------------------------------------------------------
HTML_PROFILE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>โปรไฟล์ของฉัน - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; padding: 20px; color: var(--text-main); min-height: 100vh; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }
        
        /* ขยายกล่องหลักให้เต็มจอและจัดกึ่งกลาง */
        .container { background: rgba(15, 23, 42, 0.9); padding: 30px 40px; max-width: 950px; width: 100%; border-radius: 24px; box-shadow: 0 25px 50px rgba(0,0,0,0.7); backdrop-filter: blur(14px); border: 1px solid rgba(255, 255, 255, 0.1); }
        
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 15px; margin-bottom: 25px; }
        .brand-link { text-decoration: none; color: #fff; font-size: 22px; font-weight: 600; }
        .back-link { text-decoration: none; color: #60a5fa; font-size: 14px; font-weight: 500; }
        
        /* ระบบจัดเรียงแบบ 2 คอลัมน์ (ซ้าย-ขวา) */
        .profile-grid-layout { display: grid; grid-template-columns: 280px 1fr; gap: 35px; align-items: start; }
        @media (max-width: 768px) { .profile-grid-layout { grid-template-columns: 1fr; } }
        
        /* ฝั่งซ้าย: จัดการรูปภาพและ Canvas */
        .profile-left-col { background: rgba(30, 41, 59, 0.5); padding: 25px; border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.08); text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .preview-circle { width: 140px; height: 140px; border-radius: 50%; background: rgba(30, 41, 59, 0.8); border: 3px solid #ef4444; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.4); position: relative; }
        
        #preview-canvas { display: none; width: 100%; height: 100%; cursor: grab; object-fit: cover; }
        #preview-canvas:active { cursor: grabbing; }

        .upload-btn { background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 13px; transition: 0.3s; display: inline-block; font-family: 'Prompt'; font-weight: 500; margin-top: 5px; }
        .upload-btn:hover { background: #ef4444; color: #fff; border-color: #ef4444; }
        input[type="file"] { display: none; }

        /* ฝั่งขวา: ฟอร์มกรอกข้อมูลแบบ Grid 2 คอลัมน์ย่อย */
        .profile-right-col { display: flex; flex-direction: column; gap: 15px; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .form-group { text-align: left; }
        .form-group.full-width { grid-column: span 2; }
        .form-group label { display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 5px; }
        
        .form-control { width: 100%; padding: 10px 14px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 13px; color: #fff; }
        .form-control:focus { outline: none; border-color: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.3); }
        
        .password-container { position: relative; width: 100%; }
        .toggle-password { position: absolute; right: 12px; top: 10px; cursor: pointer; color: #94a3b8; font-size: 14px; }
        
        .btn-submit { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); margin-top: 10px; transition: 0.3s; }
        .btn-submit:hover { opacity: 0.9; transform: translateY(-1px); }
        
        .alert { background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 10px; border-radius: 10px; margin-bottom: 20px; text-align: center; border: 1px solid rgba(16, 185, 129, 0.4); font-size: 13px; }
        .alert-error { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 10px; margin-bottom: 20px; text-align: center; border: 1px solid rgba(239, 68, 68, 0.4); font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="{{ url_for('index') }}" class="brand-link">⚙️ จัดการโปรไฟล์ส่วนตัว</a>
            <a href="{{ url_for('index') }}" class="back-link">← กลับหน้าแรก</a>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="{{ 'alert-error' if category == 'error' else 'alert' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" enctype="multipart/form-data">
            <div class="profile-grid-layout">
                
                <!-- คอลัมน์ซ้าย: รูปโปรไฟล์และการขยับภาพ -->
                <div class="profile-left-col">
                    <div class="preview-circle">
                        {% if user.profile_image %}
                            <img id="current-profile-img" src="{{ url_for('static', filename='uploads/' + user.profile_image) }}" alt="Profile" style="width: 100%; height: 100%; object-fit: cover;">
                        {% else %}
                            <span id="default-icon" style="font-size: 55px;">👤</span>
                        {% endif %}
                        <canvas id="preview-canvas" width="400" height="400"></canvas>
                    </div>
                    
                    <input type="hidden" name="cropped_image" id="cropped_image">
                    <p id="drag-hint" style="font-size: 11px; color: #fcd34d; margin: 0 0 10px 0; display: none;">* ลากหรือใช้นิ้วเลื่อนเพื่อขยับรูปได้</p>
                    
                    <label for="profile_image" class="upload-btn">📷 เปลี่ยนรูปโปรไฟล์</label>
                    <input type="file" name="profile_image" id="profile_image" accept="image/*">
                </div>

                <!-- คอลัมน์ขวา: ฟอร์มกรอกข้อมูล -->
                <div class="profile-right-col">
                    <div class="form-group full-width">
                        <label>ชื่อผู้ใช้งาน (Username) - ไม่สามารถเปลี่ยนได้</label>
                        <input type="text" value="{{ user.username }}" class="form-control" disabled style="opacity: 0.7; cursor: not-allowed;">
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>รหัสผ่านใหม่ (อย่างน้อย 6 ตัว และมีตัว A-Z)</label>
                            <div class="password-container">
                                <input type="password" name="password" id="profile-pass" placeholder="รหัสผ่านใหม่" class="form-control" style="padding-right: 35px;">
                                <span class="toggle-password" onclick="toggleVisibility('profile-pass', this)">👁️</span>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>ยืนยันรหัสผ่านใหม่</label>
                            <div class="password-container">
                                <input type="password" name="confirm_password" id="profile-confirm-pass" placeholder="ยืนยันรหัสผ่าน" class="form-control" style="padding-right: 35px;">
                                <span class="toggle-password" onclick="toggleVisibility('profile-confirm-pass', this)">👁️</span>
                            </div>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label>ชื่อจริง</label>
                            <input type="text" name="first_name" value="{{ user.first_name or '' }}" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label>นามสกุล</label>
                            <input type="text" name="last_name" value="{{ user.last_name or '' }}" class="form-control" required>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label>เบอร์โทรศัพท์ (10 หลัก)</label>
                            <input type="tel" name="phone" value="{{ user.phone or '' }}" class="form-control" pattern="[0-9]{10}" maxlength="10" title="กรุณากรอกเบอร์โทรศัพท์ตัวเลข 10 หลักเท่านั้น" required>
                        </div>
                        <div class="form-group">
                            <label>อีเมล</label>
                            <input type="email" name="email" value="{{ user.email or '' }}" class="form-control" required>
                        </div>
                    </div>

                    <button type="submit" class="btn-submit">💾 บันทึกการแก้ไขข้อมูล</button>
                </div>

            </div>
        </form>
    </div>
    
    <!-- JavaScript สำหรับระบบตัดภาพ และสลับโชว์ Canvas -->
    <script>
        function toggleVisibility(inputId, icon) {
            var x = document.getElementById(inputId);
            if (x.type === "password") { x.type = "text"; icon.innerHTML = "👁️‍🗨️"; }
            else { x.type = "password"; icon.innerHTML = "👁️"; }
        }

        const input = document.getElementById('profile_image');
        const canvas = document.getElementById('preview-canvas');
        const ctx = canvas.getContext('2d');
        const defaultIcon = document.getElementById('default-icon');
        const currentImg = document.getElementById('current-profile-img');
        const croppedInput = document.getElementById('cropped_image');
        const dragHint = document.getElementById('drag-hint');

        let img = new Image();
        let scale = 1;
        let imgX = 0, imgY = 0;
        let isDragging = false;
        let startX, startY;

        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    img.onload = function() {
                        scale = Math.max(canvas.width / img.width, canvas.height / img.height);
                        imgX = (canvas.width - img.width * scale) / 2;
                        imgY = (canvas.height - img.height * scale) / 2;
                        
                        if(defaultIcon) defaultIcon.style.display = 'none';
                        if(currentImg) currentImg.style.display = 'none';
                        
                        canvas.style.display = 'block';
                        dragHint.style.display = 'block';
                        drawImage();
                    }
                    img.src = event.target.result;
                }
                reader.readAsDataURL(file);
            }
        });

        function drawImage() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, imgX, imgY, img.width * scale, img.height * scale);
            croppedInput.value = canvas.toDataURL('image/jpeg', 0.9);
        }

        function restrictMovement() {
            if (imgX > 0) imgX = 0;
            if (imgX < canvas.width - img.width * scale) imgX = canvas.width - img.width * scale;
            if (imgY > 0) imgY = 0;
            if (imgY < canvas.height - img.height * scale) imgY = canvas.height - img.height * scale;
        }

        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.offsetX - imgX;
            startY = e.offsetY - imgY;
        });

        canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            imgX = e.offsetX - startX;
            imgY = e.offsetY - startY;
            restrictMovement();
            drawImage();
        });

        window.addEventListener('mouseup', () => isDragging = false);

        canvas.addEventListener('touchstart', (e) => {
            isDragging = true;
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            startX = (touch.clientX - rect.left) * scaleX - imgX;
            startY = (touch.clientY - rect.top) * scaleY - imgY;
        }, {passive: true});

        canvas.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            imgX = (touch.clientX - rect.left) * scaleX - startX;
            imgY = (touch.clientY - rect.top) * scaleY - startY;
            restrictMovement();
            drawImage();
            e.preventDefault(); 
        }, {passive: false});

        window.addEventListener('touchend', () => isDragging = false);
    </script>
</body>
</html>
"""

HTML_PRODUCT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>{{ product.name }} - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; color: var(--text-main); margin: 0; padding: 40px 20px; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { background: rgba(15, 23, 42, 0.85); padding: 35px; max-width: 1000px; width: 100%; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 20px; margin-bottom: 30px; flex-wrap: wrap; gap: 15px; }
        .brand { display: flex; align-items: center; gap: 20px; text-decoration: none; cursor: pointer; }
        .brand img { width: 90px; height: 90px; object-fit: contain; border-radius: 16px; background: #1e293b; padding: 6px; border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .brand h1 { margin: 0; font-size: 26px; font-weight: 600; color: #ffffff; letter-spacing: 0.5px; }
        .product-content { display: flex; gap: 40px; flex-wrap: wrap; align-items: center; }
        .product-image { flex: 1; min-width: 280px; text-align: center; background: rgba(30, 41, 59, 0.6); padding: 20px; border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.1); display: flex; align-items: center; justify-content: center; }
        .product-image img { width: 100%; max-width: 320px; object-fit: contain; border-radius: 10px; }
        .product-info { flex: 1; min-width: 280px; display: flex; flex-direction: column; justify-content: center; }
        .product-info h1 { margin: 0 0 10px 0; color: #fff; font-size: 26px; }
        .badge { display: inline-block; padding: 5px 15px; background: rgba(255, 255, 255, 0.1); color: var(--text-secondary); border-radius: 20px; font-size: 13px; margin-bottom: 20px; border: 1px solid rgba(255, 255, 255, 0.15); width: fit-content; }
        .price { font-size: 32px; font-weight: 600; color: #4ade80; margin: 15px 0; }
        .stock-info { font-size: 15px; color: var(--text-secondary); margin-bottom: 20px; }
        .qty-container { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 20px; }
        .qty-btn { background: rgba(255, 255, 255, 0.1); color: white; border: 1px solid rgba(255, 255, 255, 0.2); padding: 6px 14px; border-radius: 8px; font-weight: bold; cursor: pointer; font-family: 'Prompt'; }
        .qty-input { width: 70px; padding: 8px; background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; color: #fff; font-family: 'Prompt'; font-size: 16px; text-align: center; font-weight: bold; }
        .qty-input::-webkit-inner-spin-button, 
        .qty-input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
        .qty-input { -moz-appearance: textfield; }
        .add-btn { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 14px 25px; border-radius: 12px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); text-align: center; width: 100%; }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(239, 68, 68, 0.4); text-align: center; line-height: 1.5; word-break: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="{{ url_for('index') }}" class="brand">
                <img src="{{ url_for('static', filename='Logo.png') }}" alt="logo" onerror="this.src='{{ url_for('static', filename='images/logo.png') }}'">
                <h1>WHEY STATION</h1>
            </a>
            <a href="{{ url_for('index') }}" style="color: #60a5fa; text-decoration: none; font-size: 14px; font-weight: 500;">← กลับไปหน้ารวมสินค้า</a>
        </div>
        
        <div class="product-content">
            <div class="product-image">
                {% if product.image_file %}
                    <img src="{{ url_for('static', filename='images/' + product.image_file) }}" alt="{{ product.name }}">
                {% endif %}
            </div>
            <div class="product-info">
                <span class="badge">{{ product.category }}</span>
                <h1>{{ product.name }}</h1>
                <p style="color: var(--text-secondary); line-height: 1.6; font-size: 14px;">ซัดปุ๊บ กล้ามปูดทะลุเสื้อ! สลัดร่างแห้งสู่จุดสูงสุดของห่วงโซ่อาหาร</p>
                <div class="price">฿{{ "{:,.0f}".format(product.price) }} <span style="font-size: 13px; color: var(--text-secondary); font-weight: normal;">(ราคารวม Vat 7%)</span></div>
                <div class="stock-info">
                    <strong>สถานะสินค้า:</strong> 
                    {% if product.stock > 0 %}
                        <span style="color: #4ade80;">มีสินค้า (เหลือ {{ product.stock }} ชิ้น)</span>
                    {% else %}
                        <span style="color: #f87171;">สินค้าหมดชั่วคราว</span>
                    {% endif %}
                </div>
                {% with messages = get_flashed_messages() %}
                    {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
                {% endwith %}
                {% if product.stock > 0 %}
                <form action="{{ url_for('add_to_cart', product_id=product.id) }}" method="POST">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
                        <label for="quantity" style="color: var(--text-secondary); font-size: 14px; font-weight: 500;">จำนวน:</label>
                        <div class="qty-container">
                            <button type="button" class="qty-btn" onclick="changeQty(-1, {{ product.stock }})">-</button>
                            <input type="number" id="quantity" name="quantity" value="1" min="1" max="{{ product.stock }}" class="qty-input">
                            <button type="button" class="qty-btn" onclick="changeQty(1, {{ product.stock }})">+</button>
                        </div>
                        <span style="color: var(--text-secondary); font-size: 13px;">ชิ้น</span>
                    </div>
                    <button type="submit" class="add-btn">🛒 เพิ่มลงตะกร้าสินค้า</button>
                </form>
                {% else %}
                    <button class="add-btn" style="background: #334155; color: #64748b; cursor: not-allowed;" disabled>สินค้าหมด</button>
                {% endif %}
            </div>
        </div>
    </div>
    <script>
        function changeQty(amount, maxStock) {
            var input = document.getElementById('quantity');
            var currentVal = parseInt(input.value) || 1;
            var newVal = currentVal + amount;
            if (newVal < 1) newVal = 1;
            if (newVal > maxStock) newVal = maxStock;
            input.value = newVal;
        }
    </script>
</body>
</html>
"""

HTML_CART = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ตะกร้าสินค้า - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; padding: 40px 20px; color: var(--text-main); }
        .container { background: rgba(15, 23, 42, 0.85); padding: 35px; max-width: 1000px; margin: auto; border-radius: 24px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 20px; margin-bottom: 25px; flex-wrap: wrap; gap: 15px; }
        .brand { display: flex; align-items: center; gap: 20px; text-decoration: none; cursor: pointer; }
        .brand img { width: 90px; height: 90px; object-fit: contain; border-radius: 16px; background: #1e293b; padding: 6px; border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .brand h1 { margin: 0; font-size: 26px; font-weight: 600; color: #ffffff; letter-spacing: 0.5px; }
        .back-link { text-decoration: none; color: #60a5fa; font-weight: 500; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; background: rgba(30, 41, 59, 0.6); border-radius: 14px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 25px; }
        th, td { padding: 15px; text-align: left; font-size: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: #f8fafc; }
        th { background: rgba(15, 23, 42, 0.8); color: var(--text-secondary); font-weight: 600; }
        .qty-btn { background: rgba(255, 255, 255, 0.1); color: white; border: 1px solid rgba(255, 255, 255, 0.2); padding: 4px 12px; border-radius: 6px; text-decoration: none; font-weight: bold; cursor: pointer; font-family: 'Prompt'; }
        .cart-qty-input { width: 70px; padding: 6px; background: rgba(15,23,42,0.8); color: #fff; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; text-align: center; font-family: 'Prompt'; font-weight: bold; }
        .cart-qty-input::-webkit-inner-spin-button, 
        .cart-qty-input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
        .cart-qty-input { -moz-appearance: textfield; }
        .remove-btn { color: #f87171; text-decoration: none; font-size: 13px; }
        .checkout-box { background: rgba(30, 41, 59, 0.7); padding: 20px 25px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.1); display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
        .checkout-row { display: flex; justify-content: space-between; width: 100%; max-width: 450px; font-size: 15px; color: var(--text-secondary); }
        .checkout-row.total { font-size: 20px; font-weight: bold; color: #4ade80; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 10px; }
        .checkout-btn { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; text-decoration: none; padding: 12px 30px; border-radius: 12px; font-weight: 600; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); margin-top: 10px; text-align: center; display: inline-block; }
        .empty-state { text-align: center; padding: 50px 0; color: var(--text-secondary); }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(239, 68, 68, 0.4); text-align: center; line-height: 1.5; word-break: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="{{ url_for('index') }}" class="brand">
                <img src="{{ url_for('static', filename='Logo.png') }}" alt="logo" onerror="this.src='{{ url_for('static', filename='images/logo.png') }}'">
                <h1>WHEY STATION</h1>
            </a>
            <a href="{{ url_for('index') }}" class="back-link">← กลับไปเลือกซื้อสินค้าเพิ่ม</a>
        </div>
        <div id="alert-box">
            {% with messages = get_flashed_messages() %}
                {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
            {% endwith %}
        </div>
        <div id="cart-content">
        {% if items %}
        <table>
            <tr>
                <th>สินค้า</th>
                <th>ราคาต่อหน่วย</th>
                <th style="text-align: center;">จำนวน</th>
                <th>ราคารวม</th>
                <th>จัดการ</th>
            </tr>
            {% for item in items %}
            <tr id="row-{{ item.product.id }}">
                <td><strong>{{ item.product.name }}</strong></td>
                <td>฿{{ "{:,.2f}".format(item.product.price) }}</td>
                <td style="text-align: center;">
                    <div style="display:inline-flex; gap:8px; align-items:center; justify-content:center;">
                        <button type="button" class="qty-btn" onclick="updateCart({{ item.product.id }}, 'decrease')">-</button>
                        <input type="number" id="qty-{{ item.product.id }}" value="{{ item.quantity }}" min="1" max="{{ item.product.stock }}" oninput="updateCartInput({{ item.product.id }}, this.value)" class="cart-qty-input">
                        <button type="button" class="qty-btn" onclick="updateCart({{ item.product.id }}, 'increase')">+</button>
                    </div>
                </td>
                <td><strong id="subtotal-{{ item.product.id }}" style="color: #4ade80;">฿{{ "{:,.2f}".format(item.subtotal) }}</strong></td>
                <td><button type="button" onclick="updateCart({{ item.product.id }}, 'remove')" class="remove-btn" style="background:none; border:none; cursor:pointer;">🗑️ ลบ</button></td>
            </tr>
            {% endfor %}
        </table>
        <div class="checkout-box">
            <div class="checkout-row total">
                <span>ยอดรวมสุทธิทั้งสิ้น: <span style="font-size: 13px; font-weight: normal; color: var(--text-secondary);">(ราคารวม Vat 7%)</span></span>
                <span id="grand-total">฿{{ "{:,.2f}".format(total) }}</span>
            </div>
            <a href="{{ url_for('checkout', total=total) }}" class="checkout-btn">ดำเนินการชำระเงิน →</a>
        </div>
        {% else %}
        <div class="empty-state">
            <h3>ตะกร้าสินค้าว่างเปล่า</h3>
            <p>คุณยังไม่ได้เพิ่มสินค้าใดๆ ลงในตะกร้า</p>
            <a href="{{ url_for('index') }}" class="checkout-btn" style="display: inline-block; margin-top: 15px;">ไปเลือกซื้อสินค้า</a>
        </div>
        {% endif %}
        </div>
    </div>
    <script>
        function updateCart(productId, action) {
            fetch('/update_cart_ajax/' + productId + '/' + action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.items[productId]) {
                        document.getElementById('qty-' + productId).value = data.items[productId].quantity;
                        document.getElementById('subtotal-' + productId).innerText = '฿' + data.items[productId].subtotal.toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    } else {
                        const row = document.getElementById('row-' + productId);
                        if (row) row.remove();
                    }
                    document.getElementById('grand-total').innerText = '฿' + data.total.toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    document.getElementById('cart-count').innerText = data.cart_count;
                    if (data.total === 0) {
                        location.reload();
                    }
                } else if (data.message) {
                    alert(data.message);
                }
            });
        }

        function updateCartInput(productId, qty) {
            fetch('/update_cart_input_ajax/' + productId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ quantity: qty })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.items[productId]) {
                        document.getElementById('qty-' + productId).value = data.items[productId].quantity;
                        document.getElementById('subtotal-' + productId).innerText = '฿' + data.items[productId].subtotal.toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    }
                    document.getElementById('grand-total').innerText = '฿' + data.total.toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    document.getElementById('cart-count').innerText = data.cart_count;
                } else if (data.message) {
                    alert(data.message);
                }
            });
        }
    </script>
</body>
</html>
"""

HTML_CHECKOUT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ชำระเงิน - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; padding: 40px 20px; color: var(--text-main); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { background: rgba(15, 23, 42, 0.9); padding: 40px; max-width: 1100px; width: 100%; border-radius: 24px; box-shadow: 0 25px 50px rgba(0,0,0,0.7); backdrop-filter: blur(14px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 20px; margin-bottom: 30px; flex-wrap: wrap; gap: 15px; }
        .brand { display: flex; align-items: center; gap: 20px; text-decoration: none; }
        .brand img { width: 85px; height: 85px; object-fit: contain; border-radius: 14px; background: #1e293b; padding: 6px; border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .brand h1 { margin: 0; font-size: 24px; font-weight: 600; color: #ffffff; letter-spacing: 0.5px; }
        
        .checkout-grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: 30px; align-items: start; }
        @media (max-width: 850px) { .checkout-grid { grid-template-columns: 1fr; } }
        
        .checkout-column { background: rgba(30, 41, 59, 0.6); padding: 25px; border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .section-title { font-size: 18px; font-weight: 600; color: #fff; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        
        .order-summary-list { max-height: 250px; overflow-y: auto; margin-bottom: 20px; padding-right: 5px; }
        .order-item-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }
        .total-row { display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: bold; color: #4ade80; border-top: 2px solid rgba(255,255,255,0.1); padding-top: 15px; margin-top: 10px; }
        
        .timer-box { background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); padding: 12px; border-radius: 12px; margin-bottom: 20px; text-align: center; font-weight: bold; color: #fca5a5; font-size: 15px; }
        .qr-section { text-align: center; margin-bottom: 25px; background: rgba(15, 23, 42, 0.6); padding: 20px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08); }
        .qr-section img { border-radius: 12px; background: #fff; padding: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        
        .form-control { width: 100%; padding: 12px 15px; margin-bottom: 14px; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 14px; color: #fff; }
        .form-control:focus { outline: none; border-color: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.3); }
        textarea.form-control { height: 80px; resize: none; }
        
        .btn-submit { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; width: 100%; padding: 15px; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); transition: 0.3s; }
        .btn-submit:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn-submit:disabled { background: #334155; color: #64748b; cursor: not-allowed; box-shadow: none; transform: none; }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid rgba(239, 68, 68, 0.4); font-size: 13px; text-align: left; line-height: 1.5; word-break: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="{{ url_for('index') }}" class="brand">
                <img src="{{ url_for('static', filename='Logo.png') }}" alt="logo" onerror="this.src='{{ url_for('static', filename='images/logo.png') }}'">
                <h1>WHEY STATION - ดำเนินการชำระเงิน</h1>
            </a>
            <a href="{{ url_for('cart') }}" style="color: #60a5fa; text-decoration: none; font-size: 14px; font-weight: 500;">← กลับไปหน้าตะกร้าสินค้า</a>
        </div>
        
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
        {% endwith %}

        <div class="checkout-grid">
            <div class="checkout-column">
                <h3 class="section-title">🛒 สรุปรายการคำสั่งซื้อของคุณ</h3>
                <div class="order-summary-list">
                    {% for item in items %}
                    <div class="order-item-row">
                        <div>
                            <strong>{{ item.product.name }}</strong><br>
                            <span style="color: var(--text-secondary); font-size: 12px;">จำนวน: {{ item.quantity }} ชิ้น</span>
                        </div>
                        <div style="text-align: right; color: #4ade80; font-weight: 600;">
                            ฿{{ "{:,.2f}".format(item.subtotal) }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="total-row">
                    <div>
                        <span>ยอดชำระสุทธิทั้งสิ้น</span><br>
                        <span style="font-size: 12px; font-weight: normal; color: var(--text-secondary);">(ราคารวม Vat 7%)</span>
                    </div>
                    <span>฿{{ "{:,.2f}".format(total_price) }}</span>
                </div>

                <div style="margin-top: 25px; padding: 15px; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; font-size: 13px; color: #93c5fd; line-height: 1.6;">
                    💡 <strong>คำแนะนำในการชำระเงิน:</strong><br>
                    1. สแกน QR Code ด้วยแอปพลิเคชันธนาคารใดก็ได้ (ยอดเงินจะถูกระบุให้อัตโนมัติ)<br>
                    2. ตรวจสอบชื่อผู้รับโอนให้ถูกต้อง<br>
                    3. กรอกข้อมูลจัดส่งและแนบสลิปหลักฐานการโอนเงินให้ครบถ้วนภายในเวลาที่กำหนด
                </div>
            </div>

            <div class="checkout-column">
                <h3 class="section-title">💳 ช่องทางการชำระเงินผ่าน PromptPay</h3>
                
                <div class="timer-box" id="timer-container">
                    ⏱️ กรุณาชำระเงินภายใน: <span id="countdown">05:00</span> นาที
                </div>

                <div class="qr-section">
                    <p style="font-weight: bold; margin-top: 0; color: #fff; font-size: 14px; margin-bottom: 10px;">สแกน QR Code เพื่อชำระเงิน</p>
                    <img src="https://promptpay.io/0917921736/{{ total_price }}.png" width="200" alt="PromptPay QR Code" onerror="this.onerror=null; this.src='{{ url_for('static', filename='qr.jpg') }}';">
                </div>

                <form method="POST" enctype="multipart/form-data" id="checkout-form">
                    <input type="hidden" name="total_price" value="{{ total_price }}">
                    <p style="font-weight: bold; color: #fff; margin-bottom: 12px; font-size: 14px;">กรอกข้อมูลจัดส่งและแนบสลิป</p>
                    <input type="text" name="name" class="form-control" placeholder="ชื่อ-นามสกุล (ผู้รับสินค้า)" required>
                    <input type="tel" name="phone" class="form-control" placeholder="เบอร์โทรศัพท์ติดต่อ (10 หลัก)" pattern="[0-9]{10}" maxlength="10" title="กรุณากรอกเบอร์โทรศัพท์ตัวเลข 10 หลักเท่านั้น" required>
                    <textarea name="address" class="form-control" placeholder="ที่อยู่จัดส่งสินค้าโดยละเอียด (บ้านเลขที่, ถนน, ตำบล, อำเภอ, จังหวัด, รหัสไปรษณีย์)" required></textarea>
                    
                    <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary); display: block; margin-bottom: 5px;">แนบสลิปหลักฐานการโอนเงิน:</label>
                    <input type="file" name="slip" id="slip-input" accept="image/*" required style="margin-bottom: 20px; color: #fff; font-size: 13px;"><br>
                    
                    <button type="submit" id="submit-btn" class="btn-submit">✅ ยืนยันการสั่งซื้อ</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        let timeLeft = 300;
        const countdownEl = document.getElementById('countdown');
        const timerContainer = document.getElementById('timer-container');
        const submitBtn = document.getElementById('submit-btn');
        const slipInput = document.getElementById('slip-input');

        const timer = setInterval(() => {
            let minutes = Math.floor(timeLeft / 60);
            let seconds = timeLeft % 60;

            minutes = minutes < 10 ? '0' + minutes : minutes;
            seconds = seconds < 10 ? '0' + seconds : seconds;

            countdownEl.innerHTML = minutes + ':' + seconds;

            if (timeLeft <= 0) {
                clearInterval(timer);
                timerContainer.style.background = 'rgba(239, 68, 68, 0.4)';
                timerContainer.innerHTML = '❌ หมดเวลาชำระเงิน กรุณากลับไปทำรายการในตะกร้าใหม่';
                submitBtn.disabled = true;
                slipInput.disabled = true;
            }
            timeLeft--;
        }, 1000);
    </script>
</body>
</html>
"""

HTML_ADMIN = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>แผงควบคุมแอดมิน - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.8)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; padding: 30px 20px; color: var(--text-main); }
        .container { max-width: 1400px; margin: auto; }
        .top-header { background: rgba(15, 23, 42, 0.9); padding: 20px 30px; border-radius: 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 10px 30px rgba(0,0,0,0.5); backdrop-filter: blur(10px); }
        .brand-link { text-decoration: none; color: #fff; font-size: 24px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
        
        .admin-layout { display: flex; gap: 25px; align-items: flex-start; }
        
        .sidebar { width: 280px; background: rgba(15, 23, 42, 0.9); border-radius: 20px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); flex-shrink: 0; position: sticky; top: 20px; }
        .sidebar h3 { font-size: 15px; color: var(--text-secondary); margin: 0 0 15px 10px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }
        .menu-list { display: flex; flex-direction: column; gap: 8px; }
        .menu-btn { background: transparent; border: none; color: var(--text-secondary); text-align: left; padding: 14px 18px; border-radius: 12px; font-family: 'Prompt'; font-size: 15px; font-weight: 500; cursor: pointer; transition: 0.3s; display: flex; align-items: center; gap: 12px; width: 100%; text-decoration: none; box-sizing: border-box; }
        .menu-btn:hover { background: rgba(239, 68, 68, 0.15); color: #fff; }
        .menu-btn.active { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); }
        .menu-divider { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 15px 0; }

        .main-content { flex: 1; background: rgba(15, 23, 42, 0.85); padding: 35px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); min-width: 0; box-shadow: 0 15px 35px rgba(0,0,0,0.5); }
        
        .tab-pane { display: none; }
        .tab-pane.active { display: block; animation: fadeIn 0.4s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

        .sales-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .sales-box { color: white; padding: 22px; border-radius: 16px; box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
        .sales-box h2 { margin: 0 0 6px 0; font-size: 14px; font-weight: 400; opacity: 0.9; }
        .sales-box .amount { font-size: 26px; font-weight: 600; margin: 0; }
        
        .filter-box { background: rgba(30, 41, 59, 0.7); padding: 20px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 25px; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }
        h2.section-title { font-size: 22px; font-weight: 600; margin-top: 0; margin-bottom: 20px; color: #fff; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; }
        
        table { width: 100%; border-collapse: collapse; background: rgba(30, 41, 59, 0.6); border-radius: 14px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.1); margin-top: 10px; }
        th, td { padding: 14px; text-align: left; font-size: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: #f8fafc; }
        th { background: rgba(15, 23, 42, 0.85); color: var(--text-secondary); font-weight: 600; }
        
        .badge-stock-low { color: #fca5a5; font-weight: 600; background: rgba(239, 68, 68, 0.2); padding: 4px 10px; border-radius: 8px; font-size: 12px; border: 1px solid rgba(239, 68, 68, 0.3); }
        .rank-badge { display: inline-block; padding: 4px 10px; border-radius: 8px; font-weight: bold; font-size: 13px; }
        .rank-1 { background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }
        .rank-2 { background: rgba(148, 163, 184, 0.2); color: #e2e8f0; border: 1px solid rgba(148, 163, 184, 0.4); }
        .rank-3 { background: rgba(217, 119, 6, 0.2); color: #fb923c; border: 1px solid rgba(217, 119, 6, 0.4); }
        
        .status-badge { padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }
        .status-pending { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .status-packing { background: rgba(99, 102, 241, 0.2); color: #818cf8; }
        .status-shipping { background: rgba(14, 165, 233, 0.2); color: #38bdf8; }
        .status-success { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .status-cancel { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        
        .status-form { display: flex; gap: 8px; align-items: center; }
        .status-select, .stock-input, .form-control { padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.2); font-family: 'Prompt'; font-size: 14px; background: rgba(30, 41, 59, 0.9); color: #fff; width: 100%; box-sizing: border-box; }
        
        .save-btn { background: var(--primary-color); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-family: 'Prompt'; font-weight: 600; font-size: 14px; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); transition: 0.3s; }
        .save-btn:hover { opacity: 0.9; transform: translateY(-1px); }
        .delete-btn { background: #ef4444; color: white; text-decoration: none; padding: 6px 12px; border-radius: 8px; font-size: 13px; font-weight: 500; display: inline-block; }
        
        .admin-form-box { background: rgba(30, 41, 59, 0.7); padding: 25px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 25px; }
        .admin-form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .password-container { position: relative; width: 100%; }
        .toggle-password { position: absolute; right: 12px; top: 12px; cursor: pointer; color: #94a3b8; font-size: 14px; }
        .slip-link { color: #60a5fa; text-decoration: none; font-weight: 500; }
        .alert { background: #064e3b; color: #34d399; padding: 14px; border-radius: 14px; margin-bottom: 25px; text-align: center; border: 1px solid #10b981; font-weight: 500; box-shadow: 0 4px 15px rgba(0,0,0,0.3); line-height: 1.5; word-break: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <div class="top-header">
            <a href="{{ url_for('admin') }}" class="brand-link">⚡ WHEY STATION - ADMIN PANEL</a>
            <div style="display: flex; gap: 15px; align-items: center;">
                <span style="color: #94a3b8; font-size: 14px;">👤 แอดมิน: <strong style="color: #fff;">{{ session.username }}</strong></span>
                <a href="{{ url_for('logout') }}" style="background: rgba(239, 68, 68, 0.2); color: #fca5a5; text-decoration: none; padding: 8px 16px; border-radius: 10px; font-weight: 500; font-size: 13px; border: 1px solid rgba(239, 68, 68, 0.4);">ออกจากระบบ</a>
            </div>
        </div>

        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
        {% endwith %}

        <div class="admin-layout">
            <div class="sidebar">
                <h3>เมนูจัดการระบบ</h3>
                <div class="menu-list">
                    <button class="menu-btn active" onclick="switchTab('dashboard', this)">📊 สรุปยอดขาย & สถิติ</button>
                    <button class="menu-btn" onclick="switchTab('orders', this)">📝 จัดการคำสั่งซื้อ</button>
                    <button class="menu-btn" onclick="switchTab('products', this)">📦 จัดการสต๊อกสินค้า</button>
                    <button class="menu-btn" onclick="switchTab('add-product', this)">➕ เพิ่มสินค้าใหม่</button>
                    <button class="menu-btn" onclick="switchTab('add-admin', this)">🛡️ เพิ่มบัญชีแอดมิน</button>
                    <hr class="menu-divider">
                    <a href="{{ url_for('admin_users') }}" class="menu-btn" style="background: rgba(37, 99, 235, 0.2); color: #60a5fa; border: 1px solid rgba(37, 99, 235, 0.4);">👥 จัดการสมาชิกทั้งหมด</a>
                    <a href="{{ url_for('index') }}" class="menu-btn">กลับสู่หน้าร้านค้า</a>
                </div>
            </div>

            <div class="main-content">
                
                <div id="dashboard" class="tab-pane active">
                    <h2 class="section-title">📊 สรุปยอดขายร้านค้าทั้งหมด</h2>
                    <div class="sales-grid">
                        <div class="sales-box" style="background: linear-gradient(135deg, #3b82f6, #1d4ed8);">
                            <h2>ยอดขายวันนี้</h2>
                            <p class="amount">฿{{ "{:,.2f}".format(sales_today) }}</p>
                        </div>
                        <div class="sales-box" style="background: linear-gradient(135deg, #8b5cf6, #6d28d9);">
                            <h2>ยอดขายเดือนนี้</h2>
                            <p class="amount">฿{{ "{:,.2f}".format(sales_month) }}</p>
                        </div>
                        <div class="sales-box" style="background: linear-gradient(135deg, #f59e0b, #d97706);">
                            <h2>ยอดขายปีนี้</h2>
                            <p class="amount">฿{{ "{:,.2f}".format(sales_year) }}</p>
                        </div>
                        <div class="sales-box" style="background: linear-gradient(135deg, #10b981, #059669);">
                            <h2>ยอดขายรวมทั้งหมด</h2>
                            <p class="amount">฿{{ "{:,.2f}".format(total_sales) }}</p>
                        </div>
                    </div>

                    <h2 class="section-title" style="margin-top: 35px;">📅 ตรวจสอบยอดขายตามวันที่ระบุ</h2>
                    <div class="filter-box">
                        <form method="GET" action="{{ url_for('admin') }}" style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap; width: 100%;">
                            <label style="font-weight: 500;">เลือกวันที่:</label>
                            <input type="date" name="filter_date" value="{{ selected_date_str }}" class="form-control" style="width: 200px;" required>
                            <button type="submit" class="save-btn" style="background: #2563eb; padding: 10px 20px;">🔍 ค้นหา</button>
                            {% if selected_date_str %}
                                <a href="{{ url_for('admin') }}" style="color: #f87171; text-decoration: none; font-size: 14px;">ล้างการค้นหา</a>
                            {% endif %}
                        </form>
                    </div>

                    {% if selected_date_str %}
                    <div style="background: rgba(30, 41, 59, 0.8); padding: 20px; border-radius: 16px; margin-bottom: 30px; border: 1px solid rgba(255, 255, 255, 0.1);">
                        <h3 style="margin-top: 0; color: #4ade80;">ผลการตรวจสอบวันที่: {{ selected_date_str }}</h3>
                        <p style="font-size: 18px; font-weight: bold; margin-bottom: 15px;">ยอดขายรวมในวันดังกล่าว: ฿{{ "{:,.2f}".format(selected_date_sales) }}</p>
                        <h4 style="margin-bottom: 10px; color: #cbd5e1;">รายการสินค้าที่ขายออกไป:</h4>
                        {% if selected_date_items %}
                        <table>
                            <tr>
                                <th>ชื่อสินค้า</th>
                                <th style="text-align: center;">จำนวนที่ขายได้</th>
                                <th style="text-align: right;">ราคารวม (บาท)</th>
                            </tr>
                            {% for item in selected_date_items %}
                            <tr>
                                <td>{{ item.product_name }}</td>
                                <td style="text-align: center; color: #38bdf8;">{{ item.quantity }} ชิ้น</td>
                                <td style="text-align: right; color: #4ade80;">฿{{ "{:,.2f}".format(item.subtotal) }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                        {% else %}
                            <p style="color: var(--text-secondary);">ไม่มีรายการขายสินค้าในวันที่เลือกนี้</p>
                        {% endif %}
                    </div>
                    {% endif %}

                    <h2 class="section-title" style="margin-top: 35px;">🏆 จัดอันดับสินค้าขายดีที่สุด</h2>
                    <table>
                        <tr>
                            <th>อันดับ</th>
                            <th>ชื่อสินค้า</th>
                            <th style="text-align: center;">จำนวนที่ขายได้ (ชิ้น)</th>
                            <th style="text-align: right;">ยอดขายรวม (บาท)</th>
                        </tr>
                        {% for item in best_selling %}
                        <tr>
                            <td>
                                {% if loop.index == 1 %}<span class="rank-badge rank-1">🥇 อันดับ 1</span>
                                {% elif loop.index == 2 %}<span class="rank-badge rank-2">🥈 อันดับ 2</span>
                                {% elif loop.index == 3 %}<span class="rank-badge rank-3">🥉 อันดับ 3</span>
                                {% else %}<span style="color: var(--text-secondary);">#{{ loop.index }}</span>{% endif %}
                            </td>
                            <td><strong>{{ item.product_name }}</strong></td>
                            <td style="text-align: center; font-weight: 600; color: #38bdf8;">{{ item.total_qty }} ชิ้น</td>
                            <td style="text-align: right; font-weight: 600; color: #4ade80;">฿{{ "{:,.2f}".format(item.total_revenue) }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="4" style="text-align: center; color: var(--text-secondary); padding: 30px;">ยังไม่มีข้อมูลการขายสินค้าในระบบ</td></tr>
                        {% endfor %}
                    </table>
                </div>

                <div id="orders" class="tab-pane">
                    <h2 class="section-title">📝 รายการคำสั่งซื้อและอัปเดตสถานะ</h2>
                    <table>
                        <tr>
                            <th>รหัสบิล</th>
                            <th>ชื่อลูกค้า & ที่อยู่</th>
                            <th>ยอดเงิน</th>
                            <th>สลิปโอนเงิน</th>
                            <th>สถานะปัจจุบัน</th>
                            <th>เปลี่ยนสถานะ</th>
                        </tr>
                        {% for order in orders %}
                        <tr>
                            <td><strong>#{{ order.id }}</strong></td>
                            <td>
                                <div><strong>{{ order.customer_name }}</strong> (📞 {{ order.phone }})</div>
                                <div style="color: var(--text-secondary); font-size: 12px; margin-top: 4px;">{{ order.address }}</div>
                            </td>
                            <td><strong style="color: #4ade80;">฿{{ "{:,.2f}".format(order.total_price) }}</strong></td>
                            <td><a href="{{ url_for('static', filename='uploads/' + order.slip_image) }}" target="_blank" class="slip-link">📄 ดูสลิป</a></td>
                            <td>
                                <span class="status-badge 
                                    {% if order.status == 'จัดส่งสำเร็จ' %}status-success
                                    {% elif order.status == 'กำลังจัดส่ง' %}status-shipping
                                    {% elif order.status == 'กำลังเตรียมพัสดุ' %}status-packing
                                    {% elif order.status == 'ยกเลิกแล้ว' %}status-cancel
                                    {% else %}status-pending{% endif %}">
                                    {{ order.status }}
                                </span>
                            </td>
                            <td>
                                <form action="{{ url_for('update_order_status', order_id=order.id) }}" method="POST" class="status-form">
                                    <select name="status" class="status-select" style="padding: 6px 10px; font-size: 13px;">
                                        <option value="รอดำเนินการ" {% if order.status == 'รอดำเนินการ' %}selected{% endif %}>รอดำเนินการ</option>
                                        <option value="กำลังเตรียมพัสดุ" {% if order.status == 'กำลังเตรียมพัสดุ' %}selected{% endif %}>กำลังเตรียมพัสดุ</option>
                                        <option value="กำลังจัดส่ง" {% if order.status == 'กำลังจัดส่ง' %}selected{% endif %}>กำลังจัดส่ง</option>
                                        <option value="จัดส่งสำเร็จ" {% if order.status == 'จัดส่งสำเร็จ' %}selected{% endif %}>จัดส่งสำเร็จ</option>
                                        <option value="ยกเลิกแล้ว" {% if order.status == 'ยกเลิกแล้ว' %}selected{% endif %}>ยกเลิกแล้ว</option>
                                    </select>
                                    <button type="submit" class="save-btn" style="padding: 6px 12px; font-size: 13px;">อัปเดต</button>
                                </form>
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 30px;">ยังไม่มีรายการสั่งซื้อในระบบ</td></tr>
                        {% endfor %}
                    </table>
                </div>

                <div id="products" class="tab-pane">
                    <h2 class="section-title">📦 จัดการสต๊อกสินค้าและลบสินค้า</h2>
                    <form action="{{ url_for('update_all_stocks') }}" method="POST">
                        <table>
                            <tr>
                                <th>ชื่อสินค้า</th>
                                <th>หมวดหมู่</th>
                                <th>ราคา</th>
                                <th>จัดการสต๊อกคงเหลือ</th>
                                <th>จัดการ</th>
                            </tr>
                            {% for product in products %}
                            <tr>
                                <td><strong>{{ product.name }}</strong></td>
                                <td><span style="color: var(--text-secondary);">{{ product.category }}</span></td>
                                <td>฿{{ "{:,.0f}".format(product.price) }}</td>
                                <td>
                                    <div style="display: flex; gap: 8px; align-items: center;">
                                        <input type="number" name="stock_{{ product.id }}" value="{{ product.stock }}" min="0" class="stock-input" style="width: 90px;">
                                        {% if product.stock < 10 %}
                                            <span class="badge-stock-low">(ใกล้หมด)</span>
                                        {% endif %}
                                    </div>
                                </td>
                                <td>
                                    <a href="{{ url_for('admin_delete_product', product_id=product.id) }}" class="delete-btn" onclick="return confirm('คุณต้องการลบสินค้า {{ product.name }} นี้ใช่หรือไม่?')">🗑️ ลบ</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </table>
                        <div style="margin-top: 20px; text-align: right;">
                            <button type="submit" class="save-btn">💾 บันทึกสต๊อกทั้งหมด</button>
                        </div>
                    </form>
                </div>

                <div id="add-product" class="tab-pane">
                    <h2 class="section-title">📦 เพิ่มสินค้าใหม่เข้าสู่ระบบ</h2>
                    <div class="admin-form-box">
                        <form action="{{ url_for('admin_add_product') }}" method="POST" enctype="multipart/form-data">
                            <div class="admin-form-grid">
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">ชื่อสินค้า</label>
                                    <input type="text" name="name" placeholder="ชื่อสินค้า" class="form-control" required>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">หมวดหมู่</label>
                                    <input type="text" name="category" placeholder="เช่น เวย์, ครีเอทีน" class="form-control" required>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">ราคา (บาท)</label>
                                    <input type="number" step="any" name="price" placeholder="ราคา" class="form-control" required>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">จำนวนสต๊อก</label>
                                    <input type="number" name="stock" placeholder="จำนวน" class="form-control" required>
                                </div>
                            </div>
                            <div style="margin: 15px 0;">
                                <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">รูปภาพสินค้า:</label><br>
                                <input type="file" name="product_image" accept="image/*" required style="margin-top: 8px; color: #fff;">
                            </div>
                            <button type="submit" class="save-btn" style="background: #3b82f6; margin-top: 10px;">📦 บันทึกเพิ่มสินค้าใหม่</button>
                        </form>
                    </div>
                </div>

                <div id="add-admin" class="tab-pane">
                    <h2 class="section-title">🛡️ เพิ่มบัญชีผู้ดูแลระบบ (Admin) ใหม่</h2>
                    <div class="admin-form-box">
                        <form action="{{ url_for('admin_add_admin') }}" method="POST" enctype="multipart/form-data">
                            <div class="admin-form-grid">
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">ชื่อผู้ใช้งาน</label>
                                    <input type="text" name="username" placeholder="Username" class="form-control" required>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">รหัสผ่าน (6 ตัวขึ้นไป และตัวใหญ่ 1 ตัว)</label>
                                    <div class="password-container">
                                        <input type="password" name="password" id="admin-pass" placeholder="Password" class="form-control" required style="padding-right: 35px;">
                                        <span class="toggle-password" onclick="toggleVisibility('admin-pass', this)">👁️</span>
                                    </div>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">ชื่อจริง</label>
                                    <input type="text" name="first_name" placeholder="ชื่อจริง" class="form-control" required>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">นามสกุล</label>
                                    <input type="text" name="last_name" placeholder="นามสกุล" class="form-control" required>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">เบอร์โทรศัพท์ (10 หลัก)</label>
                                    <input type="tel" name="phone" placeholder="เบอร์โทรศัพท์" class="form-control" pattern="[0-9]{10}" maxlength="10" title="กรุณากรอกเบอร์โทรศัพท์ตัวเลข 10 หลักเท่านั้น" required>
                                </div>
                                <div>
                                    <label style="font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 5px;">อีเมล</label>
                                    <input type="email" name="email" placeholder="อีเมล" class="form-control" required>
                                </div>
                            </div>
                            <div style="margin: 15px 0;">
                                <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">รูปโปรไฟล์แอดมิน:</label><br>
                                <input type="file" name="profile_image" accept="image/*" style="margin-top: 8px; color: #fff;">
                            </div>
                            <button type="submit" class="save-btn" style="background: #10b981; margin-top: 10px;">🛡️ บันทึกเพิ่มแอดมินใหม่</button>
                        </form>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId, btn) {
            const panes = document.querySelectorAll('.tab-pane');
            panes.forEach(p => p.classList.remove('active'));

            const buttons = document.querySelectorAll('.menu-btn');
            buttons.forEach(b => b.classList.remove('active'));

            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
        }

        function toggleVisibility(inputId, icon) {
            var x = document.getElementById(inputId);
            if (x.type === "password") { x.type = "text"; icon.innerHTML = "👁️‍🗨️"; }
            else { x.type = "password"; icon.innerHTML = "👁️"; }
        }
    </script>
</body>
</html>
"""

HTML_ORDERS = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>สถานะการสั่งซื้อ - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; padding: 40px 20px; color: var(--text-main); }
        .container { background: rgba(15, 23, 42, 0.85); padding: 35px; max-width: 1100px; margin: auto; border-radius: 24px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 20px; margin-bottom: 25px; }
        .brand-link { text-decoration: none; color: #fff; font-size: 24px; font-weight: 600; }
        .back-link { text-decoration: none; color: #60a5fa; font-weight: 500; font-size: 14px; }
        
        .order-card { background: rgba(30, 41, 59, 0.7); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); padding: 25px; margin-bottom: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
        .order-header-info { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 15px; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        
        .status-badge { padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; display: inline-block; }
        .status-pending { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .status-packing { background: rgba(99, 102, 241, 0.2); color: #818cf8; }
        .status-shipping { background: rgba(14, 165, 233, 0.2); color: #38bdf8; }
        .status-success { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .status-cancel { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: rgba(15, 23, 42, 0.5); border-radius: 10px; overflow: hidden; }
        th, td { padding: 12px 15px; text-align: left; font-size: 13px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: #f8fafc; }
        th { background: rgba(15, 23, 42, 0.9); color: var(--text-secondary); font-weight: 600; }
        
        .empty-state { text-align: center; padding: 50px 0; color: var(--text-secondary); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="{{ url_for('index') }}" class="brand-link">📋 ตรวจสอบสถานะการสั่งซื้อของคุณ</a>
            <a href="{{ url_for('index') }}" class="back-link">← กลับไปหน้าแรก</a>
        </div>
        
        {% if orders %}
            {% for order in orders %}
            <div class="order-card">
                <div class="order-header-info">
                    <div>
                        <h3 style="margin: 0 0 5px 0; color: #fff;">คำสั่งซื้อ #{{ order.id }}</h3>
                        <p style="margin: 0; color: var(--text-secondary); font-size: 13px;">📅 วันที่สั่งซื้อ: {{ order.date_ordered.strftime('%Y-%m-%d %H:%M') }}</p>
                    </div>
                    <div>
                        <span class="status-badge 
                            {% if order.status == 'จัดส่งสำเร็จ' %}status-success
                            {% elif order.status == 'กำลังจัดส่ง' %}status-shipping
                            {% elif order.status == 'กำลังเตรียมพัสดุ' %}status-packing
                            {% elif order.status == 'ยกเลิกแล้ว' %}status-cancel
                            {% else %}status-pending{% endif %}">
                            ⏳ สถานะ: {{ order.status }}
                        </span>
                    </div>
                </div>

                <div style="margin-bottom: 15px; font-size: 13px; color: var(--text-secondary);">
                    <p style="margin: 4px 0;"><strong>ผู้รับ:</strong> {{ order.customer_name }} (📞 {{ order.phone }})</p>
                    <p style="margin: 4px 0;"><strong>ที่อยู่จัดส่ง:</strong> {{ order.address }}</p>
                </div>

                <h4 style="margin: 15px 0 8px 0; color: #cbd5e1; font-size: 14px;">📦 รายการสินค้าในคำสั่งซื้อนี้:</h4>
                <table>
                    <tr>
                        <th>ชื่อสินค้า</th>
                        <th style="text-align: center;">จำนวน</th>
                        <th style="text-align: right;">ราคาต่อหน่วย</th>
                        <th style="text-align: right;">ราคารวม (บาท)</th>
                    </tr>
                    {% for item in order.items %}
                    <tr>
                        <td>{{ item.product_name }}</td>
                        <td style="text-align: center; color: #38bdf8;">{{ item.quantity }} ชิ้น</td>
                        <td style="text-align: right;">฿{{ "{:,.2f}".format(item.price) }}</td>
                        <td style="text-align: right; color: #4ade80; font-weight: 600;">฿{{ "{:,.2f}".format(item.subtotal) }}</td>
                    </tr>
                    {% endfor %}
                </table>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <a href="{{ url_for('receipt', order_id=order.id) }}" target="_blank" style="background: #2563eb; color: white; padding: 6px 14px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 500;">
                        📄 ดูใบเสร็จรับเงิน
                    </a>
                    <div style="text-align: right;">
                        <span style="color: var(--text-secondary); font-size: 13px;">ยอดรวมสุทธิทั้งสิ้น (ราคารวม Vat 7%): </span>
                        <strong style="color: #4ade80; font-size: 18px;">฿{{ "{:,.2f}".format(order.total_price) }}</strong>
                    </div>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty-state">
                <h3>ยังไม่มีประวัติการสั่งซื้อ</h3>
                <p>คุณยังไม่ได้ทำรายการสั่งซื้อสินค้าใดๆ ในระบบ</p>
                <a href="{{ url_for('index') }}" style="background: var(--primary-color); color: white; padding: 10px 20px; border-radius: 10px; text-decoration: none; display: inline-block; margin-top: 15px;">ไปเลือกซื้อสินค้า</a>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

HTML_RECEIPT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ใบเสร็จรับเงิน #{{ order.id }} - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Prompt', sans-serif; background: #f3f4f6; margin: 0; padding: 40px 20px; color: #1f2937; }
        .receipt-box { background: #ffffff; padding: 40px; max-width: 750px; margin: auto; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
        .receipt-header { text-align: center; border-bottom: 2px solid #e5e7eb; padding-bottom: 20px; margin-bottom: 25px; }
        .receipt-header h2 { margin: 0; color: #2563eb; font-size: 26px; }
        .receipt-header p { margin: 5px 0 0 0; color: #6b7280; font-size: 14px; }
        .info-section { display: flex; justify-content: space-between; margin-bottom: 25px; font-size: 14px; }
        .info-group h4 { margin: 0 0 5px 0; color: #374151; }
        .info-group p { margin: 0; color: #6b7280; line-height: 1.5; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 25px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #f1f5f9; font-size: 14px; }
        th { background: #f8fafc; color: #6b7280; font-weight: 600; }
        .total-section { text-align: right; margin-bottom: 30px; }
        .total-section h3 { margin: 0; color: #10b981; font-size: 22px; }
        .btn-print { background: #2563eb; color: white; border: none; padding: 12px 25px; border-radius: 12px; font-family: 'Prompt'; font-size: 16px; font-weight: 500; cursor: pointer; width: 100%; }
        @media print { body { background: white; padding: 0; } .receipt-box { box-shadow: none; padding: 0; } .btn-print { display: none; } }
    </style>
</head>
<body>
    <div class="receipt-box">
        <div class="receipt-header">
            <h2>Whey Station</h2>
            <p>ใบเสร็จรับเงิน / หลักฐานการชำระเงิน</p>
        </div>
        <div class="info-section">
            <div class="info-group">
                <h4>ข้อมูลลูกค้า:</h4>
                <p><strong>ชื่อผู้รับ:</strong> {{ order.customer_name }}</p>
                <p><strong>เบอร์โทรศัพท์:</strong> {{ order.phone }}</p>
                <p><strong>ที่อยู่จัดส่ง:</strong> {{ order.address }}</p>
            </div>
            <div class="info-group" style="text-align: right;">
                <h4>รายละเอียดใบเสร็จ:</h4>
                <p><strong>เลขที่ใบเสร็จ:</strong> #000{{ order.id }}</p>
                <p><strong>วันที่สั่งซื้อ:</strong> {{ order.date_ordered.strftime('%Y-%m-%d %H:%M') }}</p>
            </div>
        </div>
        <table>
            <tr>
                <th>รายการสินค้า</th>
                <th style="text-align: center;">จำนวน</th>
                <th style="text-align: right;">ราคาต่อหน่วย</th>
                <th style="text-align: right;">ราคารวม</th>
            </tr>
            {% for item in order.items %}
            <tr>
                <td>{{ item.product_name }}</td>
                <td style="text-align: center;">{{ item.quantity }}</td>
                <td style="text-align: right;">฿{{ "{:,.2f}".format(item.price) }}</td>
                <td style="text-align: right; font-weight: 600;">฿{{ "{:,.2f}".format(item.subtotal) }}</td>
            </tr>
            {% endfor %}
        </table>
        <div class="total-section">
            <p style="color: #6b7280; font-size: 14px; margin-bottom: 5px;">ยอดชำระสุทธิทั้งสิ้น (ราคารวม Vat 7%)</p>
            <h3>฿{{ "{:,.2f}".format(order.total_price) }}</h3>
        </div>
        <button onclick="window.print()" class="btn-print">🖨️ พิมพ์ใบเสร็จ / บันทึกเป็น PDF</button>
    </div>
</body>
</html>
"""

HTML_USERS = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>จัดการสมาชิกและแอดมิน - Admin Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary-color: #ef4444; --success-color: #10b981; --bg-color: #0f172a; --text-main: #f8fafc; --text-secondary: #94a3b8; }
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; padding: 40px 20px; color: var(--text-main); }
        .container { background: rgba(15, 23, 42, 0.85); padding: 35px; max-width: 1300px; margin: auto; border-radius: 24px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid rgba(255, 255, 255, 0.1); padding-bottom: 20px; margin-bottom: 25px; flex-wrap: wrap; gap: 15px; }
        .brand-link { text-decoration: none; color: #fff; font-size: 24px; font-weight: 600; }
        .back-btn { background: rgba(255, 255, 255, 0.1); color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 12px; font-weight: 500; font-size: 14px; border: 1px solid rgba(255, 255, 255, 0.2); }
        .table-responsive { width: 100%; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; background: rgba(30, 41, 59, 0.6); border-radius: 14px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.1); min-width: 950px; }
        th, td { padding: 15px; text-align: left; font-size: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: #f8fafc; white-space: nowrap; }
        th { background: rgba(15, 23, 42, 0.8); color: var(--text-secondary); font-weight: 600; }
        .role-admin { background: rgba(239, 68, 68, 0.2); color: #f87171; padding: 4px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }
        .role-user { background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 4px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }
        .profile-img { width: 45px; height: 45px; object-fit: cover; border-radius: 50%; border: 1px solid rgba(255,255,255,0.2); background: #1e293b; }
        .action-form { display: flex; gap: 6px; align-items: center; }
        .pwd-input { padding: 6px 10px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.2); background: rgba(15, 23, 42, 0.8); color: #fff; font-size: 13px; width: 120px; }
        .btn-action { background: #2563eb; color: #fff; border: none; padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; font-family: 'Prompt'; }
        .btn-delete { background: #ef4444; color: #fff; border: none; padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; font-family: 'Prompt'; text-decoration: none; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="{{ url_for('admin') }}" class="brand-link">👥 ข้อมูลสมาชิกและผู้ดูแลระบบทั้งหมด</a>
            <a href="{{ url_for('admin') }}" class="back-btn">← กลับไปหน้าแอดมินหลัก</a>
        </div>
        <div class="table-responsive">
            <table>
                <tr>
                    <th>รูปโปรไฟล์</th>
                    <th>ID</th>
                    <th>ชื่อผู้ใช้ (Username)</th>
                    <th>สิทธิ์ (Role)</th>
                    <th>ชื่อ - นามสกุล</th>
                    <th>เบอร์โทร & อีเมล</th>
                    <th>รหัสผ่านเดิม</th>
                    <th>เปลี่ยนรหัสผ่าน</th>
                    <th>จัดการ</th>
                </tr>
                {% for u in users %}
                <tr>
                    <td>
                        {% if u.profile_image %}
                            <img src="{{ url_for('static', filename='uploads/' + u.profile_image) }}" class="profile-img" alt="profile">
                        {% else %}
                            <div class="profile-img" style="display: flex; align-items: center; justify-content: center; font-size: 18px;">👤</div>
                        {% endif %}
                    </td>
                    <td>#{{ u.id }}</td>
                    <td><strong>{{ u.username }}</strong></td>
                    <td>
                        {% if u.role == 'admin' %}
                            <span class="role-admin">Admin</span>
                        {% else %}
                            <span class="role-user">User</span>
                        {% endif %}
                    </td>
                    <td>{{ u.first_name or '-' }} {{ u.last_name or '-' }}</td>
                    <td>
                        <div>📞 {{ u.phone or '-' }}</div>
                        <div style="font-size: 12px; color: var(--text-secondary);">✉️ {{ u.email or '-' }}</div>
                    </td>
                    <td><code style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 6px; color: #38bdf8;">{{ u.password }}</code></td>
                    <td>
                        <form action="{{ url_for('admin_update_password', user_id=u.id) }}" method="POST" class="action-form">
                            <input type="password" name="new_password" placeholder="รหัสใหม่" class="pwd-input" required>
                            <button type="submit" class="btn-action">เปลี่ยน</button>
                        </form>
                    </td>
                    <td>
                        {% if u.id != session.get('user_id') %}
                            <a href="{{ url_for('admin_delete_user', user_id=u.id) }}" class="btn-delete" onclick="return confirm('คุณต้องการลบบัญชีนี้ใช่หรือไม่?')">🗑️ ลบ</a>
                        {% else %}
                            <span style="color: #10b981; font-size: 13px;">(กำลังใช้งาน)</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="9" style="text-align: center; color: var(--text-secondary); padding: 30px;">ยังไม่มีสมาชิกในระบบ</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

HTML_FORGOT_PASSWORD = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ลืมรหัสผ่าน - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; color: #f8fafc; }
        .auth-card { background: rgba(15, 23, 42, 0.9); padding: 40px; border-radius: 20px; width: 350px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); backdrop-filter: blur(12px); text-align: center; border: 1px solid rgba(255, 255, 255, 0.1); }
        .auth-card h2 { color: #ef4444; font-size: 26px; margin-bottom: 10px; }
        .auth-card p { color: #94a3b8; margin-bottom: 25px; font-size: 14px; }
        input[type="email"] { width: 100%; padding: 15px; margin-bottom: 15px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 14px; color: #fff; }
        .btn-main { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; margin-bottom: 15px; }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(239, 68, 68, 0.4); }
        .alert-success { background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(16, 185, 129, 0.4); }
        .back-link { color: #94a3b8; text-decoration: none; font-size: 14px; }
    </style>
</head>
<body>
    <div class="auth-card">
        <h2>กู้คืนรหัสผ่าน</h2>
        <p>กรอกอีเมลของคุณเพื่อรับรหัส OTP 6 หลัก</p>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="{{ 'alert-success' if category == 'success' else 'alert' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="email" name="email" placeholder="กรอกอีเมลที่ใช้สมัคร" required>
            <button type="submit" class="btn-main">ส่งรหัส OTP ไปยังอีเมล</button>
        </form>
        <a href="{{ url_for('login') }}" class="back-link">กลับไปหน้าเข้าสู่ระบบ</a>
    </div>
</body>
</html>
"""

HTML_VERIFY_OTP = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ยืนยันรหัส OTP - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; color: #f8fafc; }
        .auth-card { background: rgba(15, 23, 42, 0.9); padding: 40px; border-radius: 20px; width: 350px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); backdrop-filter: blur(12px); text-align: center; border: 1px solid rgba(255, 255, 255, 0.1); }
        .auth-card h2 { color: #10b981; font-size: 26px; margin-bottom: 10px; }
        .auth-card p { color: #94a3b8; margin-bottom: 25px; font-size: 14px; }
        input[type="text"] { width: 100%; padding: 15px; margin-bottom: 15px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 20px; text-align: center; letter-spacing: 5px; color: #fff; }
        .btn-main { background: linear-gradient(135deg, #10b981, #059669); color: white; width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; margin-bottom: 15px; }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(239, 68, 68, 0.4); }
        .alert-success { background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(16, 185, 129, 0.4); }
    </style>
</head>
<body>
    <div class="auth-card">
        <h2>ยืนยันรหัส OTP</h2>
        <p>กรุณากรอกรหัส 6 หลักที่ส่งไปยังอีเมลของคุณ</p>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="{{ 'alert-success' if category == 'success' else 'alert' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="otp" placeholder="------" maxlength="6" required>
            <button type="submit" class="btn-main">ตรวจสอบรหัส</button>
        </form>
    </div>
</body>
</html>
"""

HTML_RESET_PASSWORD = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ตั้งรหัสผ่านใหม่ - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Prompt', sans-serif; background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('{{ url_for("static", filename="ChatGPT Image Oct 5, 2026, 10_27_24 PM.png") }}'); background-size: cover; background-position: center; background-attachment: fixed; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; color: #f8fafc; }
        .auth-card { background: rgba(15, 23, 42, 0.9); padding: 40px; border-radius: 20px; width: 350px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); backdrop-filter: blur(12px); text-align: center; border: 1px solid rgba(255, 255, 255, 0.1); }
        .auth-card h2 { color: #f59e0b; font-size: 26px; margin-bottom: 10px; }
        input[type="password"] { width: 100%; padding: 15px; margin-bottom: 15px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 14px; color: #fff; }
        .btn-main { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(239, 68, 68, 0.4); }
    </style>
</head>
<body>
    <div class="auth-card">
        <h2>ตั้งรหัสผ่านใหม่</h2>
        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 20px;">อย่างน้อย 6 ตัว และมีตัวพิมพ์ใหญ่ 1 ตัว</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        <form method="POST">
            <input type="password" name="password" placeholder="รหัสผ่านใหม่" required>
            <input type="password" name="confirm_password" placeholder="ยืนยันรหัสผ่านใหม่" required>
            <button type="submit" class="btn-main">บันทึกรหัสผ่านใหม่</button>
        </form>
    </div>
</body>
</html>
"""

HTML_ADMIN_LOGIN = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>เข้าสู่ระบบผู้ดูแลระบบ - Whey Station</title>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Prompt', sans-serif; background-color: #0f172a; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; color: #f8fafc; }
        .auth-card { background: rgba(30, 41, 59, 0.9); padding: 40px; border-radius: 20px; width: 350px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); text-align: center; border: 1px solid rgba(255, 255, 255, 0.1); border-top: 6px solid #ef4444; }
        .auth-card h2 { color: #ef4444; font-size: 26px; margin-bottom: 10px; margin-top: 0; }
        input[type="text"], input[type="password"] { width: 100%; padding: 15px; margin-bottom: 15px; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; box-sizing: border-box; font-family: 'Prompt'; font-size: 14px; color: #fff; }
        .btn-main { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; font-family: 'Prompt'; cursor: pointer; }
        .alert { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(239, 68, 68, 0.4); }
        .back-link { display: inline-block; margin-top: 20px; color: #94a3b8; text-decoration: none; font-size: 14px; }
    </style>
</head>
<body>
    <div class="auth-card">
        <h2>⚡ ADMIN SYSTEM</h2>
        <p style="color: #94a3b8; margin-bottom: 25px; font-size: 14px;">เข้าสู่ระบบเฉพาะผู้ดูแลร้านค้าเท่านั้น</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="alert">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="Admin Username" required>
            <input type="password" name="password" placeholder="Admin Password" required>
            <button type="submit" class="btn-main">เข้าสู่ระบบแอดมิน</button>
        </form>
    </div>
    <a href="{{ url_for('login') }}" class="back-link">กลับไปหน้าล็อกอินทั่วไป</a>
</body>
</html>
"""


# =========================================================================
# ส่วนที่ 4: การกำหนดเส้นทางและระบบการทำงานของเว็บ (Routes & Logic)
# =========================================================================

@app.route('/')
def index():
    category = request.args.get('category', 'All')
    if category == 'All':
        products = Product.query.all()
    else:
        products = Product.query.filter_by(category=category).all()
        
    cart = session.get('cart', {})
    if isinstance(cart, list):
        cart = {}
        session['cart'] = cart
        
    cart_count = sum(cart.values())
    return render_template_string(HTML_INDEX, products=products, cart_count=cart_count)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {})
    if isinstance(cart, list): cart = {}
    cart_count = sum(cart.values())
    return render_template_string(HTML_PRODUCT, product=product, cart_count=cart_count)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, password=password, role='user').first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['profile_image'] = user.profile_image
            return redirect(url_for('index'))
        else:
            flash('❌ ชื่อผู้ใช้หรือรหัสผ่านผู้ใช้งานทั่วไปไม่ถูกต้อง')
    return render_template_string(HTML_LOGIN)


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            otp = str(random.randint(100000, 999999))
            user.otp_code = otp
            user.otp_expiry = datetime.now() + timedelta(minutes=5)
            db.session.commit()
            
            session['reset_email'] = email
            
            try:
                msg = MIMEMultipart()
                msg['From'] = MAIL_USERNAME
                msg['To'] = email
                msg['Subject'] = 'รหัสยืนยัน OTP สำหรับกู้คืนรหัสผ่าน - Whey Station'
                body = f"""สวัสดีคุณ {user.first_name or user.username},
รหัส OTP สำหรับกู้คืนรหัสผ่านของคุณคือ: {otp}
รหัสนี้มีอายุการใช้งาน 5 นาที"""
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                
                server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT)
                server.login(MAIL_USERNAME, MAIL_PASSWORD)
                server.sendmail(MAIL_USERNAME, email, msg.as_string())
                server.quit()
            except Exception as e:
                flash(f'⚠️ ส่งอีเมลไม่สำเร็จ (Error: {str(e)}) | [โหมดทดสอบ] รหัส OTP ของคุณคือ: {otp}', 'success')
                return redirect(url_for('verify_otp'))
                
            flash('✅ ระบบได้ส่งรหัส OTP ไปยังอีเมลของคุณแล้ว กรุณากรอกรหัส 6 หลัก', 'success')
            return redirect(url_for('verify_otp'))
        else:
            flash('❌ ไม่พบอีเมลนี้ในระบบสมาชิก กรุณาตรวจสอบความถูกต้อง', 'error')
            
    return render_template_string(HTML_FORGOT_PASSWORD)


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        user = User.query.filter_by(email=email).first()
        
        if user and user.otp_code == entered_otp:
            if user.otp_expiry and datetime.now() <= user.otp_expiry:
                session['otp_verified'] = True
                return redirect(url_for('reset_password'))
            else:
                flash('❌ รหัส OTP หมดอายุแล้ว กรุณาขอรหัสใหม่อีกครั้ง')
        else:
            flash('❌ รหัส OTP ไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง')
            
    return render_template_string(HTML_VERIFY_OTP)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('otp_verified') or not session.get('reset_email'):
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        pwd_error = is_valid_password(password)
        if pwd_error:
            flash(f'❌ {pwd_error}')
        elif password != confirm_password:
            flash('❌ รหัสผ่านใหม่และยืนยันรหัสผ่านไม่ตรงกัน')
        else:
            email = session.get('reset_email')
            user = User.query.filter_by(email=email).first()
            if user:
                user.password = password
                user.otp_code = None
                user.otp_expiry = None
                db.session.commit()
                
                session.pop('reset_email', None)
                session.pop('otp_verified', None)
                
                flash('✅ เปลี่ยนรหัสผ่านสำเร็จ! กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่', 'success')
                return redirect(url_for('login'))
                
    return render_template_string(HTML_RESET_PASSWORD)


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = User.query.filter_by(username=username, password=password, role='admin').first()
        if admin:
            session['user_id'] = admin.id
            session['username'] = admin.username
            session['role'] = admin.role
            session['profile_image'] = admin.profile_image
            return redirect(url_for('admin'))
        else:
            flash('❌ ชื่อผู้ใช้หรือรหัสผ่านแอดมินไม่ถูกต้อง')
    return render_template_string(HTML_ADMIN_LOGIN)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')

        cropped_data = request.form.get('cropped_image')
        file = request.files.get('profile_image')
        filename = None
        
        if cropped_data:
            header, encoded = cropped_data.split(",", 1)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = secure_filename(f"{username}_{timestamp}.jpg")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            with open(file_path, "wb") as fh:
                fh.write(base64.b64decode(encoded))
                
        elif file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        pwd_error = is_valid_password(password)
        if len(username) < 4:
            flash('❌ ชื่อผู้ใช้งานต้องมีความยาวอย่างน้อย 4 ตัวอักษรขึ้นไป')
        elif not phone.isdigit() or len(phone) != 10:
            flash('❌ เบอร์โทรศัพท์ต้องเป็นตัวเลข 10 หลักเท่านั้น')
        elif pwd_error:
            flash(f'❌ {pwd_error}')
        elif User.query.filter_by(username=username).first():
            flash('❌ ชื่อผู้ใช้นี้มีคนใช้แล้ว กรุณาใช้ชื่ออื่น')
        else:
            new_user = User(
                username=username, 
                password=password, 
                role='user',
                first_name=first_name, 
                last_name=last_name, 
                phone=phone, 
                email=email,
                profile_image=filename
            )
            db.session.add(new_user)
            db.session.commit()
            flash('✅ สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ')
            return redirect(url_for('login'))
            
    return render_template_string(HTML_REGISTER)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = User.query.get_or_404(session['user_id'])
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        
        if not phone.isdigit() or len(phone) != 10:
            flash('❌ เบอร์โทรศัพท์ต้องเป็นตัวเลข 10 หลักเท่านั้น', 'error')
            return redirect(url_for('profile'))
            
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.phone = phone
        user.email = request.form.get('email')
        
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password and new_password.strip() != '':
            pwd_error = is_valid_password(new_password)
            if pwd_error:
                flash(f'❌ {pwd_error}', 'error')
                return redirect(url_for('profile'))
            if new_password != confirm_password:
                flash('❌ รหัสผ่านใหม่และยืนยันรหัสผ่านไม่ตรงกัน กรุณากรอกใหม่อีกครั้ง', 'error')
                return redirect(url_for('profile'))
            user.password = new_password
            
        cropped_data = request.form.get('cropped_image')
        file = request.files.get('profile_image')
        
        if cropped_data:
            header, encoded = cropped_data.split(",", 1)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = secure_filename(f"{user.username}_{timestamp}.jpg")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            with open(file_path, "wb") as fh:
                fh.write(base64.b64decode(encoded))
                
            user.profile_image = filename
            session['profile_image'] = filename
            
        elif file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_image = filename
            session['profile_image'] = filename
            
        db.session.commit()
        flash('✅ อัปเดตข้อมูลโปรไฟล์ส่วนตัวสำเร็จ!', 'success')
        return redirect(url_for('profile'))
        
    return render_template_string(HTML_PROFILE, user=user)


@app.route('/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    cart = session.get('cart', {})
    if isinstance(cart, list): cart = {}
    
    if request.method == 'POST':
        try:
            quantity = int(request.form.get('quantity', 1))
        except ValueError:
            quantity = 1
    else:
        quantity = 1
        
    product = Product.query.get_or_404(product_id)
    prod_id = str(product_id)
    current_qty = cart.get(prod_id, 0)
    
    if current_qty + quantity > product.stock:
        flash(f'❌ ไม่สามารถเพิ่มสินค้าเกินจำนวนที่มีในสต๊อกได้ (เหลือ {product.stock} ชิ้น)')
        return redirect(url_for('product_detail', product_id=product_id))
        
    cart[prod_id] = current_qty + quantity
    session['cart'] = cart
    session.modified = True
    flash('🛒 เพิ่มสินค้าลงตะกร้าเรียบร้อยแล้ว!')
    return redirect(url_for('index'))


@app.route('/update_cart_ajax/<int:product_id>/<action>', methods=['POST'])
def update_cart_ajax(product_id, action):
    cart = session.get('cart', {})
    prod_id = str(product_id)
    product = Product.query.get(product_id)
    
    if prod_id in cart:
        if action == 'increase':
            if product and cart[prod_id] < product.stock:
                cart[prod_id] += 1
            else:
                return jsonify({'success': False, 'message': f'สินค้ามีจำนวนจำกัดในสต๊อก (เหลือ {product.stock} ชิ้น)'})
        elif action == 'decrease':
            cart[prod_id] -= 1
            if cart[prod_id] <= 0:
                cart.pop(prod_id)
        elif action == 'remove':
            cart.pop(prod_id)
            
    session['cart'] = cart
    session.modified = True
    
    total = 0
    items_data = {}
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            sub = p.price * qty
            total += sub
            items_data[pid] = {'quantity': qty, 'subtotal': sub}
            
    return jsonify({
        'success': True, 
        'total': total, 
        'items': items_data, 
        'cart_count': sum(cart.values())
    })


@app.route('/update_cart_input_ajax/<int:product_id>', methods=['POST'])
def update_cart_input_ajax(product_id):
    cart = session.get('cart', {})
    prod_id = str(product_id)
    product = Product.query.get_or_404(product_id)
    
    data = request.get_json()
    try:
        qty = int(data.get('quantity', 1))
    except (ValueError, TypeError):
        qty = 1
        
    if qty > product.stock:
        qty = product.stock
        
    if qty <= 0:
        cart.pop(prod_id, None)
    else:
        cart[prod_id] = qty
        
    session['cart'] = cart
    session.modified = True
    
    total = 0
    items_data = {}
    for pid, q in cart.items():
        p = Product.query.get(int(pid))
        if p:
            sub = p.price * q
            total += sub
            items_data[pid] = {'quantity': q, 'subtotal': sub}
            
    return jsonify({
        'success': True,
        'total': total,
        'items': items_data,
        'cart_count': sum(cart.values())
    })


@app.route('/cart')
def cart():
    cart_session = session.get('cart', {})
    if isinstance(cart_session, list): cart_session = {}
    
    items = []
    total = 0
    for prod_id, quantity in cart_session.items():
        product = Product.query.get(int(prod_id))
        if product:
            sub = product.price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': sub
            })
            total += sub
            
    return render_template_string(HTML_CART, items=items, total=total, cart_count=sum(cart_session.values()))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart_session = session.get('cart', {})
    if isinstance(cart_session, list): cart_session = {}
    
    items = []
    total = 0
    for prod_id, quantity in cart_session.items():
        product = Product.query.get(int(prod_id))
        if product:
            sub = product.price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': sub
            })
            total += sub

    raw_total = request.args.get('total', total)
    try:
        total_price = float(raw_total)
    except (ValueError, TypeError):
        total_price = float(total)

    for prod_id, quantity in cart_session.items():
        product = Product.query.get(int(prod_id))
        if not product or product.stock < quantity:
            flash(f'❌ สินค้า "{product.name if product else prod_id}" มีจำนวนไม่พอในสต๊อก (เหลือ {product.stock if product else 0} ชิ้น)')
            return redirect(url_for('cart'))

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        total_val = request.form['total_price']
        
        if not phone.isdigit() or len(phone) != 10:
            flash('❌ เบอร์โทรศัพท์จัดส่งต้องเป็นตัวเลข 10 หลักเท่านั้น')
            return redirect(url_for('checkout', total=total_val))
            
        filename = 'default_slip.jpg'
        file = request.files.get('slip')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        new_order = Order(
            user_id=session['user_id'], 
            total_price=float(total_val), 
            slip_image=filename, 
            customer_name=name, 
            phone=phone, 
            address=address
        )
        db.session.add(new_order)
        db.session.flush()
        
        for prod_id, quantity in cart_session.items():
            product = Product.query.get(int(prod_id))
            if product:
                sub = product.price * quantity
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_name=product.name,
                    price=product.price,
                    quantity=quantity,
                    subtotal=sub
                )
                db.session.add(order_item)
                
                if product.stock >= quantity:
                    product.stock -= quantity
                else:
                    product.stock = 0
                
        db.session.commit()
        session.pop('cart', None)
        flash('🎉 สั่งซื้อสำเร็จ! ตัดสต๊อกและบันทึกคำสั่งซื้อเรียบร้อยแล้ว')
        return redirect(url_for('index'))

    return render_template_string(HTML_CHECKOUT, items=items, total_price=total_price)


@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    products = Product.query.all()
    orders = Order.query.all()
    
    valid_orders = [o for o in orders if o.status != 'ยกเลิกแล้ว']
    total_sales = sum(o.total_price for o in valid_orders)
    
    now = datetime.now()
    sales_today = sum(o.total_price for o in valid_orders if o.date_ordered.date() == now.date())
    sales_month = sum(o.total_price for o in valid_orders if o.date_ordered.year == now.year and o.date_ordered.month == now.month)
    sales_year = sum(o.total_price for o in valid_orders if o.date_ordered.year == now.year)
    
    selected_date_str = request.args.get('filter_date', '')
    selected_date_sales = 0
    selected_date_items = []
    if selected_date_str:
        try:
            filter_dt = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            filtered_orders = [o for o in valid_orders if o.date_ordered.date() == filter_dt]
            selected_date_sales = sum(o.total_price for o in filtered_orders)
            for fo in filtered_orders:
                for item in fo.items:
                    selected_date_items.append(item)
        except ValueError:
            pass

    best_selling = db.session.query(
        OrderItem.product_name,
        func.sum(OrderItem.quantity).label('total_qty'),
        func.sum(OrderItem.subtotal).label('total_revenue')
    ).join(Order).filter(Order.status != 'ยกเลิกแล้ว').group_by(OrderItem.product_name).order_by(func.sum(OrderItem.quantity).desc()).all()

    return render_template_string(HTML_ADMIN, products=products, orders=orders, 
                                  total_sales=total_sales, sales_today=sales_today, 
                                  sales_month=sales_month, sales_year=sales_year,
                                  best_selling=best_selling,
                                  selected_date_str=selected_date_str,
                                  selected_date_sales=selected_date_sales,
                                  selected_date_items=selected_date_items)


@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template_string(HTML_USERS, users=users)


@app.route('/admin/add_admin', methods=['POST'])
def admin_add_admin():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    phone = request.form.get('phone')
    email = request.form.get('email')

    pwd_error = is_valid_password(password) if password else 'กรุณากรอกรหัสผ่าน'

    if not phone.isdigit() or len(phone) != 10:
        flash('❌ เบอร์โทรศัพท์แอดมินต้องเป็นตัวเลข 10 หลักเท่านั้น')
        return redirect(url_for('admin'))

    file = request.files.get('profile_image')
    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if User.query.filter_by(username=username).first():
        flash('❌ ชื่อผู้ใช้นี้มีในระบบแล้ว กรุณาใช้ชื่ออื่น')
    elif pwd_error:
        flash(f'❌ {pwd_error}')
    else:
        new_admin = User(
            username=username,
            password=password,
            role='admin',
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            profile_image=filename
        )
        db.session.add(new_admin)
        db.session.commit()
        flash('✅ เพิ่มบัญชีผู้ดูแลระบบใหม่พร้อมรูปโปรไฟล์สำเร็จ!')
        
    return redirect(url_for('admin'))


@app.route('/admin/add_product', methods=['POST'])
def admin_add_product():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    category = request.form.get('category')
    price = request.form.get('price')
    stock = request.form.get('stock')
    
    file = request.files.get('product_image')
    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        images_folder = os.path.join(BASE_DIR, 'static', 'images')
        os.makedirs(images_folder, exist_ok=True)
        file.save(os.path.join(images_folder, filename))
        
    try:
        new_product = Product(
            name=name,
            category=category,
            price=float(price),
            stock=int(stock),
            image_file=filename
        )
        db.session.add(new_product)
        db.session.commit()
        flash('✅ เพิ่มสินค้าใหม่พร้อมรูปภาพสำเร็จ!')
    except Exception as e:
        flash('❌ เกิดข้อผิดพลาดในการเพิ่มสินค้า กรุณาลองใหม่อีกครั้ง')
        
    return redirect(url_for('admin'))


@app.route('/admin/delete_product/<int:product_id>')
def admin_delete_product(product_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'🗑️ ลบสินค้า "{product.name}" สำเร็จแล้ว')
    return redirect(url_for('admin'))


@app.route('/admin/update_password/<int:user_id>', methods=['POST'])
def admin_update_password(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    
    pwd_error = is_valid_password(new_password) if new_password else 'กรุณากรอกรหัสผ่านใหม่'
    if pwd_error:
        flash(f'❌ {pwd_error}')
    else:
        user.password = new_password
        db.session.commit()
        flash(f'✅ เปลี่ยนรหัสผ่านของสมาชิก {user.username} สำเร็จ!')
        
    return redirect(url_for('admin_users'))


@app.route('/admin/delete_user/<int:user_id>')
def admin_delete_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == session.get('user_id'):
        flash('❌ ไม่สามารถลบบัญชีที่คุณกำลังใช้งานอยู่ได้')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'🗑️ ลบบัญชี {user.username} ออกจากระบบเรียบร้อยแล้ว')
        
    return redirect(url_for('admin_users'))


@app.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    new_status = request.form.get('status')
    order = Order.query.get_or_404(order_id)
    
    if new_status == 'ยกเลิกแล้ว' and order.status != 'ยกเลิกแล้ว':
        for item in order.items:
            product = Product.query.filter_by(name=item.product_name).first()
            if product:
                product.stock += item.quantity
    elif order.status == 'ยกเลิกแล้ว' and new_status != 'ยกเลิกแล้ว':
        for item in order.items:
            product = Product.query.filter_by(name=item.product_name).first()
            if product:
                if product.stock >= item.quantity:
                    product.stock -= item.quantity
                else:
                    product.stock = 0

    order.status = new_status
    db.session.commit()
    flash('✅ อัปเดตสถานะคำสั่งซื้อสำเร็จ!')
    return redirect(url_for('admin'))


@app.route('/update_all_stocks', methods=['POST'])
def update_all_stocks():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    products = Product.query.all()
    for product in products:
        stock_value = request.form.get(f'stock_{product.id}')
        if stock_value is not None:
            try:
                product.stock = int(stock_value)
            except ValueError:
                pass
                
    db.session.commit()
    flash('✅ อัปเดตสต๊อกสินค้าทั้งหมดสำเร็จ!')
    return redirect(url_for('admin'))


@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.date_ordered.desc()).all()
    cart = session.get('cart', {})
    if isinstance(cart, list): cart = {}
    cart_count = sum(cart.values())
    
    return render_template_string(HTML_ORDERS, orders=user_orders, cart_count=cart_count)


@app.route('/receipt/<int:order_id>')
def receipt(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    order = Order.query.get_or_404(order_id)
    if order.user_id != session['user_id'] and session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    return render_template_string(HTML_RECEIPT, order=order)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# =========================================================================
# ส่วนที่ 5: การรันเซิร์ฟเวอร์
# =========================================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Product.query.first():
            products = [
                Product(name='เวย์โปรตีน MY WHEY MAX รส Strawberry', category='เวย์', price=3300, stock=30, image_file='Baam01.png'),
                Product(name='เวย์โปรตีน ISO - SOY รส Dark Chocolate', category='เวย์', price=1350, stock=15, image_file='Baam02.png'),
                Product(name='เวย์โปรตีน ISO ABSOLUTE ZERO รส Strawberry', category='เวย์', price=1600, stock=15, image_file='Baam03.png'),
                Product(name='เวย์โปรตีน ULTRA MASS รส Strawberry Yoghurt', category='เวย์', price=2800, stock=15, image_file='Baam04.png'),
                Product(name='เวย์โปรตีน MASS SOY XXXXL รส Black Sesame', category='เวย์', price=2025, stock=15, image_file='Baam05.png'),
                Product(name='CREATINE MAX ATP 5000', category='ครีเอทีน', price=700, stock=15, image_file='Creatine02.png'),
                Product(name='L-CARNITINE L-TARTRATE MAX', category='แอลคาเนทีน', price=750, stock=15, image_file='lcanetine.png'),
                Product(name='VITAMIN C 500 MG', category='วิตามิน', price=400, stock=15, image_file='vitamin.png')
            ]
            admin_user = User(
                username='admin', 
                password='2549', 
                role='admin', 
                first_name='Admin', 
                last_name='System', 
                phone='0800000000', 
                email='admin@wheystation.com'
            )
            db.session.add_all(products)
            db.session.add(admin_user)
            db.session.commit()
            
    app.run(debug=True)