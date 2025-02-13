from flask import Blueprint, request, jsonify
from models import db, Car, MaintenanceRecord, Admin
from services.maintenance_service import MaintenanceService
from datetime import datetime  # Ajoutez cette ligne en haut du fichier
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import os
from redis import Redis
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
car_routes = Blueprint('car_routes', __name__)
BLOCKLIST = set()
@car_routes.route('/cars', methods=['POST'])
def add_car():
    data = request.json

    # Vérifier si une voiture avec le même plate_number existe déjà
    existing_car = Car.query.filter_by(plate_number=data['plate_number']).first()
    if existing_car:
        return jsonify({'message': 'Car with this plate number already exists'}), 400

    new_car = Car(
        plate_number=data['plate_number'],
        brand=data['brand'],
        model=data['model'],
        year=data['year'],
        mileage=data.get('mileage', 0)
    )
    db.session.add(new_car)
    db.session.commit()

    return jsonify({'message': 'Car added successfully', 'car_id': new_car.id}), 201


@car_routes.route('/cars/<int:car_id>', methods=['PUT'])
def update_car(car_id):
    data = request.json
    car = Car.query.get(car_id)

    if not car:
        return jsonify({'message': 'Car not found'}), 404

    car.plate_number = data.get('plate_number', car.plate_number)
    car.brand = data.get('brand', car.brand)
    car.model = data.get('model', car.model)
    car.year = data.get('year', car.year)
    car.mileage = data.get('mileage', car.mileage)

    db.session.commit()
    return jsonify({'message': 'Car updated successfully'}), 200

@car_routes.route('/cars/<int:car_id>', methods=['DELETE'])
def delete_car(car_id):
    try:
        car = Car.query.get(car_id)
        
        if not car:
            return jsonify({'message': 'Car not found'}), 404
            
        db.session.delete(car)
        db.session.commit()
        return jsonify({'message': 'Car deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting car: {str(e)}'}), 500

@car_routes.route('/maintenance', methods=['POST'])
def create_maintenance():
    data = request.json
    try:
        maintenance = MaintenanceService.create_maintenance_record(
            car_id=data['car_id'],
            maintenance_type=data['type'],
            last_done_date=datetime.strptime(
                data.get('last_done_date', datetime.now().strftime("%Y-%m-%d")),
                "%Y-%m-%d"
            )
        )
        return jsonify({'message': 'Maintenance record created', 'maintenance_id': maintenance.id}), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@car_routes.route('/maintenance/upcoming', methods=['GET'])
def get_upcoming_maintenances():
    # Appeler la méthode existante get_upcoming_maintenances() avec 30 jours par défaut
    upcoming_maintenances = MaintenanceService.get_upcoming_maintenances(days_ahead=30)
    return jsonify(upcoming_maintenances), 200

@car_routes.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    admin = Admin.query.filter_by(email=email).first()

    if admin and admin.password == password:
        access_token = create_access_token(identity=str(admin.id))

        return jsonify({
            'message': 'Login successful',
            'token': access_token,
            'admin_id': admin.id,
            'role': admin.role
        }), 200
    else:
        return jsonify({'message': 'Invalid email or password'}), 401

@car_routes.route('/get-cars', methods=['GET'])
def get_all_cars():
    """
    Récupérer toutes les voitures existantes dans la base de données
    """
    cars = MaintenanceService.get_all_cars()
    return jsonify(cars), 200

