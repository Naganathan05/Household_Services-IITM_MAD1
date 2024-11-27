import sqlite3
import os
from flask import Flask, request, jsonify, redirect, session, render_template, abort
from datetime import datetime

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')
db_path = 'C:/Users/Dell/householdDB'

@app.route("/")
def home():
    return "Welcome to the Household Services App!"

@app.route("/adminLogin", methods=['GET'])
def loginAdmin():
    return render_template("login.html")

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
                    session['id'] = user[0]
                    session['role'] = role

                    if role == 'Admin':
                        return redirect("/admin")
                    elif role == 'Customer':
                        return redirect("/customer")
                    elif role == "Professional":
                        return redirect("/professionalDashboard")

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
                SELECT u.id, u.name, sr.experience, sr.serviceName, sr.status
                FROM Users u
                JOIN Professionals sr ON u.id = sr.userID
            """)

            professionals = [
                {
                    "id": row[0],
                    "name": row[1],
                    "experience": row[2],
                    "service_name": row[3],
                    "status": row[4]
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
            return redirect('/admin')

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

        return redirect('/admin')

    except Exception as e:
        print("Error 2")
        print(e)
        print(jsonify({"error": str(e)}))

@app.route('/searchAdmin', methods = ['GET'])
def getSearchAdmin():
    return render_template("adminSearch.html")

@app.route('/registerCustomer', methods = ['GET'])
def getRegisterCustomer():
    return render_template("registerCustomer.html")

@app.route('/serviceRemarks', methods = ['GET'])
def getServiceRemarks():
    return render_template("serviceRemarks.html")

@app.route('/searchService', methods = ['GET'])
def getSearchService():
    return render_template("searchService.html")

@app.route('/customer', methods=['GET'])
def customerDashboard():
    user_id = session['id']

    # Fetch customer_id using userID from Customers table
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id FROM Customers WHERE userID = ?", (user_id,))
        result = cur.fetchone()

    if not result:
        # If no customer entry exists for the userID, redirect to login or error page
        return redirect('adminLogin')

    customer_id = result[0]  # Extract customer_id from the query result
    print("Mapped Customer ID: ", customer_id)

    # Fetch available services
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id, name FROM Services")
        services = cur.fetchall()  # List of tuples [(id, name), ...]

    # Fetch all service requests for the mapped customer_id
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT sr.id, 
                s.name AS service_name, 
                u.name AS professional_name, 
                p.phoneNumber AS professional_phone, 
                sr.service_status
            FROM ServiceRequests sr
            JOIN Services s ON sr.service_id = s.id
            LEFT JOIN Professionals p ON sr.professional_id = p.id
            LEFT JOIN Users u ON p.userID = u.id
            WHERE sr.customer_id = ?
        """, (customer_id,))
        service_requests = cur.fetchall()
        print("Fetched Resukts: ")
        print(service_requests)

    # Render the dashboard template
    return render_template(
        'customerDashboard.html',
        services=services,
        service_requests=service_requests
    )

@app.route('/searchServiceRequests', methods=['GET'])
def search_service_requests():
    try:
        # Get the search word (professional_id) from query parameters
        professional_id = request.args.get('q', type=int)

        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            # Query to fetch records matching the searched professional_id
            cur.execute("""
                SELECT sr.id, u.id AS assigned_professional, sr.date_of_request, sr.service_status
                FROM ServiceRequests sr
                LEFT JOIN Professionals u ON sr.professional_id = u.id
                WHERE sr.professional_id = ?
            """, (professional_id,))
            
            # Fetch the matching records and format them
            service_requests = [
                {
                    "id": row[0],
                    "assigned_professional": row[1],
                    "requested_date": row[2],
                    "status": row[3]
                }
                for row in cur.fetchall()
            ]
        
        return jsonify(service_requests), 200

    except Exception as e:
        print("Error fetching service requests:", e)
        return {"message": "An error occurred while fetching service requests"}, 500

@app.route('/searchProfessionals', methods=['GET'])
def search_professionals():
    try:
        # Get the search word (professional name) from query parameters
        search_word = request.args.get('q', type=str)

        # Ensure search_word is not None
        if not search_word:
            return {"message": "Search word cannot be empty"}, 400

        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            # Correct SQL query to fetch professionals by name
            cur.execute("""
                SELECT u.id AS userID, u.name AS name, p.serviceName AS service_name, p.status
                FROM Professionals p
                INNER JOIN Users u ON p.userID = u.id
                WHERE u.name LIKE ?
            """, (f"%{search_word}%",))  # Use LIKE for partial matching
            
            # Fetch the matching records and format them
            professionals = [
                {
                    "userID": row[0],
                    "name": row[1],
                    "service_name": row[2],
                    "status": row[3]
                }
                for row in cur.fetchall()
            ]

        # Return the results in JSON format
        return jsonify(professionals), 200

    except sqlite3.OperationalError as e:
        print("SQL error:", e)
        return {"message": f"SQL error: {e}"}, 500
    except Exception as e:
        print("Error fetching professionals:", e)
        return {"message": "An error occurred while fetching professionals"}, 500

