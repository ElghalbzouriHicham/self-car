# backend/services/maintenance_service.py
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, Car, MaintenanceRecord
from typing import List, Dict, Optional
from flask_jwt_extended import get_jti, get_jwt

class MaintenanceService:
    MAINTENANCE_INTERVALS = {
        'oil_change': 6,        # tous les 6 mois
        'technical_inspection': 12,  # tous les 12 mois
        'insurance': 12          # renouvellement annuel
    }

    @classmethod
    def create_maintenance_record(
        cls, 
        car_id: int, 
        maintenance_type: str, 
        last_done_date: Optional[datetime] = None
    ) -> MaintenanceRecord:
        """
        Créer un enregistrement de maintenance pour une voiture
        
        Args:
            car_id (int): Identifiant de la voiture
            maintenance_type (str): Type de maintenance
            last_done_date (datetime, optional): Date de dernière maintenance
        
        Returns:
            MaintenanceRecord: Nouvel enregistrement de maintenance
        """
         # Vérifier que le type de maintenance est valide
        if maintenance_type not in cls.MAINTENANCE_INTERVALS:
            raise ValueError(f"Type de maintenance invalide: {maintenance_type}")

        # Vérifier s'il existe déjà une maintenance valide
        today = datetime.now().date()
        existing_record = MaintenanceRecord.query.filter(
            MaintenanceRecord.car_id == car_id,
            MaintenanceRecord.type == maintenance_type,
            MaintenanceRecord.next_due_date >= today
        ).first()

        if existing_record:
            raise ValueError(f"Une maintenance de type '{maintenance_type}' existe déjà pour cette voiture (valide jusqu'au {existing_record.next_due_date})")

        
        # Utiliser la date actuelle si aucune date n'est fournie
        today = last_done_date or datetime.now().date()
        
        # Calculer l'intervalle de maintenance
        interval_months = cls.MAINTENANCE_INTERVALS[maintenance_type]
        next_due_date = today + timedelta(days=interval_months * 30)
        
        # Créer l'enregistrement de maintenance
        record = MaintenanceRecord(
            car_id=car_id,
            type=maintenance_type,
            last_done_date=today,
            next_due_date=next_due_date
        )
        
        try:
            db.session.add(record)
            db.session.commit()
            return record
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def get_maintenance_history(cls, car_id: int) -> List[MaintenanceRecord]:
        """
        Récupérer l'historique complet des maintenances pour une voiture
        
        Args:
            car_id (int): Identifiant de la voiture
        
        Returns:
            List[MaintenanceRecord]: Liste des enregistrements de maintenance
        """
        return MaintenanceRecord.query.filter_by(car_id=car_id).order_by(
            MaintenanceRecord.next_due_date.desc()
        ).all()

    @classmethod
    def get_upcoming_maintenances(cls, days_ahead: int = 30) -> List[Dict]:
        """
        Récupérer les maintenances à venir dans les prochains jours
        
        Args:
            days_ahead (int): Nombre de jours à l'avance pour chercher les maintenances
        
        Returns:
            List[Dict]: Liste des maintenances à venir avec détails
        """
        today = datetime.now().date()
        upcoming_date = today + timedelta(days=days_ahead)
        
        upcoming_maintenances = db.session.query(
            MaintenanceRecord, Car
        ).join(Car).filter(
            MaintenanceRecord.next_due_date.between(today, upcoming_date)
        ).all()
        
        return [
            {
                'maintenance_id': maintenance.id,
                'car_id': car.id,
                'plate_number': car.plate_number,
                'brand': car.brand,
                'model': car.model,
                'maintenance_type': maintenance.type,
                'last_done_date': maintenance.last_done_date,
                'next_due_date': maintenance.next_due_date
            } 
            for maintenance, car in upcoming_maintenances
        ]

    @classmethod
    def update_maintenance_record(
        cls, 
        maintenance_id: int, 
        maintenance_date: Optional[datetime] = None
    ) -> MaintenanceRecord:
        """
        Mettre à jour un enregistrement de maintenance
        
        Args:
            maintenance_id (int): ID de la maintenance
            maintenance_date (datetime, optional): Date de maintenance
        
        Returns:
            MaintenanceRecord: Enregistrement de maintenance mis à jour
        """
        record = MaintenanceRecord.query.get_or_404(maintenance_id)
        
        # Utiliser la date actuelle si aucune date n'est fournie
        current_date = maintenance_date or datetime.now().date()
        
        # Récupérer l'intervalle pour ce type de maintenance
        interval_months = cls.MAINTENANCE_INTERVALS[record.type]
        
        # Mettre à jour les dates
        record.last_done_date = current_date
        record.next_due_date = current_date + timedelta(days=interval_months * 30)
        
        try:
            db.session.commit()
            return record
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def delete_maintenance_record(cls, maintenance_id: int) -> bool:
        """
        Supprimer un enregistrement de maintenance
        
        Args:
            maintenance_id (int): ID de la maintenance à supprimer
        
        Returns:
            bool: True si suppression réussie, False sinon
        """
        record = MaintenanceRecord.query.get_or_404(maintenance_id)
        
        try:
            db.session.delete(record)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    @classmethod
    def get_maintenance_stats(cls) -> Dict:
        """
        Générer des statistiques sur les maintenances
        
        Returns:
            Dict: Statistiques détaillées des maintenances
        """
        # Nombre total de maintenances par type
        maintenance_counts = db.session.query(
            MaintenanceRecord.type, 
            func.count(MaintenanceRecord.id)
        ).group_by(MaintenanceRecord.type).all()
        
        # Maintenances en retard
        today = datetime.now().date()
        overdue_maintenances = db.session.query(
            func.count(MaintenanceRecord.id)
        ).filter(
            MaintenanceRecord.next_due_date < today
        ).scalar()
        
        return {
            'maintenance_types_count': dict(maintenance_counts),
            'overdue_maintenances': overdue_maintenances
        }
    @classmethod
    def get_all_cars(cls) -> List[Dict]:
        """
        Récupérer toutes les voitures existantes dans la base de données
        
        Returns:
            List[Dict]: Liste des voitures avec leurs détails
        """
        cars = Car.query.all()
        
        return [
            {
                'id': car.id,
                'plate_number': car.plate_number,
                'brand': car.brand,
                'model': car.model,
                'year': car.year,
                'mileage': car.mileage,
                'status': car.status,
                'created_at': car.created_at,
                'updated_at': car.updated_at
            }
            for car in cars
        ]
    @classmethod
    def get_all_maintenances(cls) -> List[Dict]:
        """
        Récupérer tous les enregistrements de maintenance de la base de données.

        Returns:
            List[Dict]: Liste des enregistrements de maintenance avec détails
        """
        maintenances = db.session.query(MaintenanceRecord, Car).join(Car).all()

        return [
            {
                'maintenance_id': maintenance.id,
                'car_id': car.id,
                'plate_number': car.plate_number,
                'brand': car.brand,
                'model': car.model,
                'maintenance_type': maintenance.type,
                'last_done_date': maintenance.last_done_date,
                'next_due_date': maintenance.next_due_date
            }
            for maintenance, car in maintenances
        ]

    @classmethod
    def get_completed_maintenances(cls, car_id: Optional[int] = None) -> List[Dict]:
        try:
            today = datetime.today().date()  # Récupérer la date d'aujourd'hui

            query = db.session.query(MaintenanceRecord, Car).join(Car)
            
            if car_id is not None:
                query = query.filter(MaintenanceRecord.car_id == car_id)
            
            # On récupère les maintenances dont la date de traitement est passée ou aujourd'hui
            query = query.filter(MaintenanceRecord.next_due_date < today)

            completed_maintenances = query.all()

            result = [
                {
                    'maintenance_id': maintenance.id,
                    'car_id': car.id,
                    'plate_number': car.plate_number,
                    'brand': car.brand,
                    'model': car.model,
                    'maintenance_type': maintenance.type,
                    'last_done_date': maintenance.last_done_date,
                    'next_due_date': maintenance.next_due_date,
                    'status': maintenance.status
                }
                for maintenance, car in completed_maintenances
            ]
            
            print("Résultat des maintenances complétées par date:", result)  # Debug
            return result
        except Exception as e:
            print("Erreur dans get_completed_maintenances:", str(e))
            return []

    @classmethod
    def get_overdue_maintenances(cls) -> List[Dict]:
        """
        Récupérer toutes les maintenances en retard
        """
        try:
            today = datetime.today().date()
            overdue_maintenances = db.session.query(
                MaintenanceRecord, Car
            ).join(Car).filter(
                MaintenanceRecord.next_due_date < today
            ).all()

            return [
                {
                    'maintenance_id': maintenance.id,
                    'car_id': car.id,
                    'plate_number': car.plate_number,
                    'brand': car.brand,
                    'model': car.model,
                    'maintenance_type': maintenance.type,
                    'last_done_date': maintenance.last_done_date,
                    'next_due_date': maintenance.next_due_date,
                    'days_overdue': (today - maintenance.next_due_date).days
                }
                for maintenance, car in overdue_maintenances
            ]
        except Exception as e:
            print("Erreur dans get_overdue_maintenances:", str(e))
            return []

    @classmethod
    def get_monthly_summary(cls, year: int, month: int) -> Dict:
        """
        Récupérer un résumé mensuel des maintenances
        """
        start_date = datetime(year, month, 1)
        end_date = start_date + timedelta(days=31)
        
        completed = db.session.query(func.count(MaintenanceRecord.id)).filter(
            MaintenanceRecord.last_done_date.between(start_date, end_date)
        ).scalar()
        
        upcoming = db.session.query(func.count(MaintenanceRecord.id)).filter(
            MaintenanceRecord.next_due_date.between(start_date, end_date)
        ).scalar()
        
        return {
            'month': f"{year}-{month:02d}",
            'completed_maintenances': completed,
            'upcoming_maintenances': upcoming
        }
    @classmethod
    def get_brand_maintenance_stats(cls) -> Dict:
        """
        Statistiques de maintenance par marque de voiture
        """
        stats = db.session.query(
            Car.brand,
            func.count(MaintenanceRecord.id),
            func.avg(func.datediff(MaintenanceRecord.next_due_date, MaintenanceRecord.last_done_date))
        ).join(MaintenanceRecord).group_by(Car.brand).all()

        return {
            brand: {
                'total_maintenances': count,
                'average_cycle_days': round((avg_days or 0), 2)
            }
            for brand, count, avg_days in stats
        }


    @classmethod
    def get_maintenance_status_distribution(cls) -> Dict:
        """
        Statistiques de répartition des statuts de maintenance
        """
        status_counts = db.session.query(
            MaintenanceRecord.status,
            func.count(MaintenanceRecord.id)
        ).group_by(MaintenanceRecord.status).all()
        
        return dict(status_counts)

    _instance = None
    _redis_client = None

    @classmethod
    def initialize(cls, redis_client):
        cls._redis_client = redis_client
        return cls

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance
    @classmethod
    def logout(self, jwt_token):
        """
        Invalider le token JWT en l'ajoutant à la liste noire
        
        Args:
            jwt_token: Le token JWT à invalider
            
        Returns:
            bool: True si la déconnexion est réussie
        """
        try:
            if not self._redis_client:
                raise Exception("Redis client not initialized")

            # Obtenir les informations du token
            token_data = get_jwt()
            jti = token_data["jti"]
            exp = token_data["exp"]
            
            # Stocker le JTI dans Redis avec une expiration
            self._redis_client.set(f'token_blacklist:{jti}', 'true', ex=exp)
            return True
        except Exception as e:
            print(f"Erreur lors de la déconnexion: {str(e)}")
            return False

    