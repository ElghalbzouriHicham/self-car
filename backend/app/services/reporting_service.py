from models import Car, MaintenanceRecord
from sqlalchemy import func

class ReportingService:
    @staticmethod
    def get_maintenance_summary():
        """Générer un rapport récapitulatif des maintenances"""
        # Total de voitures
        total_cars = Car.query.count()

        # Répartition par statut
        car_status_counts = db.session.query(
            Car.status, 
            func.count(Car.id)
        ).group_by(Car.status).all()

        # Prochaines maintenances
        upcoming_maintenances = MaintenanceRecord.query.filter(
            MaintenanceRecord.next_due_date <= func.current_date() + 30
        ).all()

        return {
            'total_cars': total_cars,
            'car_status': dict(car_status_counts),
            'upcoming_maintenances': len(upcoming_maintenances)
        }