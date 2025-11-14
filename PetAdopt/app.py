from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# ---------------------------
# MySQL CONFIGURATION
# ---------------------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # default user in XAMPP
app.config['MYSQL_PASSWORD'] = ''  # leave blank unless you set one
app.config['MYSQL_DB'] = 'petadopt'
mysql = MySQL(app)

# ---------------------------
# IMAGE CONFIG
# ---------------------------
app.config['UPLOAD_FOLDER'] = 'static/images'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---------------------------
# ROUTES
# ---------------------------

@app.route('/')
def home():
    return render_template('home.html')

# ✅ REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', [username])
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Username already exists.')
        else:
            cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)',
                           (username, password, email))
            mysql.connection.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

# ✅ LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()

        if account:
            session['user'] = account['username']
            session['user_id'] = account['id']
            flash('Login successful!')
            return redirect(url_for('pets_page'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

# ✅ PETS PAGE
@app.route('/pets')
def pets_page():
    if 'user' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    search_query = request.args.get('search', '')
    pet_type = request.args.get('type', 'all')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    sql = "SELECT * FROM pets"
    params = []

    if pet_type != 'all':
        sql += " WHERE type=%s"
        params.append(pet_type)
        if search_query:
            sql += " AND name LIKE %s"
            params.append('%' + search_query + '%')
    elif search_query:
        sql += " WHERE name LIKE %s"
        params.append('%' + search_query + '%')

    cursor.execute(sql, params)
    pets = cursor.fetchall()

    return render_template('pets.html', pets=pets, search_query=search_query, pet_type_filter=pet_type)

# ✅ PET DETAILS / ADOPTION
@app.route('/pet/<int:pet_id>', methods=['GET', 'POST'])
def pet_detail(pet_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM pets WHERE id = %s', [pet_id])
    pet = cursor.fetchone()

    if not pet:
        flash('Pet not found.')
        return redirect(url_for('pets_page'))

    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        message = request.form['message']
        user_id = session.get('user_id')

        cursor.execute('''
            INSERT INTO adoptions (user_id, pet_id, fullname, email, message, status)
            VALUES (%s, %s, %s, %s, %s, 'Pending')
        ''', (user_id, pet_id, fullname, email, message))

        cursor.execute('UPDATE pets SET status = "Adopted" WHERE id = %s', [pet_id])
        mysql.connection.commit()

        flash(f'Thank you, {fullname}! Your request to adopt {pet["name"]} has been submitted ❤️')
        return redirect(url_for('pets_page'))

    return render_template('pet_detail.html', pet=pet)

# ✅ PROFILE PAGE
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    user_id = session['user_id']

    # Handle profile update (email, phone, address)
    if request.method == 'POST':
        new_email = request.form.get('email')
        new_phone = request.form.get('phone')
        new_address = request.form.get('address')

        cursor.execute('''
            UPDATE users SET email=%s, phone=%s, address=%s WHERE id=%s
        ''', (new_email, new_phone, new_address, user_id))
        mysql.connection.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('profile'))

    # Fetch user info
    cursor.execute('SELECT * FROM users WHERE id = %s', [user_id])
    user = cursor.fetchone()

    # Fetch favorite pets
    cursor.execute('''
        SELECT pets.* FROM pets
        JOIN favorites ON pets.id = favorites.pet_id
        WHERE favorites.user_id = %s
    ''', [user_id])
    favorite_pets = cursor.fetchall()

    # Fetch adopted pets
    cursor.execute('''
        SELECT pets.* FROM pets
        JOIN adoptions ON pets.id = adoptions.pet_id
        WHERE adoptions.user_id = %s
    ''', [user_id])
    adopted_pets = cursor.fetchall()

    return render_template('profile.html', 
                           username=user['username'],
                           full_name=user.get('full_name', ''),
                           email=user.get('email', ''),
                           phone=user.get('phone', ''),
                           address=user.get('address', ''),
                           date_joined=user.get('date_joined', ''),
                           favorite_pets=favorite_pets,
                           adopted_pets=adopted_pets)

# ✅ LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('home'))

# ✅ RUN APP
if __name__ == '__main__':
    app.run(debug=True)
