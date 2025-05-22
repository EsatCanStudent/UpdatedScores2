from django.core.management.base import BaseCommand
from scores import scheduler
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Zamanlanmış görevleri başlatır (maç güncellemeleri, analiz oluşturma vb.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--generate-analysis',
            action='store_true',
            help='Sadece maç analizi ve önizlemesi oluştur'
        )
        parser.add_argument(
            '--update-matches',
            action='store_true',
            help='Sadece maç verilerini güncelle'
        )
        parser.add_argument(
            '--now',
            action='store_true',
            help='İşlemi hemen gerçekleştir, zamanlanmış görev oluşturma'
        )

    def handle(self, *args, **options):
        if options['now']:
            # Hemen çalıştır
            if options['generate_analysis']:
                self.stdout.write('Maç analizi ve önizlemesi oluşturuluyor...')
                scheduler.generate_match_analysis()
                scheduler.generate_match_previews()
                self.stdout.write(self.style.SUCCESS('Maç analizi ve önizlemesi başarıyla oluşturuldu.'))
            elif options['update_matches']:
                self.stdout.write('Maç verileri güncellenecek...')
                scheduler.update_matches_data()
                scheduler.update_todays_matches()
                self.stdout.write(self.style.SUCCESS('Maç verileri başarıyla güncellendi.'))
            else:
                self.stdout.write('Tüm veriler güncellenecek...')
                scheduler.fetch_sports_data_full()
                scheduler.generate_match_analysis()
                scheduler.generate_match_previews()
                self.stdout.write(self.style.SUCCESS('Tüm veriler başarıyla güncellendi.'))
        else:
            # Zamanlanmış görev olarak çalıştır
            self.stdout.write('Zamanlanmış görevler başlatılıyor...')
            scheduler.start()
            self.stdout.write(self.style.SUCCESS('Zamanlanmış görevler başlatıldı. Sunucu çalıştığı sürece görevler aktif olacak.'))
