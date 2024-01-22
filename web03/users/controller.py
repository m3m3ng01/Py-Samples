#users/controller.py
import re  # Import the regular expressions library
#import secrets
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import current_user, login_required, login_user
from werkzeug.security import check_password_hash, generate_password_hash

from .model import User


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

Users_blueprint = Blueprint('users', __name__)


@Users_blueprint.route("/register", methods=["POST"])
def register():
    limiter=current_app.config['limiter']
    db_session=current_app.config['db_session']
    @limiter.limit("1 per minute")  # Additional rate limiting for this endpoint
    def exec_reg():
        data = request.get_json()

        # Validate user input
        try:
            name = data["name"]
            email = data["email"]
            phone_number = data["phone_number"]
            address = data["address"]
            password = data["password"]

            # Validate email format
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_regex, data["email"]):
                return jsonify({"error": "Invalid email format"}), 400

            # Validate password strength
            password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
            if not re.match(password_regex, data["password"]):
                return jsonify({"error": "Password must be at least 8 characters, contain 1 uppercase, 1 number, and 1 special character (@$!%*?&)"}), 400

            # Validate name length (alphabetic characters only)
            if len(data["name"]) < 4 or not data["name"].isalpha():
                return jsonify({"error": "Name must be at least 4 alphabetic characters"}), 400
            
            if len(data["address"]) < 10:
                return jsonify({"error": "Address must be at least 10 characters"}), 400
            
            # Validate phone is numeric only
            if not data["phone_number"].isdigit():
                return jsonify({"error": "Phone must be number only"}), 400

        except KeyError as e:
            return jsonify({"error": "Missing required field: " + str(e)}), 400

        # Hash password with bcrypt
        hashed_password = generate_password_hash(password)
        
        # Store user information securely in your database
        # Store user data securely in MySQL
        new_user = User(name=name, email=email, phone_number=phone_number, address=address, password=hashed_password)
        try:
            db_session.add(new_user)
            db_session.commit()
            db_session.close()
            return jsonify({"message": "User registered successfully"}), 201
        except Exception as e:  # Catch any database-related errors
            #return jsonify({"error": str(e)}), 500  # Return a generic error message
            #!for security reason, we should not showing error like above and change into something like this:
            return jsonify({"error": "Email already registered"}), 400
    return(exec_reg())


@Users_blueprint.route("/login", methods=["POST"])
def login():
    limiter=current_app.config['limiter']
    db_session=current_app.config['db_session']
    logger=current_app.config['logger']
    @limiter.limit("1 per minute")  # Additional rate limiting for this endpoint
    def exec_login():
        try:
            eml = request.json.get("email")
            password = request.json.get("password")
            
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_regex, eml):
                return jsonify({"error": "Invalid email format"}), 400
        except KeyError as e:
            return jsonify({"error": "Missing required field: " + str(e)}), 400
        
        try:
            with db_session as sesi:
                user = sesi.query(User).filter_by(email=eml).first()
            if user:
                hashed_password = (user.password)  # Access the hashed password (already in bytes)
                password = password
                
                if check_password_hash(hashed_password, password):  # No need to encode password
                    if (user.is_active==False):
                        return jsonify({"message": "User Inactive! Please contact Administrator for further process."}), 401
                    login_user(user)
                    session['user_id'] = user.id  # Store user ID in session
                    # Create and save a session token for authentication manually
                    #session_token = generate_session_token()  # Replace with your token generation logic
                    #db_session.query(User).filter_by(email=email).update({"session_token": session_token})
                    #db_session.commit()

                    return jsonify({"message": "User login successfully"}), 200
            else:
                return jsonify({"error": "Invalid credentials"}), 401
        except Exception as e:
            logger.error(f"Database error during login: {e}")  # Log the error for debugging
            return jsonify({"error": "Internal server error"}), 500
    return(exec_login())

@Users_blueprint.route("/profile", methods=['GET', 'POST'])
@login_required  # Ensures only logged-in users can access this route
def get_user_profile():
    limiter=current_app.config['limiter']
    @limiter.limit("1 per minute")  # Additional rate limiting for this endpoint
    def show_profile():
        # Get the user object from the current session
        profile_data = {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "address":current_user.address,
            "phone number":current_user.phone_number
        }
    # Return the profile data as JSON
        return jsonify(profile_data)
    return(show_profile())

@Users_blueprint.route("/editprofile", methods=['POST']) # edit only: name, address, phone_number and NEED correct password for confirmation
@login_required  # Ensures only logged-in users can access this route
def edit_user_profile():
    limiter=current_app.config['limiter']
    db_session=current_app.config['db_session']
    logger=current_app.config['logger']
    @limiter.limit("2 per minute")  # Additional rate limiting for this endpoint
    def edit_profile():
    # Get the user object from the current session
        data = request.get_json()

        # Validate user input
        try:
            name = data.get("name",current_user.name)
            phone_number = data.get("phone_number",current_user.phone_number)
            address = data.get("address",current_user.address)
            password = data["password"]

            if len(name) < 4 or not name.isalpha():
                return jsonify({"error": "Name must be at least 4 alphabetic characters"}), 400
            if len(address) < 10:
                return jsonify({"error": "Address must be at least 10 characters"}), 400
            if not phone_number.isdigit():
                return jsonify({"error": "Phone must be number only"}), 400            
            if check_password_hash(current_user.password, password)==False:
                return jsonify({"error": "Please re-type your password"}), 400
        except KeyError as e:
            return jsonify({"error": "Missing required field: " + str(e)}), 400
        
        current_user.name = name
        current_user.phone_number = phone_number
        current_user.address = address
        
        try:
            with db_session as sesi:
                    sesi.add(current_user)  # Add to session for update
                    sesi.commit()  # Commit changes to database
                    sesi.close()
            return jsonify("Profile Updated!"),200
        except Exception as e:
            logger.error(f"Database error during process: {e}")  # Log the error for debugging
            return jsonify({"error": "Internal server error"}), 500
    return(edit_profile())


@Users_blueprint.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    session.clear()  # Clear all session data
    return jsonify({"message": "Logout successful"}), 200
