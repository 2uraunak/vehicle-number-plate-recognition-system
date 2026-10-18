import os
import re
import time
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SQLite database for vehicle logs
def init_db():
    conn = sqlite3.connect('vehicle_records.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  plate_number TEXT,
                  state_code TEXT,
                  confidence REAL,
                  timestamp TEXT,
                  image_path TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Indian state code mapping
STATE_CODES = {
    'DL': 'Delhi', 'MH': 'Maharashtra', 'KA': 'Karnataka', 'TN': 'Tamil Nadu',
    'UP': 'Uttar Pradesh', 'HR': 'Haryana', 'GJ': 'Gujarat', 'WB': 'West Bengal',
    'AP': 'Andhra Pradesh', 'TS': 'Telangana', 'KL': 'Kerala', 'RJ': 'Rajasthan'
}

def mock_anpr_inference(image_path):
    # Simulated robust OCR detection for standard plates
    filename = os.path.basename(image_path).lower()
    if 'dl' in filename:
        plate = "DL 01 AB 1234"
        conf = 98.4
    elif 'ka' in filename:
        plate = "KA 05 MN 9876"
        conf = 96.8
    elif 'mh' in filename:
        plate = "MH 12 DE 5678"
        conf = 97.2
    else:
        # Default detected plate
        plate = "HR 26 DQ 5555"
        conf = 95.6

    state_prefix = plate[:2]
    state_name = STATE_CODES.get(state_prefix, "India Union")
    return plate, conf, state_name

@app.route('/')
def home():
    conn = sqlite3.connect('vehicle_records.db')
    c = conn.cursor()
    c.execute("SELECT plate_number, state_code, confidence, timestamp, image_path FROM vehicle_log ORDER BY id DESC LIMIT 10")
    recent_logs = c.fetchall()
    conn.close()
    return render_template('index.html', logs=recent_logs)

@app.route('/scan', methods=['POST'])
def scan_vehicle():
    if 'vehicle_image' not in request.files:
        return redirect(url_for('home'))
    file = request.files['vehicle_image']
    if file.filename == '':
        return redirect(url_for('home'))
        
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    
    plate, conf, state = mock_anpr_inference(save_path)
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Save to database
    conn = sqlite3.connect('vehicle_records.db')
    c = conn.cursor()
    c.execute("INSERT INTO vehicle_log (plate_number, state_code, confidence, timestamp, image_path) VALUES (?, ?, ?, ?, ?)",
              (plate, state, conf, ts, filename))
    conn.commit()
    conn.close()
    
    return render_template('index.html', 
                           scanned=True, 
                           plate=plate, 
                           confidence=conf, 
                           state=state, 
                           image_file=filename,
                           timestamp=ts)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
