import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    NOTIFICATION_DAYS_AHEAD = 30

    # Configuration de la base de données MySQL
    USERNAME = 'root'
    PASSWORD = ''
    HOST = 'localhost'  # Ou l'adresse IP de votre serveur MySQL
    DATABASE = 'car_rental_db'

    # URI de la base de données MySQL
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}/{DATABASE}'



    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    EMAIL_SENDER = os.getenv('EMAIL_SENDER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

        # Configuration de Celery (avec Redis)
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'