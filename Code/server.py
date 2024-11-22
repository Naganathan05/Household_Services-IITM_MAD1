import sqlite3
import os
from flask import Flask, request, jsonify, redirect, session, render_template

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')
db_path = 'C:/Users/Dell/householdDB'

@app.route("/")
def home():
    return "Welcome to the Household Services App!"

@app.route("/adminLogin", methods=['GET'])
def loginAdmin():
    return render_template("loginAdmin.html")

@app.route("/loginUser", methods=['POST'])
def loginUser():
    print("Request Received")
    email = request.form.get("emailID")
    password = request.form.get("password")

    if not email or not password:
        return jsonify({"BAD_REQUEST": "Invalid credentials!"})

    print(f"Login attempt with username: {email}, password: {password}")

    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
            user = cur.fetchone()
            print("User Details")
            print(user)

            if user:
                if user[3] == password:
                    role = user[4]

                    print("User found successfully!")
                    session['user'] = email
                    session['role'] = role

                    if role == 'Admin':
                        return redirect("/adminHome")
                    elif role == 'Customer':
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

def initialize_database():
    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            cur.execute("DROP TABLE IF EXISTS Users")
            cur.execute("DROP TABLE IF EXISTS Services")
            cur.execute("DROP TABLE IF EXISTS ServiceRequests")
            cur.execute("DROP TABLE IF EXISTS Reviews")

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

            cur.execute("""
                INSERT OR IGNORE INTO Users (name, email, password, role)
                VALUES ("Naganathan", "naganathan1555@gmail.com", "Naganathan@15", "Admin")
            """)

            print("Tables created and seeded successfully!")

    except Exception as e:
        print("Error in table creation or connecting to server:", e)

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, port=8080)