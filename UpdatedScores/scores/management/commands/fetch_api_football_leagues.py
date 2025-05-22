from django.core.management.base import BaseCommand
from scores.api_client import APIFootballClient
from scores.models import League
import unicodedata

def normalize(text):
    if not text:
        return ''
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower().replace('(', '').replace(')', '').replace('-', ' ').replace('.', '').replace('’', '').replace("'", '').strip()

# Sadece istenen ülke-lig kombinasyonları
POPULAR_LEAGUES = [
    ("England", "Premier League"),
    ("Spain", "La Liga"),
    ("Germany", "Bundesliga"),
    ("Italy", "Serie A"),
    ("France", "Ligue 1"),
    ("Turkey", "Süper Lig"),
    ("World", "Champions League"),        # UEFA Champions League
    ("World", "UEFA Europa League"),
]
# Normalize edilmiş tuple listesi
NORMALIZED_POPULAR_LEAGUES = [(normalize(country), normalize(league)) for country, league in POPULAR_LEAGUES]

class Command(BaseCommand):
    help = 'API-FOOTBALL ile sadece istenen ülke-lig kombinasyonlarını kaydeder (önce tüm ligleri siler).'
    
    def handle(self, *args, **options):
        # Önce tüm ligleri sil
        League.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Sadece seçili ligler eklenecek:'))
        for country, league in POPULAR_LEAGUES:
            self.stdout.write(f'- {league} ({country})')
            
        client = APIFootballClient()
        data = client.get_leagues()
        if not data or 'response' not in data:
            self.stdout.write(self.style.ERROR('API-FOOTBALL ile lig verisi alınamadı!'))
            return
        count = 0
        matched = []
        for league_obj in data['response']:
            league = league_obj.get('league', {})
            country = league_obj.get('country', {})
            league_name = league.get('name', '')
            country_name = country.get('name', '')
            norm_league = normalize(league_name)
            norm_country = normalize(country_name)
            for wanted_country, wanted_league in NORMALIZED_POPULAR_LEAGUES:
                if wanted_league in norm_league and wanted_country in norm_country:
                    League.objects.update_or_create(
                        id=league['id'],
                        defaults={
                            'name': league_name,
                            'country': country_name
                        }
                    )
                    matched.append(f"{league_name} ({country_name})")
                    count += 1
                    break
        self.stdout.write(self.style.SUCCESS(f'{count} popüler lig (ülke-lig eşleşmesiyle) kaydedildi:'))
        for m in matched:
            self.stdout.write(f'- {m}')