@app.route('/searchCustomers', methods=['GET'])
def search_customers():
    try:
        # Log the search request
        print("Search Came for Customers !!")
        
        # Get the search word (customer name) from query parameters
        search_word = request.args.get('q', type=str)

        # Ensure search_word is not None
        if search_word is None:
            return {"message": "Search word cannot be None"}, 400

        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            # Adjust the SQL query based on whether the search word is empty
            if search_word.strip() == "":
                # Fetch all records where role is Customer
                cur.execute("""
                    SELECT id AS userID, name, email, role
                    FROM Users
                    WHERE role = 'Customer'
                """)
            else:
                # Fetch records matching the search word and role is Customer
                cur.execute("""
                    SELECT id AS userID, name, email
                    FROM Users
                    WHERE role = 'Customer' AND name LIKE ?
                """, (f"%{search_word}%",))  # Use LIKE for partial matching
            
            # Fetch the matching records and format them
            customers = [
                {
                    "name": row[1],
                    "userID": row[0],
                    "email": row[2]
                }
                for row in cur.fetchall()
            ]

        # Return the results in JSON format
        return jsonify(customers), 200

    except sqlite3.OperationalError as e:
        print("SQL error:", e)
        return {"message": f"SQL error: {e}"}, 500
    except Exception as e:
        print("Error fetching customers:", e)
        return {"message": "An error occurred while fetching customers"}, 500

@app.route('/registerCustomer', methods=['POST'])
def register_customer():
    try:
        # Get data from the form submission
        email = request.form['email']
        password = request.form['password']
        fullname = request.form['fullname']
        address = request.form['address']
        pin_code = request.form['pin_code']

        # Connect to the database
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            cur.execute("""
                INSERT INTO Users (email, password, name, role)
                VALUES (?, ?, ?, ?)
            """, (email, password, fullname, 'Customer'))


            user_id = cur.lastrowid
            cur.execute("""
                INSERT INTO Customers (userID, address, PinCode)
                VALUES (?, ?, ?)
            """, (user_id, address, pin_code))

            con.commit()

        return redirect('/adminLogin')

    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500
    
@app.route('/getProfessionals/<serviceName>', methods=['GET'])
def get_professionals(serviceName):
    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            # Query to fetch professionals who match the given service name

            cur.execute("""
                SELECT p.userID, u.name, p.phoneNumber 
                FROM Professionals p
                JOIN Users u ON p.userID = u.id
                WHERE p.serviceName = ?
            """, (serviceName,))
            
            # Fetch all matching professionals
            professionals = cur.fetchall()
            print("Reached Here !!")
            print(professionals)

            # Format the response
            response = {
                "status": "success",
                "professionals": [
                    {"id": row[0], "name": row[1], "phone": row[2]} for row in professionals
                ]
            }
            return jsonify(response), 200

    except Exception as e:
        # Handle any exceptions and return an error response
        response = {
            "status": "error",
            "message": str(e)
        }
        print(e)
        return jsonify(response), 500
    

@app.route('/bookService', methods=['POST'])
def book_service():
    try:
        # Parse the JSON request body
        print("Reached Here into Booking !!")
        data = request.get_json()
        service_id = data.get('serviceId')
        professional_User_id = data.get('professionalId')
        
        # Get the user ID from the session
        user_id = session.get('id')
        print("This is USER ID: ")
        print(user_id)
        if not user_id:
            return {"message": "Unauthorized. Please log in as a customer."}, 401

        # Fetch customer_id from the database using user_id
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT id FROM Customers WHERE userID = ?
            """, (user_id,))
            customer = cur.fetchone()

            if not customer:
                return {"message": "Customer not found for the given user."}, 404

            customer_id = customer[0]  # Extract customer_id from the result

        # Fetch professional_id from the Professionals table using user_id
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT id FROM Professionals WHERE userID = ?
            """, (professional_User_id,))
            professional = cur.fetchone()

            if not professional:
                return {"message": "Professional not found for the given user."}, 404

            professional_id = professional[0]  # Extract professional_id from the result

        # Check if a service request already exists
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT 1 FROM ServiceRequests 
                WHERE customer_id = ? AND professional_id = ?
            """, (customer_id, professional_id))
            existing_request = cur.fetchone()

            if existing_request:
                return {"message": "Service request already exists for this customer and professional."}, 400

        # Set the current date for the service request
        date_of_request = datetime.now().strftime('%Y-%m-%d')
        service_status = "Requested"

        # Insert a new record into ServiceRequests table
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO ServiceRequests (service_id, customer_id, professional_id, date_of_request, service_status)
                VALUES (?, ?, ?, ?, ?)
            """, (service_id, customer_id, professional_id, date_of_request, service_status))

            # Commit the transaction
        con.commit()

        # Return a success message
        return {"message": "Service request booked successfully!"}, 200

    except Exception as e:
        # Handle errors and return an appropriate message
        print(e)
        return {"message": f"An error occurred: {str(e)}"}, 500