@car_routes.route('/maintenance/<int:maintenance_id>', methods=['PUT'])
def update_maintenance(maintenance_id):
    """
    Mettre à jour un enregistrement de maintenance.

    Args:
        maintenance_id (int): L'ID de l'enregistrement de maintenance.

    JSON Body (optionnel):
        {
            "maintenance_date": "2024-11-09"  # Format YYYY-MM-DD
        }

    Returns:
        JSON: Détails de l'enregistrement de maintenance mis à jour.
    """
    data = request.get_json()

    # Extraire la date de maintenance si elle est fournie
    maintenance_date = data.get('maintenance_date') if data else None
    if maintenance_date:
        try:
            maintenance_date = datetime.strptime(maintenance_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    try:
        record = MaintenanceService.update_maintenance_record(
            maintenance_id=maintenance_id,
            maintenance_date=maintenance_date
        )
        return jsonify({
            "id": record.id,
            "type": record.type,
            "last_done_date": record.last_done_date.isoformat(),
            "next_due_date": record.next_due_date.isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route pour supprimer un enregistrement de maintenance
@car_routes.route('/maintenance/<int:maintenance_id>', methods=['DELETE'])
def delete_maintenance(maintenance_id):
    """
    Supprimer un enregistrement de maintenance.

    Args:
        maintenance_id (int): L'ID de l'enregistrement de maintenance.

    Returns:
        JSON: Message de succès ou d'échec.
    """
    try:
        success = MaintenanceService.delete_maintenance_record(maintenance_id)
        if success:
            return jsonify({"message": "Maintenance record deleted successfully."}), 200
        else:
            return jsonify({"error": "Failed to delete maintenance record."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@car_routes.route('/maintenance/all', methods=['GET'])
def get_all_maintenances():
    try:
        all_maintenances = MaintenanceService.get_all_maintenances()
        return jsonify(all_maintenances), 200
    except Exception as e:
        return jsonify({'error': 'Erreur lors de la récupération des maintenances'}), 500


@car_routes.route('/maintenance/notifications', methods=['GET'])
def send_maintenance_notifications():
    try:
        upcoming = MaintenanceService.get_upcoming_maintenances()
        one_month = datetime.now() + timedelta(days=30)
        
        for maintenance in upcoming:
            if maintenance.next_due_date <= one_month:
                msg = Message(
                    'Maintenance Reminder',
                    sender=app.config['MAIL_USERNAME'],
                    recipients=['ggsm7383@gmail.com']
                )
                msg.body = f"""
                Maintenance Reminder:
                Vehicle: {maintenance.car.plate_number}
                Type: {maintenance.type}
                Due Date: {maintenance.next_due_date}
                """
                mail.send(msg)
                
        return jsonify({"message": "Notifications sent successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@car_routes.route('/maintenance/completed', methods=['GET'])
def get_completed_maintenances():
    """
    Récupérer les maintenances complétées.
    Peut optionnellement filtrer par ID de voiture.
    """
    car_id = request.args.get('car_id', type=int)
    
    try:
        completed_maintenances = MaintenanceService.get_completed_maintenances(car_id)
        return jsonify(completed_maintenances), 200
    except Exception as e:
        print("Erreur Backend:", str(e))  # Ajoute cette ligne pour voir l'erreur exacte
        return jsonify({'error': 'Erreur lors de la récupération des maintenances complétées'}), 500

@car_routes.route('/reports/overdue', methods=['GET'])
def get_overdue_maintenances():
    try:
        overdue = MaintenanceService.get_overdue_maintenances()
        return jsonify(overdue), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@car_routes.route('/reports/monthly-summary', methods=['GET'])
def get_monthly_summary():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    if not year or not month:
        return jsonify({'error': 'Les paramètres year et month sont requis'}), 400
    
    try:
        summary = MaintenanceService.get_monthly_summary(year, month)
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@car_routes.route('/reports/brand-stats', methods=['GET'])
def get_brand_stats():
    try:
        stats = MaintenanceService.get_brand_maintenance_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@car_routes.route('/reports/status-distribution', methods=['GET'])
def get_status_distribution():
    try:
        distribution = MaintenanceService.get_maintenance_status_distribution()
        return jsonify(distribution), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


redis_client = Redis(host='localhost', port=6379, db=0)
auth_service = MaintenanceService.initialize(redis_client).get_instance()

@car_routes.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    try:
        jti = get_jwt()['jti']
        print(f"Tentative de déconnexion - JTI du token: {jti}")
        
        # Ajouter le token à la liste noire
        BLOCKLIST.add(jti)
        print(f"Token ajouté à la liste noire avec succès")
        print(f"État actuel de la BLOCKLIST: {BLOCKLIST}")
        
        return jsonify(message="Successfully logged out"), 200
        
    except Exception as e:
        print(f"Erreur lors de la déconnexion: {str(e)}")
        return jsonify(message="Logout failed"), 500
