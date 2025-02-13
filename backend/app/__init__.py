from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')  # Charge la configuration depuis config.py

    # Initialisation de SQLAlchemy
    db.init_app(app)

    # Importation des routes
    from .routes.voitures import voitures_bp
    from .routes.maintenances import maintenances_bp
    from .routes.notifications import notifications_bp
    from .routes.admins import admins_bp

    # Enregistrement des Blueprints
    app.register_blueprint(voitures_bp)
    app.register_blueprint(maintenances_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admins_bp)

    return app