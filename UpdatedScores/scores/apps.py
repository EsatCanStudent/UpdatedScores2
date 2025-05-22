from django.apps import AppConfig

class ScoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scores'

    def ready(self):
        """
        Django uygulaması başladığında çalıştırılır.
        Zamanlanmış görevleri başlatmak için scheduler importunu burada yap.
        """
        from . import scheduler
        scheduler.start()
        from . import signals  # signals.py dosyasını burada import et