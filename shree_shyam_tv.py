import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

DB_NAME = "shree_shyam_tv.db"

# --- Profanity Filter ---
PROFANITY_LIST = ["bhadwa", "chutiya", "madarchod", "behenchod", "saala", "asshole", "fuck", "shit", "bitch", "gandu"]

def is_clean(text):
    if not text: return True
    text = text.lower()
    return not any(word in text for word in PROFANITY_LIST)

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Kirtan Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kirtans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            date TEXT NOT NULL,
            pic_base64 TEXT,
            organizer TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bus Seva Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bus_seva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seva_name TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            seats INTEGER,
            phone TEXT,
            organizer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sathi Connect Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sathi_connect (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            purpose TEXT,
            whatsapp TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Contact Messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Visitor Stats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitor_stats (
            date TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Background Task: Auto-Delete Expired Posts ---
def cleanup_expired_posts():
    while True:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Delete expired kirtans
            cursor.execute("DELETE FROM kirtans WHERE date < ?", (today,))
            # Delete expired bus services
            cursor.execute("DELETE FROM bus_seva WHERE departure_date < ?", (today,))
            
            conn.commit()
            conn.close()
            print(f"[{datetime.now()}] Cleanup task completed.")
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        time.sleep(3600) # Run every hour

# --- API Routes ---

# 1. Kirtan Endpoints
@app.route('/api/kirtans', methods=['GET'])
def get_kirtans():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kirtans WHERE date >= ? ORDER BY date ASC", (today,))
    rows = cursor.fetchall()
    conn.close()
    
    kirtans = []
    for r in rows:
        kirtans.append({
            "id": r[0], "name": r[1], "location": r[2], 
            "date": r[3], "pic": r[4], "organizer": r[5], "phone": r[6]
        })
    return jsonify(kirtans)

@app.route('/api/kirtans', methods=['POST'])
def add_kirtan():
    data = request.json
    if not is_clean(data.get('name')) or not is_clean(data.get('location')):
        return jsonify({"error": "Inappropriate language"}), 400
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO kirtans (name, location, date, pic_base64, organizer, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['name'], data['location'], data['date'], data.get('pic'), data.get('organizer'), data['phone']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kirtan added successfully"}), 201

# 2. Bus Seva Endpoints
@app.route('/api/bus', methods=['GET'])
def get_bus():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bus_seva WHERE departure_date >= ? ORDER BY departure_date ASC", (today,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "from": r[2], "to": r[3], "date": r[4], "seats": r[5], "phone": r[6]} for r in rows])

@app.route('/api/bus', methods=['POST'])
def add_bus():
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bus_seva (seva_name, origin, destination, departure_date, seats, phone, organizer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['name'], data['from'], data['to'], data['date'], data['seats'], data['phone'], data.get('organizer')))
    conn.commit()
    conn.close()
    return jsonify({"message": "Bus Seva added"}), 201

# 3. Sathi Connect Endpoints
@app.route('/api/sathi', methods=['GET'])
def get_sathi():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sathi_connect ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "location": r[2], "purpose": r[3], "whatsapp": r[4]} for r in rows])

@app.route('/api/sathi', methods=['POST'])
def add_sathi():
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sathi_connect (name, location, purpose, whatsapp) VALUES (?, ?, ?, ?)',
                   (data['name'], data['location'], data['purpose'], data['whatsapp']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Request posted"}), 201

# 4. Contact Form
@app.route('/api/contact', methods=['POST'])
def add_contact():
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)',
                   (data['name'], data['email'], data['message']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Message sent"}), 201

# 5. Admin Delete (General)
@app.route('/api/admin/delete/<table_name>/<int:id>', methods=['DELETE'])
def admin_delete(table_name, id):
    # Security Note: In production, verify Admin token here
    allowed_tables = ['kirtans', 'bus_seva', 'sathi_connect']
    if table_name not in allowed_tables:
        return jsonify({"error": "Invalid table"}), 400
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted successfully"})

# 6. Visitor Stats
@app.route('/api/visit', methods=['POST'])
def log_visit():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO visitor_stats (date, count) VALUES (?, 0)", (today,))
    cursor.execute("UPDATE visitor_stats SET count = count + 1 WHERE date = ?", (today,))
    conn.commit()
    conn.close()
    return jsonify({"status": "logged"})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM visitor_stats WHERE date = ?", (today,))
    row = cursor.fetchone()
    conn.close()
    return jsonify({"daily_visitors": row[0] if row else 0})

if __name__ == '__main__':
    init_db()
    # Start cleanup thread
    daemon = threading.Thread(target=cleanup_expired_posts, daemon=True)
    daemon.start()
    # Run server
    app.run(host='0.0.0.0', port=5000)