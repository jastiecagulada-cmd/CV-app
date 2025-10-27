import os
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret'

# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            course TEXT,
            year_level INTEGER
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
    conn.commit()
    conn.close()

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
    if request.method == 'POST':
        student_id = request.form['student_id']
        equipment = request.form['equipment'].split(',')
        action = request.form['action']
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        for item in equipment:
            c.execute("INSERT INTO equipment_log (student_id, equipment_name, action) VALUES (?, ?, ?)",
                      (student_id.strip(), item.strip(), action))
        conn.commit()
        conn.close()
        flash(f"{action.title()} logged successfully!")
        return redirect(url_for('borrow_return'))
    return render_template('borrow_return.html')

@app.route('/records', methods=['GET', 'POST'])
def records():
    logs = []
    if request.method == 'POST':
        student_id = request.form['student_id']
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT equipment_name, action, timestamp FROM equipment_log WHERE student_id = ? ORDER BY timestamp DESC", (student_id,))
        logs = c.fetchall()
        conn.close()
        return render_template('records.html', logs=logs)

    # --- Ensure DB is initialized and server starts ---
    if __name__ == "__main__":
        init_db()
        app.run(host=os.environ.get("FLASK_HOST", "127.0.0.1"),
                port=int(os.environ.get("FLASK_PORT", 5000)),
                debug=os.environ.get("FLASK_DEBUG", "False") == "True")
    return render_template('records.html', logs=logs)

@app.route('/history')
def history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT student_id, equipment_name, action, timestamp FROM equipment_log ORDER BY timestamp DESC")
    logs = c.fetchall()
    conn.close()
    return render_template('history.html', logs=logs)

if __name__ == '__main__':
    init_db()
    # Allow configuring host/port/debug via environment variables so Electron can control them
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    # When launched by Electron, use_reloader must be False to avoid double-launching the server
    app.run(host=host, port=port, debug=debug, use_reloader=False)
