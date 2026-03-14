from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import create_connection
from datetime import datetime
import hashlib
import traceback

app = Flask(__name__)
app.secret_key = "your_secret_key_here_change_this_in_production"

# ==================== HOME PAGE ====================
@app.route('/')
def index():
    return render_template('index.html')

# ==================== USER REGISTRATION ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username or not email or not password or not confirm_password:
                flash("All fields are required!", "error")
                return redirect(url_for('register'))
            
            if len(username) < 3:
                flash("Username must be at least 3 characters!", "error")
                return redirect(url_for('register'))
            
            if len(password) < 6:
                flash("Password must be at least 6 characters!", "error")
                return redirect(url_for('register'))
            
            if password != confirm_password:
                flash("Passwords don't match!", "error")
                return redirect(url_for('register'))
            
            # Hash password
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            
            connection = create_connection()
            if not connection:
                flash("Database connection failed!", "error")
                return redirect(url_for('register'))
            
            cursor = connection.cursor()
            
            try:
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password)
                )
                connection.commit()
                flash("Registration successful! Please login.", "success")
                return redirect(url_for('login'))
            except Exception as e:
                connection.rollback()
                if "Duplicate entry" in str(e):
                    flash("Username or email already exists!", "error")
                else:
                    flash(f"Registration failed: {str(e)}", "error")
                return redirect(url_for('register'))
            finally:
                cursor.close()
                connection.close()
        
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('register'))
    
    return render_template('register.html')

# ==================== USER LOGIN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash("Username and password are required!", "error")
                return redirect(url_for('login'))
            
            # Hash password
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            
            connection = create_connection()
            if not connection:
                flash("Database connection failed!", "error")
                return redirect(url_for('login'))
            
            cursor = connection.cursor()
            cursor.execute(
                "SELECT user_id, username, email FROM users WHERE username=%s AND password=%s",
                (username, hashed_password)
            )
            user = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if user:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['email'] = user[2]
                flash(f"Welcome, {user[1]}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid username or password!", "error")
                return redirect(url_for('login'))
        
        except Exception as e:
            flash(f"Login error: {str(e)}", "error")
            return redirect(url_for('login'))
    
    return render_template('login.html')

# ==================== DASHBOARD ====================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login first!", "error")
        return redirect(url_for('login'))
    
    try:
        connection = create_connection()
        if not connection:
            flash("Database connection failed!", "error")
            return redirect(url_for('index'))
        
        cursor = connection.cursor()
        
        # Get all events
        cursor.execute("""
            SELECT e.event_id, e.event_name, e.description, e.event_date, e.event_time, 
                   e.location, e.capacity, u.username
            FROM events e
            JOIN users u ON e.organizer_id = u.user_id
            ORDER BY e.event_date DESC
        """)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'event_id': row[0],
                'event_name': row[1],
                'description': row[2],
                'event_date': str(row[3]),
                'event_time': str(row[4]),
                'location': row[5],
                'capacity': row[6],
                'organizer': row[7]
            })
        
        cursor.close()
        connection.close()
        
        return render_template('dashboard.html', events=events)
    
    except Exception as e:
        flash(f"Error loading events: {str(e)}", "error")
        return redirect(url_for('index'))

# ==================== CREATE EVENT ====================
@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'user_id' not in session:
        flash("Please login first!", "error")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            event_name = request.form.get('event_name', '').strip()
            description = request.form.get('description', '').strip()
            event_date = request.form.get('event_date', '')
            event_time = request.form.get('event_time', '')
            location = request.form.get('location', '').strip()
            capacity = request.form.get('capacity', '0')
            
            # Validation
            if not event_name or not event_date or not event_time or not location or not capacity:
                flash("All fields are required!", "error")
                return redirect(url_for('create_event'))
            
            try:
                capacity = int(capacity)
                if capacity <= 0:
                    flash("Capacity must be greater than 0!", "error")
                    return redirect(url_for('create_event'))
            except ValueError:
                flash("Capacity must be a number!", "error")
                return redirect(url_for('create_event'))
            
            connection = create_connection()
            if not connection:
                flash("Database connection failed!", "error")
                return redirect(url_for('create_event'))
            
            cursor = connection.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO events 
                    (event_name, description, event_date, event_time, location, capacity, organizer_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (event_name, description, event_date, event_time, location, capacity, session['user_id']))
                
                connection.commit()
                flash("Event created successfully!", "success")
                return redirect(url_for('dashboard'))
            
            except Exception as e:
                connection.rollback()
                flash(f"Error creating event: {str(e)}", "error")
                return redirect(url_for('create_event'))
            finally:
                cursor.close()
                connection.close()
        
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('create_event'))
    
    return render_template('create_event.html')

# ==================== REGISTER FOR EVENT ====================
@app.route('/register_event/<int:event_id>', methods=['POST'])
def register_event(event_id):
    if 'user_id' not in session:
        flash("Please login first!", "error")
        return redirect(url_for('login'))
    
    try:
        connection = create_connection()
        if not connection:
            flash("Database connection failed!", "error")
            return redirect(url_for('dashboard'))
        
        cursor = connection.cursor()
        
        # Check if already registered
        cursor.execute(
            "SELECT * FROM registrations WHERE user_id=%s AND event_id=%s",
            (session['user_id'], event_id)
        )
        if cursor.fetchone():
            flash("You are already registered for this event!", "error")
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard'))
        
        # Check event capacity
        cursor.execute(
            "SELECT capacity FROM events WHERE event_id=%s",
            (event_id,)
        )
        event = cursor.fetchone()
        if not event:
            flash("Event not found!", "error")
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard'))
        
        # Count registrations
        cursor.execute(
            "SELECT COUNT(*) FROM registrations WHERE event_id=%s",
            (event_id,)
        )
        registered_count = cursor.fetchone()[0]
        
        if registered_count >= event[0]:
            flash("Event is full! Cannot register.", "error")
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard'))
        
        # Register user
        cursor.execute("""
            INSERT INTO registrations (user_id, event_id)
            VALUES (%s, %s)
        """, (session['user_id'], event_id))
        
        connection.commit()
        flash("Successfully registered for the event!", "success")
        cursor.close()
        connection.close()
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        flash(f"Error registering: {str(e)}", "error")
        return redirect(url_for('dashboard'))

# ==================== VIEW MY REGISTRATIONS ====================
@app.route('/my_events')
def my_events():
    if 'user_id' not in session:
        flash("Please login first!", "error")
        return redirect(url_for('login'))
    
    try:
        connection = create_connection()
        if not connection:
            flash("Database connection failed!", "error")
            return redirect(url_for('index'))
        
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT e.event_id, e.event_name, e.description, e.event_date, e.event_time, 
                   e.location, e.capacity, u.username
            FROM registrations r
            JOIN events e ON r.event_id = e.event_id
            JOIN users u ON e.organizer_id = u.user_id
            WHERE r.user_id = %s
            ORDER BY e.event_date DESC
        """, (session['user_id'],))
        
        my_events_list = []
        for row in cursor.fetchall():
            my_events_list.append({
                'event_id': row[0],
                'event_name': row[1],
                'description': row[2],
                'event_date': str(row[3]),
                'event_time': str(row[4]),
                'location': row[5],
                'capacity': row[6],
                'organizer': row[7]
            })
        
        cursor.close()
        connection.close()
        
        return render_template('my_events.html', my_events=my_events_list)
    
    except Exception as e:
        flash(f"Error loading your events: {str(e)}", "error")
        return redirect(url_for('index'))

# ==================== LOGOUT ====================
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out!", "success")
    return redirect(url_for('index'))

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)