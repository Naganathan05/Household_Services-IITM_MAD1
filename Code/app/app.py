import sqlite3
import os
from flask import *

app = Flask(__name__)

# Secret key for session management
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')
db_path = 'C:/Users/Dell/householdDB' 

# Flask app routes and main logic
@app.route("/")
def home():
    return "Welcome to the Household Services App!"

@app.route("/loginUser", methods=['POST'])
def loginUser():
    data = request.get_json()
    username = data.get("userName")
    password = data.get("password")

    if not username or not password:
        return jsonify({"BAD_REQUEST": "Invalid credentials!"})

    print(f"Login attempt with username: {username}, password: {password}")

    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            cur.execute("SELECT * FROM Users WHERE username = ?", (username,))
            user = cur.fetchone()

            if user:
                # Check if the password matches the hashed password
                if check_password_hash(user[2], password):  # Assuming the password is stored in the 2nd index
                    role = user[4]  # The role is at index 4 in the 'Users' table

                    print("User found successfully!")
                    session['user'] = username
                    session['role'] = role

                    # Redirect based on user role (1 for Admin, 0 for regular user)
                    if role == 'Admin':  # Assuming 'Admin' is stored as role value
                        return redirect("/adminHome")
                    elif role == 'Customer':  # Assuming 'Customer' is stored as role value
                        return redirect("/userHome")
                    else:
                        return redirect("/login")

                else:
                    return jsonify({"BAD_REQUEST": "Incorrect password!"})

            else:
                return jsonify({"BAD_REQUEST": "User not found!"})

    except sqlite3.Error as e:
        print(f"Error connecting to the database: {e}")
        return jsonify({"ERROR": "Database connection error!"})

    return redirect("/login")


# Database initialization
def initialize_database():
    try:
        # Establish a connection to SQLite database
        with sqlite3.connect("C:/Users/Dell/householdDB") as con:
            cur = con.cursor()
            
            # Create Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    created_at DATE DEFAULT CURRENT_DATE
                )
            """)

            # Create Services table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    price REAL NOT NULL,
                    time_required INTEGER NOT NULL,
                    description TEXT,
                    created_at DATE DEFAULT CURRENT_DATE
                )
            """)

            # Create ServiceRequests table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ServiceRequests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id INTEGER NOT NULL,
                    customer_id INTEGER NOT NULL,
                    professional_id INTEGER,
                    date_of_request DATE NOT NULL,
                    date_of_completion DATE,
                    service_status VARCHAR(50) NOT NULL,
                    remarks TEXT,
                    FOREIGN KEY (service_id) REFERENCES Services (id),
                    FOREIGN KEY (customer_id) REFERENCES Users (id),
                    FOREIGN KEY (professional_id) REFERENCES Users (id)
                )
            """)

            # Create Reviews table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_request_id INTEGER NOT NULL,
                    reviewer_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    comment TEXT,
                    created_at DATE DEFAULT CURRENT_DATE,
                    FOREIGN KEY (service_request_id) REFERENCES ServiceRequests (id),
                    FOREIGN KEY (reviewer_id) REFERENCES Users (id)
                )
            """)

            print("Tables created successfully!")
    except Exception as e:
        print("Error in table creation or connecting to server:", e)


if __name__ == '__main__':
    initialize_database()
    app.run(debug = True, port=8080)