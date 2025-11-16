import os
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from ultralytics import YOLO
import cv2
import numpy as np
import base64

# Load YOLO model once - use relative path
model_path = os.path.join(os.path.dirname(__file__), "after_dsmtf.pt")
model = YOLO(model_path)

app = Flask(__name__)
app.secret_key = 'secret'

# Map YOLO class names to actual inventory names
CLASS_TO_EQUIPMENT = {
    "graduated_cylinder": "Graduated Cylinder",
    "beaker": "Beaker",
    'compass': 'Compass',
    'digital_balance': 'Digital Balance',
    'erlenmeyer_flask': 'Erlenmeyer Flask',
    'funnel': 'Funnel',
    'horseshoe_magnet': 'Horseshoe Magnet',
    'test_tube_rack': 'Test Tube Rack',
    'triple_beam_balance': 'Triple Beam Balance',
    'tripod': 'Tripod',
}

# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            course TEXT,
            year_level INTEGER,
            number_of_equipment INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS equipment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            action TEXT CHECK(action IN ('borrow', 'return')),
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            quantity INTEGER DEFAULT 0
        )
    ''')
    
    # Add the new column to existing tables if it doesn't already exist
    try:
        c.execute("ALTER TABLE students ADD COLUMN number_of_equipment INTEGER DEFAULT 0")
    except:
        pass  # Column already exists
    
    conn.commit()
    conn.close()

# ---------- Helper Functions ----------
def get_inventory():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, name, quantity FROM inventory ORDER BY name ASC")
    items = c.fetchall()
    conn.close()
    return items

def get_inventory_dict():
    """Return dict: equipment_name -> quantity"""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT name, quantity FROM inventory")
    items = c.fetchall()
    conn.close()
    return {name: qty for name, qty in items}

# ---------- Routes ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        sid = request.form['student_id']
        name = request.form['name']
        course = request.form['course']
        year = request.form['year_level']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO students VALUES (?, ?, ?, ?)", (sid, name, course, year))
        conn.commit()
        conn.close()
        flash("Student registered successfully!")
        return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/borrow_return', methods=['GET', 'POST'])
def borrow_return():
    inventory = get_inventory()
    inventory_dict = get_inventory_dict()
    detected_items = request.args.get('detected')
    if detected_items:
        detected_items = detected_items.split(',')

    if request.method == 'POST':
        student_id = request.form['student_id']
        action = request.form['action']
        equipment_name = request.form['equipment_name']
        quantity = int(request.form.get('quantity', 1))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        
        # Verify equipment exists in inventory
        c.execute("SELECT quantity FROM inventory WHERE name=?", (equipment_name,))
        row = c.fetchone()
        if not row:
            flash("Equipment not found in inventory.")
        else:
            # Verify student exists
            c.execute("SELECT number_of_equipment FROM students WHERE student_id=?", (student_id,))
            student_row = c.fetchone()
            if not student_row:
                flash("Student not found. Please register first.")
            else:
                current_student_items = student_row[0] or 0
                
                # Log the action (inventory is NOT updated here - only via admin inventory page)
                c.execute("INSERT INTO equipment_log (student_id, equipment_name, action) VALUES (?, ?, ?)",
                          (student_id, equipment_name, action))
                
                # Update student's equipment count
                if action == "borrow":
                    new_count = current_student_items + quantity
                    c.execute("UPDATE students SET number_of_equipment=? WHERE student_id=?", 
                              (new_count, student_id))
                    flash(f"Borrowed {quantity} × {equipment_name}.")
                elif action == "return":
                    new_count = max(0, current_student_items - quantity)  # Ensure non-negative
                    c.execute("UPDATE students SET number_of_equipment=? WHERE student_id=?", 
                              (new_count, student_id))
                    flash(f"Returned {quantity} × {equipment_name}.")
        
        conn.commit()
        conn.close()
        return redirect(url_for('borrow_return'))

    return render_template("borrow_return.html",
                           inventory=inventory,
                           inventory_dict=inventory_dict,
                           detected_items=detected_items)

@app.route('/process_capture', methods=['POST'])
def process_capture():
    image_data = request.form['image_data'].split(",")[1]
    nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    results = model(frame)
    detected_classes = set()
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            detected_classes.add(model.names[cls_id])

    # Map class names to inventory names
    detected_equipment = []
    inventory_dict = get_inventory_dict()
    for cls in detected_classes:
        if cls in CLASS_TO_EQUIPMENT and CLASS_TO_EQUIPMENT[cls] in inventory_dict:
            detected_equipment.append(CLASS_TO_EQUIPMENT[cls])

    if detected_equipment:
        flash("Detected: " + ", ".join(detected_equipment))
        return redirect(url_for("borrow_return", detected=",".join(detected_equipment)))
    else:
        flash("No valid equipment detected in inventory.")
        return redirect(url_for("borrow_return"))

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form['name'].strip()
            quantity = int(request.form['quantity'])
            if name:
                try:
                    c.execute("INSERT INTO inventory (name, quantity) VALUES (?, ?)", (name, quantity))
                    conn.commit()
                    flash("Equipment added successfully.")
                except sqlite3.IntegrityError:
                    flash("Equipment already exists.")
        elif action == 'update':
            item_id = request.form['item_id']
            quantity = int(request.form['quantity'])
            c.execute("UPDATE inventory SET quantity=? WHERE id=?", (quantity, item_id))
            conn.commit()
            flash("Quantity updated.")
        elif action == 'delete':
            item_id = request.form['item_id']
            c.execute("DELETE FROM inventory WHERE id=?", (item_id,))
            conn.commit()
            flash("Equipment deleted.")
        return redirect(url_for('inventory'))

    c.execute("SELECT id, name, quantity FROM inventory ORDER BY name ASC")
    items = c.fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

@app.route('/records', methods=['GET', 'POST'])
def records():
    logs = []
    if request.method == 'POST':
        student_id = request.form['student_id']
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT equipment_name, action, timestamp FROM equipment_log WHERE student_id=? ORDER BY timestamp DESC", (student_id,))
        logs = c.fetchall()
        conn.close()
    return render_template('records.html', logs=logs)

@app.route('/history')
def history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT student_id, equipment_name, action, timestamp FROM equipment_log ORDER BY timestamp DESC")
    logs = c.fetchall()
    conn.close()
    return render_template('history.html', logs=logs)

# ---------- Run Server ----------
if __name__ == '__main__':
    init_db()
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host=host, port=port, debug=debug, use_reloader=False)
