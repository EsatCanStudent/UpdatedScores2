from django.core.management.base import BaseCommand
from scores.models import League, Team
import requests
import os

class Command(BaseCommand):
    help = "API-FOOTBALL'dan seçili liglerin takımlarını çeker ve kaydeder."

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            help='Takımların çekileceği sezon (örn. 2025)',
        )

    def handle(self, *args, **options):
        api_key = os.getenv("API_FOOTBALL_KEY")
        base_url = os.getenv("API_FOOTBALL_BASE_URL")
        headers = {"x-apisports-key": api_key}
        leagues = League.objects.all()
        total = 0
        
        # Güncel yılı al veya parametreden al
        current_year = options.get('season') or datetime.datetime.now().year
        # Backup sezon olarak bir önceki yılı da hazır tutalım
        backup_season = current_year - 1
        
        self.stdout.write(self.style.WARNING(f"Takımlar {current_year} sezonu için çekilecek (yoksa {backup_season} denenecek)"))
        
        for league in leagues:            # API-FOOTBALL'da lig id'si genellikle 'id' alanında tutulur
            league_id = getattr(league, 'id', None)
            if not league_id:
                continue
                
            url = f"{base_url}/teams?league={league_id}&season={current_year}"
            
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                
                # API yanıt durum kodunu kontrol et
                if resp.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"  API Hatası ({resp.status_code}): {resp.text}"))
                    continue
                
                data = resp.json()
                
                # Veri yoksa önceki sezonu deneyelim
                if not data.get("response") or len(data.get("response", [])) == 0:
                    self.stdout.write(self.style.WARNING(f"  {league.name} için {current_year} sezonunda takım verisi bulunamadı. {backup_season} sezonu deneniyor..."))
                    url = f"{base_url}/teams?league={league_id}&season={backup_season}"
                    resp = requests.get(url, headers=headers, timeout=30)
                    
                    if resp.status_code != 200:
                        self.stdout.write(self.style.ERROR(f"  API Hatası (önceki sezon): {resp.status_code}"))
                        continue
                    
                    data = resp.json()
                    
                    if not data.get("response") or len(data.get("response", [])) == 0:
                        self.stdout.write(self.style.ERROR(f"  {league.name} için hiçbir sezonda takım verisi bulunamadı."))
                        continue
                
                team_count = len(data.get("response", []))
                self.stdout.write(self.style.SUCCESS(f"  {league.name} için {team_count} takım bulundu."))
                
                for team_data in data.get("response", []):
                    team_info = team_data["team"]
                    Team.objects.update_or_create(
                        id=str(team_info["id"]),
                        defaults={
                            "name": team_info["name"],
                            "logo": team_info.get("logo"),
                            "league": league
                        }
                    )
                    total += 1
                    
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"  HTTP isteği hatası: {str(e)}"))
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Beklenmeyen hata: {str(e)}"))
                continue
        self.stdout.write(self.style.SUCCESS(f"{total} takım başarıyla kaydedildi."))
