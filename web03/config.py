import os


class Config:
#NOTE general config
    basedir = os.path.abspath(os.path.dirname(__file__))  # Get the absolute path to the project directory
    log_location=os.path.join(basedir, 'my_app.log')

#NOTE config for DB
    #NOTE for other db:
    #SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://myuser:mypassword@localhost:3306/mydatabase" #MYSQL
    #SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://myuser:mypassword@localhost:5432/mydatabase"  #POSTGRESQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                            'sqlite:///' + os.path.join(basedir, 'my_app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
