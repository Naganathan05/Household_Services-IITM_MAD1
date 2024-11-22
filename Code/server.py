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

@app.route('/admin', methods=['GET'])
def getAdminDashboard():
    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            
            cur.execute("SELECT id, name, price AS base_price FROM Services")
            services = [{"id": row[0], "name": row[1], "base_price": row[2]} for row in cur.fetchall()]

            cur.execute("""
                SELECT u.id, u.name, sr.experience, sr.serviceName
                FROM Users u
                JOIN Professionals sr ON u.id = sr.userID
            """)

            professionals = [
                {
                    "id": row[0],
                    "name": row[1],
                    "experience": row[2],
                    "service_name": row[3]
                }
                for row in cur.fetchall()
            ]
            
            # Fetch and structure service requests data
            cur.execute("""
                SELECT sr.id, u.id AS assigned_professional, sr.date_of_request, sr.service_status
                FROM ServiceRequests sr
                LEFT JOIN Professionals u ON sr.professional_id = u.id
            """)
            service_requests = [
                {
                    "id": row[0],
                    "assigned_professional": row[1],
                    "requested_date": row[2],
                    "status": row[3]
                }
                for row in cur.fetchall()
            ]
        
        # Render the template with the structured data
        return render_template(
            'adminDashbord.html',
            services=services,
            professionals=professionals,
            service_requests=service_requests
        )
    
    except Exception as e:
        print("Error fetching data from database:", e)
        return "Error loading admin dashboard", 500
    
@app.route('/deleteService/<int:serviceID>', methods=['POST'])
def deleteService(serviceID):
    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            # Step 1: Get the service name for the given service ID
            cur.execute("SELECT name FROM Services WHERE id = ?", (serviceID,))
            service = cur.fetchone()

            if not service:
                return {"message": "Service not found"}, 404

            service_name = service[0]

            # Step 2: Delete related service requests
            cur.execute("DELETE FROM ServiceRequests WHERE service_id = ?", (serviceID,))

            # Step 3: Remove professionals offering this service
            cur.execute("DELETE FROM Professionals WHERE serviceName = ?", (service_name,))

            # Step 4: Delete the service itself
            cur.execute("DELETE FROM Services WHERE id = ?", (serviceID,))

            con.commit()
            return {"message": "Service and related data successfully deleted"}, 200

    except Exception as e:
        print("Error deleting service:", e)
        return {"message": "An error occurred while deleting the service"}, 500
    
@app.route('/editService/<int:serviceID>', methods=['GET'])
def getEditService(serviceID):
    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            # Fetch service details for the given service ID
            cur.execute("SELECT name, description, price, time_required FROM Services WHERE id = ?", (serviceID,))
            service = cur.fetchone()

            if not service:
                return {"message": "Service not found"}, 404
            
            serviceName, description, basePrice, timeRequired = service
            return render_template(
                "editService.html",
                serviceID=serviceID,
                serviceName=serviceName,
                description=description,
                basePrice=basePrice,
                timeRequired=timeRequired
            )
        
    except Exception as e:
        print("Error fetching service details:", e)
        return {"message": "An error occurred while fetching the service details"}, 500
    
@app.route('/editService/<int:serviceID>', methods=['PUT'])
def editService(serviceID):
    try:
        # Parse the JSON data sent from the frontend
        data = request.json
        serviceName = data.get('serviceName')
        description = data.get('description')
        basePrice = data.get('basePrice')
        timeRequired = data.get('timeRequired')

        # Validate the required fields
        if not (serviceName and description and basePrice and timeRequired):
            return {"message": "All fields are required"}, 400

        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            # Check if the service exists
            cur.execute("SELECT id FROM Services WHERE id = ?", (serviceID,))
            if not cur.fetchone():
                return {"message": "Service not found"}, 404

            # Update the service details in the database
            cur.execute("""
                UPDATE Services
                SET name = ?, description = ?, price = ?, time_required = ?
                WHERE id = ?
            """, (serviceName, description, basePrice, timeRequired, serviceID))
            con.commit()

        return {"message": "Service updated successfully"}, 200

    except Exception as e:
        print("Error updating service details:", e)
        return {"message": "An error occurred while updating the service details"}, 500



@app.route('/newService', methods = ['GET'])
def newService():
    return render_template("newService.html")

@app.route('/newService', methods=['POST'])
def addService():
    try:
        print("Received a POST Request")
        # data = request.get_json()
        service_name = request.form.get('serviceName')
        description = request.form.get('description')
        base_price = request.form.get('basePrice')
        timeRequired = request.form.get('timeRequired')
        # service_name = data.get('serviceName')
        # description = data.get('description')
        # base_price = data.get('basePrice')
        # timeRequired = data.get('timeRequired')

        if not service_name or not base_price:
            print("Error 1")
            return jsonify({"error": "Service name and base price are required!"}), 400

        try:
            base_price = float(base_price)
        except ValueError:
            return jsonify({"error": "Base price must be a valid number!"}), 400

        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO Services (name, price, description, time_required)
                VALUES (?, ?, ?, ?)
            """, (service_name, base_price, description, timeRequired))
            con.commit()

        return jsonify({"message": "Service added successfully!"}), 201

    except Exception as e:
        print("Error 2")
        print(e)
        print(jsonify({"error": str(e)}))
    return render_template("loginAdmin.html")


def initialize_database():
    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            cur.execute("DROP TABLE IF EXISTS Users")
            cur.execute("DROP TABLE IF EXISTS Services")
            cur.execute("DROP TABLE IF EXISTS ServiceRequests")
            cur.execute("DROP TABLE IF EXISTS Reviews")
            cur.execute("DROP TABLE IF EXISTS Professionals")

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
                CREATE TABLE IF NOT EXISTS Professionals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    userID INTEGER NOT NULL,
                    serviceName VARCHAR(255) NOT NULL,
                    experience INTEGER NOT NULL,
                    FOREIGN KEY (userID) REFERENCES Users (id),
                    FOREIGN KEY (serviceName) REFERENCES Services (name)
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
                    FOREIGN KEY (professional_id) REFERENCES Professionals (id)
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
            cur.execute("""
                INSERT OR IGNORE INTO Services (name, price, time_required, description)
                VALUES ("ABC", 5000, 2, "This is a New Service")
            """)
            cur.execute("""
                INSERT INTO Users (name, email, password, role)
                VALUES ("worker", "naganathan155@gmail.com", "Naganathan@15", "Professional")
            """)
            cur.execute("""
                INSERT OR IGNORE INTO Professionals (userID, serviceName, experience)
                VALUES (2, "worker", 5)
            """)
            cur.execute("""
                INSERT OR IGNORE INTO ServiceRequests (service_id, customer_id, professional_id, date_of_request, service_status)
                VALUES (1, 1, 1, CURRENT_DATE, "Requested")
            """)

            print("Tables created and seeded successfully!")

    except Exception as e:
        print("Error in table creation or connecting to server:", e)

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, port=8080)