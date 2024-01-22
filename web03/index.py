import logging
from logging.handlers import \
    RotatingFileHandler  # # NOTE For file-based logging

from config import Config
from flask import Flask
from flask_limiter import Limiter
from flask_login import LoginManager, current_user
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)

#NOTE: db configuration is in config.py
app.config.from_object(Config)
db = SQLAlchemy(app)
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
#----

#NOTE: user session management control
app.config["SECRET_KEY"] = "your_secret_key"  # Replace with a strong secret key
app.config["SESSION_TYPE"] = "sqlalchemy"  # Choose "filesystem" if using cookies, "sqlalchemy" for database
app.config["SESSION_SQLALCHEMY_DB"] = db  # Use your SQLAlchemy session object if storing in database


class UserLimiter(Limiter):
    def __init__(self, app, default_limits):
        super().__init__(app, default_limits)
    def get_rate_limit(self, current_app, request):
        if current_user.is_authenticated:
            return ["200 per day", "120 per hour"]
        else:
            return super().get_rate_limit(current_app, request)

limiter = Limiter(app, default_limits=["200 per day", "60 per hour"])  # NOTE this command to give limit of access per IP addr. Adjust limits as needed

#NOTE set config for Blueprints
app.config['limiter'] = limiter
app.config['db_session'] = Session()
app.config['logger'] = app.logger
#----

#NOTE log file control
app.logger.setLevel(logging.DEBUG)  # Set logging level to DEBUG for more detailed info
handler = RotatingFileHandler(Config.log_location, maxBytes=10485760, backupCount=10)  # Create a rotating file handler
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)  # Add the handler to the app's logger
#----


#NOTE import blueprints and register to main app
from users.controller import Users_blueprint
from users.model import User

#-

app.register_blueprint(Users_blueprint, limiter=limiter)
#----


@login_manager.user_loader
def load_user(user_id):
    """Loads the user object from the database based on the user ID."""
    with Session() as sesi:  # Assuming a database session context manager
        user = sesi.get(User, int(user_id))  # Query for the user
    return user


if __name__ == "__main__":
    app.run(debug=True)  # Set debug=False in production
