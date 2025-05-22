from apscheduler.schedulers.background import BackgroundScheduler
from django.core import management
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from datetime import timedelta
import os
import sys
import django
import logging

logger = logging.getLogger(__name__)

from .models import Match, Profile

# Circular import prevention
def get_notification_service():
    from .notification_service import NotificationService
    return NotificationService

def check_upcoming_matches():
    """
    Check for matches that will start soon and send notifications to users
    """
    # Find matches starting in the next 15-20 minutes
    now = timezone.now()
    start_window = now + timedelta(minutes=15)
    end_window = now + timedelta(minutes=20)
    
    upcoming_matches = Match.objects.filter(
        match_date__gte=now,
        match_date__lte=end_window
    )
    
    logger.info(f"Found {upcoming_matches.count()} matches starting soon")
    
    notification_service = get_notification_service()
    
    for match in upcoming_matches:
        try:
            notification_service.notify_match_start(match)
            logger.info(f"Sent match start notifications for {match}")
        except Exception as e:
            logger.error(f"Failed to send match start notification for {match}: {e}")

def start():
    """
    Zamanlanmış görevleri başlat
    """
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Maç verilerini güncelleme aralığını belirle
    update_interval = int(os.environ.get('UPDATE_INTERVAL', 3600))  # Varsayılan 1 saat
    
    # Sadece maç verileri için güncel bilgileri çek (sık aralıklarla)
    scheduler.add_job(
        update_matches_data,
        trigger=IntervalTrigger(seconds=update_interval),
        id="update_matches_data",
        max_instances=1,
        replace_existing=True,
    )
    logger.info(f"Maç verileri her {update_interval//60} dakikada bir güncellenecek.")
    
    # Bugünkü maçlar sabah erken saatte ve öğleden sonra güncellenecek
    scheduler.add_job(
        update_todays_matches,
        trigger='cron',
        hour='7,12,16,20',  # Günde 4 kez güncelleme
        id="update_todays_matches",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Bugünkü maçlar günde 4 kez (saat 7, 12, 16, 20) güncellenecek.")
      # Günlük tam güncelleme (gece 03:00'da)
    scheduler.add_job(
        fetch_sports_data_full,
        trigger='cron',
        hour=3,
        minute=0,
        id="fetch_sports_data_full",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Tam veri güncellemesi her gün 03:00'da yapılacak.")
      # Maç önizlemesi oluşturma (her gün sabah 08:00'da)
    scheduler.add_job(
        generate_match_previews,
        trigger='cron',
        hour=8,
        minute=0,
        id="generate_match_previews",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Maç önizlemeleri her gün 08:00'da oluşturulacak.")
      # Her 5 dakikada bir yaklaşan maçları kontrol et ve bildirim gönder
    scheduler.add_job(
        check_upcoming_matches,
        trigger=IntervalTrigger(minutes=5),
        id="check_upcoming_matches",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Yaklaşan maçlar her 5 dakikada bir kontrol edilecek.")
    
    # Maç analizi oluşturma (her 6 saatte bir)
    scheduler.add_job(
        generate_match_analysis,
        trigger=IntervalTrigger(hours=6),
        id="generate_match_analysis",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Maç analizleri her 6 saatte bir güncellenecek.")
    
    # ===== API-FOOTBALL SCHEDULER JOBS =====
    
    # Maç kadrolarını güncelleme (her 15 dakikada bir)
    scheduler.add_job(
        update_match_lineups,
        trigger=IntervalTrigger(minutes=15),
        id="update_match_lineups",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Maç kadroları her 15 dakikada bir güncellenecek.")
    
    # Maç olaylarını güncelleme (her 1 dakikada bir - canlı maçlar için)
    scheduler.add_job(
        update_match_events,
        trigger=IntervalTrigger(minutes=1),
        id="update_match_events",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Maç olayları her 1 dakikada bir güncellenecek.")
    
    # Maç istatistiklerini güncelleme (her 30 dakikada bir)
    scheduler.add_job(
        update_match_statistics,
        trigger=IntervalTrigger(minutes=30),
        id="update_match_statistics",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Maç istatistikleri her 30 dakikada bir güncellenecek.")
    
    # Maç önizlemelerini güncelleme (günde iki kez)
    scheduler.add_job(
        update_match_previews,
        trigger=CronTrigger(hour='8,20'),
        id="update_match_previews",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Maç önizlemeleri günde iki kez (08:00 ve 20:00) güncellenecek.")
    
    # Canlı maç olaylarını düzenli olarak kontrol et
    scheduler.add_job(
        monitor_live_events,
        trigger=IntervalTrigger(minutes=3),
        id="monitor_live_events",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Canlı maç olayları her 3 dakikada bir kontrol edilecek.")
    
    scheduler.start()
    logger.info("Scheduler started!")

def update_matches_data():
    """
    Sadece maç verilerini günceller - canlı skorlar için
    """
    try:
        logger.info("Maç verileri güncelleniyor...")
        management.call_command('fetch_api_football_matches')
        logger.info("Maç verileri başarıyla güncellendi")
    except Exception as e:
        logger.error(f"Maç verilerini güncellerken hata oluştu: {e}")

def update_todays_matches():
    """
    Bugünkü maçları günceller - daha sık güncelleme için
    """
    try:
        logger.info("Bugünkü maçlar güncelleniyor...")
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        management.call_command('fetch_api_football_matches', date=today)
        logger.info("Bugünkü maçlar başarıyla güncellendi")
    except Exception as e:
        logger.error(f"Bugünkü maçları güncellerken hata oluştu: {e}")
        
# ===== API-FOOTBALL TASKS =====

def update_match_lineups():
    """
    API-FOOTBALL'dan maç kadrolarını günceller
    """
    try:
        logger.info("Maç kadroları güncelleniyor...")
        management.call_command('fetch_match_lineups', days=1)
        logger.info("Maç kadroları başarıyla güncellendi")
    except Exception as e:
        logger.error(f"Maç kadrolarını güncellerken hata oluştu: {e}")

def update_match_events():
    """
    API-FOOTBALL'dan maç olaylarını günceller
    """
    try:
        logger.info("Maç olayları güncelleniyor...")
        management.call_command('fetch_match_events', days=1)
        logger.info("Maç olayları başarıyla güncellendi")
    except Exception as e:
        logger.error(f"Maç olaylarını güncellerken hata oluştu: {e}")

def update_match_statistics():
    """
    API-FOOTBALL'dan maç istatistiklerini günceller
    """
    try:
        logger.info("Maç istatistikleri güncelleniyor...")
        management.call_command('fetch_match_statistics', days=1)
        logger.info("Maç istatistikleri başarıyla güncellendi")
    except Exception as e:
        logger.error(f"Maç istatistiklerini güncellerken hata oluştu: {e}")

def update_match_previews():
    """
    API-FOOTBALL'dan maç önizlemelerini günceller
    """
    try:
        logger.info("Maç önizlemeleri güncelleniyor...")
        management.call_command('fetch_match_previews', days=3)
        logger.info("Maç önizlemeleri başarıyla güncellendi")
    except Exception as e:
        logger.error(f"Maç önizlemelerini güncellerken hata oluştu: {e}")

def monitor_live_events():
    """
    Canlı maç olaylarını takip et ve bildirim gönder
    """
    try:
        logger.info("Canlı maç olayları takip ediliyor...")
        # Run the monitor command briefly to check for updates
        management.call_command('monitor_live_events', interval=10, log_level='INFO')
        logger.info("Canlı maç olayları kontrolü tamamlandı")
    except Exception as e:
        logger.error(f"Canlı maç olaylarını takip ederken hata oluştu: {e}")

def fetch_sports_data():
    """
    Spor verilerini güncelle
    """
    try:
        logger.info("Tüm maç verileri güncelleniyor...")
        management.call_command('fetch_sports_data')
        logger.info("Tüm maç verileri güncellendi")
    except Exception as e:
        logger.error(f"Veri güncellerken hata oluştu: {e}")

def fetch_sports_data_full():
    """
    Tüm spor verilerini güncelle (lig, takım dahil)
    """
    try:
        logger.info("Tam veri güncellemesi yapılıyor...")
        management.call_command('fetch_sports_data', full=True)
        logger.info("Tam veri güncellemesi tamamlandı")
    except Exception as e:
        logger.error(f"Tam veri güncellemesinde hata oluştu: {e}")
        
def generate_match_previews():
    """
    Bugün ve gelecekteki maçlar için önizleme oluştur
    """
    try:
        logger.info("Maç önizlemeleri oluşturuluyor...")
        management.call_command('generate_match_analysis', preview=True)
        logger.info("Maç önizlemeleri başarıyla oluşturuldu")
    except Exception as e:
        logger.error(f"Maç önizlemeleri oluşturulurken hata oluştu: {e}")
        
def generate_match_analysis():
    """
    Tamamlanmış maçlar için analizler oluştur
    """
    try:
        logger.info("Maç analizleri oluşturuluyor...")
        management.call_command('generate_match_analysis', analysis=True, days=2)
        logger.info("Maç analizleri başarıyla oluşturuldu")
    except Exception as e:
        logger.error(f"Maç analizleri oluşturulurken hata oluştu: {e}")
        logger.info("Tam veri güncellemesi tamamlandı")
    except Exception as e:
        logger.error(f"Tam veri güncellemesi sırasında hata oluştu: {e}")
        
def generate_match_analysis():
    """Son 3 günlük tamamlanmış maçlar için analiz oluştur"""
    try:
        logger.info("Maç analizleri oluşturuluyor...")
        management.call_command('generate_match_analysis', days=3)
        logger.info("Maç analizleri başarıyla oluşturuldu.")
    except Exception as e:
        logger.error(f"Maç analizleri oluşturulurken hata oluştu: {e}")

def generate_match_previews():
    """Gelecek 3 günlük maçlar için önizleme oluştur"""
    try:
        logger.info("Maç önizlemeleri oluşturuluyor...")
        management.call_command('generate_match_analysis', days=3, preview=True)
        logger.info("Maç önizlemeleri başarıyla oluşturuldu.")
    except Exception as e:
        logger.error(f"Maç önizlemeleri oluşturulurken hata oluştu: {e}")
