from flask import Flask
from flask_cors import CORS
from models import db, MaintenanceRecord, Car, Admin
from routes import car_routes
from flask_jwt_extended import JWTManager
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz

def send_maintenance_emails(app, mail):
    """
    Fonction pour envoyer des emails automatiques basés sur les maintenances du jour
    """
    with app.app_context():
        try:
            # Récupérer la date actuelle
            today = datetime.now().date()
            one_month_later = today + timedelta(days=30)
            # Récupérer uniquement les enregistrements de maintenance du jour
            maintenance_records = MaintenanceRecord.query.filter(
                MaintenanceRecord.next_due_date == one_month_later
            ).all()
            
            # Récupérer tous les emails d'admin
            admin_emails = [admin.email for admin in Admin.query.all()]
            
            # Si aucun enregistrement de maintenance pour aujourd'hui, ne rien faire
            if not maintenance_records:
                print("Aucune maintenance prévue pour aujourd'hui.")
                return
            
            # Préparer le contenu de l'email
            maintenance_details = []
            for record in maintenance_records:
                # Récupérer les informations de la voiture
                car = Car.query.get(record.car_id)
                maintenance_details.append(
                    f"Voiture {car.brand} {car.model} (Immatriculation: {car.plate_number})\n"
                    f"Type de maintenance: {record.type}\n"
                    f"Date prévue: {record.next_due_date}\n"
                    f"Statut: {record.status}\n"
                )
            
            # Créer le message
            msg = Message(
                subject=f'Maintenances du Jour - {today.strftime("%d/%m/%Y")}',
                recipients=admin_emails,
                body=f"""
                Bonjour,
                
                Voici les maintenances prévues pour aujourd'hui :
                
                {"".join(maintenance_details)}
                
                Merci de prendre les actions nécessaires.
                
                Cordialement,
                Votre Système de Gestion de Maintenance
                """
            )
            
            # Envoi de l'email
            mail.send(msg)
            print(f"Email de maintenance envoyé avec succès le {datetime.now()}")
        
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email de maintenance: {str(e)}")

def init_scheduler(app):
    scheduler = BackgroundScheduler()
    mail = Mail(app)
    
    # Configurer le job pour s'exécuter tous les jours à 8h00 du matin
    scheduler.add_job(
        func=send_maintenance_emails,
        trigger='cron',
        hour=14,
        minute=47,
        args=[app, mail]
    )
    
    scheduler.start()
    return scheduler

def create_app():
    app = Flask(__name__)
    app.config['JWT_SECRET_KEY'] = 'votre-clé-secrète'  # Changez ceci en production
    jwt = JWTManager(app)

    # Configuration de l'email
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'ggsm7383@gmail.com'
    app.config['MAIL_PASSWORD'] = 'yhzu akkk ztjz xbnl'
    app.config['MAIL_DEFAULT_SENDER'] = 'ggsm7383@gmail.com'
    
    CORS(app)
    app.config.from_object('config.Config')
    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Initialiser Mail
    mail = Mail(app)
    
    # Enregistrer les routes
    app.register_blueprint(car_routes, url_prefix='/api')

    # Initialiser le scheduler
    scheduler = init_scheduler(app)
    
    # Stocker le scheduler dans l'app pour pouvoir l'arrêter si nécessaire
    app.scheduler = scheduler
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)