@app.route('/bookServiceCustomer', methods=['POST'])
def bookService():
    try:
        # Parse the JSON request body
        print("Reached Here into Booking !!")
        data = request.get_json()
        service_id = data.get('serviceId')
        professional_id = data.get('professionalId')
        
        # Get the user ID from the session
        user_id = session.get('id')
        print("This is USER ID: ")
        print(user_id)
        if not user_id:
            return {"message": "Unauthorized. Please log in as a customer."}, 401

        # Fetch customer_id from the database using user_id
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT id FROM Customers WHERE userID = ?
            """, (user_id,))
            customer = cur.fetchone()

            if not customer:
                return {"message": "Customer not found for the given user."}, 404

            customer_id = customer[0]  # Extract customer_id from the result

        # Check if a service request already exists
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT 1 FROM ServiceRequests 
                WHERE customer_id = ? AND professional_id = ?
            """, (customer_id, professional_id))
            existing_request = cur.fetchone()

            if existing_request:
                return {"message": "Service request already exists for this customer and professional."}, 400

        # Set the current date for the service request
        date_of_request = datetime.now().strftime('%Y-%m-%d')
        service_status = "Requested"

        # Insert a new record into ServiceRequests table
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO ServiceRequests (service_id, customer_id, professional_id, date_of_request, service_status)
                VALUES (?, ?, ?, ?, ?)
            """, (service_id, customer_id, professional_id, date_of_request, service_status))

            # Commit the transaction
        con.commit()

        # Return a success message
        return {"message": "Service request booked successfully!"}, 200

    except Exception as e:
        # Handle errors and return an appropriate message
        print(e)
        return {"message": f"An error occurred: {str(e)}"}, 500

    
    
def get_service_request_details(service_request_id, user_id):
    connection = sqlite3.connect(db_path)  # Replace with your database file
    cursor = connection.cursor()
    print("UserID and Service Request ID: ")
    print(user_id, service_request_id)
    
    try:
        # Query to fetch service request details
        cursor.execute("""
        SELECT 
            sr.id, 
            s.name AS serviceName, 
            s.description, 
            sr.date_of_request, 
            p.id AS professional_id, 
            u.name AS professional_name, 
            p.phoneNumber AS contact_no, 
            sr.remarks
        FROM 
            ServiceRequests sr
        LEFT JOIN 
            Services s ON sr.service_id = s.id
        LEFT JOIN 
            Professionals p ON sr.professional_id = p.id
        LEFT JOIN 
            Users u ON p.userID = u.id
        WHERE 
            sr.id = ?
            AND u.id = ?;
        """, (service_request_id, user_id))
        
        result = cursor.fetchone()
        connection.close()
        
        if not result:
            return None
        
        # Return the result as a dictionary
        return {
            "request_id": result[0],
            "service_name": result[1],
            "description": result[2],
            "date": result[3],
            "professional_id": result[4],
            "professional_name": result[5],
            "contact_no": result[6],
            "remarks": result[7],
        }
    except sqlite3.Error as e:
        connection.close()
        print(f"Database error: {e}")
        return None

# Flask route
@app.route('/getRemarks/<int:service_request_id>', methods=['GET'])
def get_remarks(service_request_id):
    # Fetch details from the database
    user_id = session.get('id') 
    service_request_details = get_service_request_details(service_request_id, user_id)
    
    if not service_request_details:
        abort(404, description="Service request not found.")
    
    # Render the serviceRemarks.html page with the fetched data
    return render_template("serviceRemarks.html", **service_request_details)

@app.route('/searchCustomer/<serviceName>', methods=['GET'])
def search_customer(serviceName):
    try:
        # Connect to the database
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            
            # Query to fetch service ID and related professionals
            cur.execute("""
                SELECT 
                    s.id AS serviceID,
                    p.id AS professionalID,
                    p.experience,
                    p.phoneNumber
                FROM 
                    Services s
                JOIN 
                    Professionals p 
                ON 
                    s.name = p.serviceName
                WHERE 
                    s.name LIKE ?
            """, (f'%{serviceName}%',))  # Allow partial matches with LIKE
            
            # Fetch all results
            results = cur.fetchall()
            
            # Prepare the response data
            response_data = [
                {
                    "serviceID": row[0],
                    "professionalID": row[1],
                    "experience": row[2],
                    "phoneNumber": row[3]
                }
                for row in results
            ]

        # Return the results as JSON
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "An error occurred while searching for services."}), 500
    
@app.route('/professionalDashboard', methods=['GET'])
def professionalDashboard():
    try:
        # Connect to the database
        connection = sqlite3.connect(db_path)  # Adjust to your actual database file
        cursor = connection.cursor()

        # SQL query to fetch all necessary data from ServiceRequests, Customers, and Users tables
        query = '''
            SELECT 
                sr.id AS service_request_id,
                u.name AS customer_name,
                u.id AS user_id,
                c.address AS address,
                c.PinCode AS pincode,
                u.email AS phone,  -- Assuming email is the phone number as per provided schema
                sr.service_status AS status,
                sr.date_of_request AS date,
                r.rating AS rating
            FROM 
                ServiceRequests sr
            JOIN 
                Customers c ON sr.customer_id = c.id
            JOIN 
                Users u ON c.userID = u.id
            LEFT JOIN 
                Reviews r ON sr.id = r.service_request_id
        '''

        # Execute the query and fetch all results
        cursor.execute(query)
        service_requests = cursor.fetchall()

        # Convert the results into a list of dictionaries for easy rendering
        services = []
        for row in service_requests:
            services.append({
                "id": row[0],
                "customerName": row[1],
                "userID": row[2],
                "address": row[3],
                "pincode": row[4],
                "phone": row[5],
                "status": row[6],
                "date": row[7],
                "rating": row[8] if row[8] else 'N/A'
            })

        # Close the database connection
        cursor.close()
        connection.close()

        # Render the HTML template with the fetched services data
        return render_template('professionalDashboard.html', services=services)

    except Exception as e:
        print(f"Error fetching service requests: {e}")
        return "Error loading dashboard", 500

@app.route('/acceptServiceRequest/<int:serviceRequestID>', methods=['GET'])
def accept_service_request(serviceRequestID):
    try:
        # Connect to the database
        connection = sqlite3.connect(db_path)  # Replace with your DB connection
        cursor = connection.cursor()
        
        # Update the status to 'Accepted' for the given serviceRequestID
        cursor.execute('''
            UPDATE ServiceRequests
            SET service_status = 'Accepted'
            WHERE id = ?
        ''', (serviceRequestID,))
        
        # Commit the changes and close the connection
        connection.commit()
        cursor.close()
        connection.close()
        
        # Redirect to the professional dashboard to refresh the page
        return redirect('/professionalDashboard')
    
    except Exception as e:
        print(f"Error updating service request: {e}")
        return "Error processing the request", 500

@app.route('/rejectServiceRequest/<int:serviceRequestID>', methods=['GET'])
def reject_service_request(serviceRequestID):
    try:
        # Connect to the database
        connection = sqlite3.connect(db_path)  # Replace with your DB connection
        cursor = connection.cursor()
        
        # Update the status to 'Accepted' for the given serviceRequestID
        cursor.execute('''
            UPDATE ServiceRequests
            SET service_status = 'Requested'
            WHERE id = ?
        ''', (serviceRequestID,))
        
        # Commit the changes and close the connection
        connection.commit()
        cursor.close()
        connection.close()
        
        # Redirect to the professional dashboard to refresh the page
        return redirect('/professionalDashboard')
    
    except Exception as e:
        print(f"Error updating service request: {e}")
        return "Error processing the request", 500

def initialize_database():
    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()

            cur.execute("DROP TABLE IF EXISTS ServiceRequests")
            cur.execute("DROP TABLE IF EXISTS Professionals")
            cur.execute("DROP TABLE IF EXISTS Services")
            cur.execute("DROP TABLE IF EXISTS Reviews")
            cur.execute("DROP TABLE IF EXISTS Customers")
            cur.execute("DROP TABLE IF EXISTS Users")

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
                    phoneNumber INTEGER NOT NULL,
                    status VARCHAR(255),
                    FOREIGN KEY (userID) REFERENCES Users (id),
                    FOREIGN KEY (serviceName) REFERENCES Services (name)
                )
                         
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS Customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    userID INTEGER NOT NULL,
                    phoneNumber INTEGER NOT NULL,
                    address VARCHAR(255) NOT NULL,
                    PinCode INTEGER NOT NULL
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
                INSERT OR IGNORE INTO Professionals (userID, serviceName, experience, phoneNumber, status)
                VALUES (2, "ABC", 5, 9080800380, "Not Approved")
            """)
            cur.execute("""
                INSERT OR IGNORE INTO Users (name, email, password, role)
                VALUES ("dummy", "naganathan55@gmail.com", "Naganathan@15", "Customer")
            """)
            cur.execute("""
                INSERT OR IGNORE INTO Customers (userID, phoneNumber, address, PinCode)
                VALUES (3, 9080800380, "YMR Patti", 624001)
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