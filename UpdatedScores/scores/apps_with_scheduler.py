"""
Django uygulaması hazır olduğunda scheduler'ı aktif ederiz.
"""
from django.apps import AppConfig

class ScoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scores'
    
    def ready(self):
        """
        Django uygulaması başladığında çalıştırılır.
        """
        try:
            # İmport here to avoid AppRegistryNotReady exception
            from scores import scheduler
            
            # Sadece ana process'te çalıştır (Reloader'da çalışmayı engelle)
            import os
            if os.environ.get('RUN_MAIN', None) != 'true':
                scheduler.start()
        except Exception as e:
            print(f"Scheduler başlatılamadı: {e}")
