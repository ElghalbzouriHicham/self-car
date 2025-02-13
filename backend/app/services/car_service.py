import schedule
import time
from datetime import datetime, timedelta
from models import db, Car, MaintenanceRecord

class MaintenanceService:
    @staticmethod
    def create_maintenance_record(car_id, maintenance_type, interval_months):
        """Créer un enregistrement de maintenance pour une voiture"""
        today = datetime.now().date()
        next_due_date = today + timedelta(days=interval_months * 30)
        
        record = MaintenanceRecord(
            car_id=car_id,
            type=maintenance_type,
            last_done_date=today,
            next_due_date=next_due_date
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def get_upcoming_maintenances(days_ahead=30):
        """Récupérer les maintenances à venir dans les X prochains jours"""
        today = datetime.now().date()
        upcoming_date = today + timedelta(days=days_ahead)
        
        return MaintenanceRecord.query.filter(
            MaintenanceRecord.next_due_date.between(today, upcoming_date)
        ).all()

    @staticmethod
    def send_maintenance_notifications():
        """Envoyer des notifications pour les maintenances à venir"""
        upcoming_maintenances = MaintenanceService.get_upcoming_maintenances()
        
        notifications = []
        for maintenance in upcoming_maintenances:
            car = maintenance.car
            notification = {
                'car_id': car.id,
                'plate_number': car.plate_number,
                'maintenance_type': maintenance.type,
                'due_date': maintenance.next_due_date
            }
            notifications.append(notification)
        
        return notifications