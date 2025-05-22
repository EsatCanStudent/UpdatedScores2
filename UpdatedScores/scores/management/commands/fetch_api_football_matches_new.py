from django.core.management.base import BaseCommand
from scores.models import League, Team, Match
import requests
import os
import datetime
from django.utils.dateparse import parse_datetime
from django.db import transaction

class Command(BaseCommand):
    help = "API-FOOTBALL'dan liglerin maclarini ceker ve kaydeder."
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            help='Maçların çekileceği sezon (örn. 2025)',
        )
        parser.add_argument(
            '--last',
            type=int,
            default=14,
            help='Son kaç günlük maçları çekmek istiyorsunuz (varsayılan: 14)',
        )
        parser.add_argument(
            '--next',
            type=int,
            default=14,
            help='Gelecek kaç günlük maçları çekmek istiyorsunuz (varsayılan: 14)',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Belirli bir tarih için maçları çek (YYYY-MM-DD formatında)',
        )
        parser.add_argument(
            '--no-delete',
            action='store_true',
            help='Önceki maç verilerini silmeden ekle/güncelle',
        )

    def handle(self, *args, **options):
        api_key = os.getenv("API_FOOTBALL_KEY")
        base_url = os.getenv("API_FOOTBALL_BASE_URL")
        headers = {"x-apisports-key": api_key}
        leagues = League.objects.all()
        total = 0
        
        # Özel bir tarih belirtilmiş mi kontrol et
        specific_date = options.get('date')
        no_delete = options.get('no_delete', False)
        
        if not no_delete and not specific_date:
            # Mac verilerini silmeden once uyari yapalim
            self.stdout.write(self.style.WARNING("Bu islem tum mac verilerini silecek ve API'den yeniden cekecektir."))
            
            # Mac verilerini siliyoruz cunku guncel veri cekecegiz
            # Transaction icinde yap ki yarim kalirsa sorun olusmasin
            with transaction.atomic():
                Match.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("Eski mac verileri silindi. Yeni veriler cekiliyor..."))
        elif specific_date and not no_delete:
            # Sadece belirtilen tarih için olan maçları sil
            try:
                date_obj = datetime.datetime.strptime(specific_date, '%Y-%m-%d').date()
                count = Match.objects.filter(match_date__date=date_obj).delete()[0]
                self.stdout.write(self.style.SUCCESS(f"{specific_date} tarihindeki {count} maç silindi."))
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Geçersiz tarih formatı: {specific_date}. YYYY-MM-DD formatında olmalı."))
                return
        else:
            self.stdout.write(self.style.WARNING("Mevcut maç verileri silinmeden güncelleme yapılacak."))
        
        # Günümüzün yılını alma ve güncel sezonu belirleme
        current_year = datetime.datetime.now().year
        season = options.get('season', current_year)
        # Backup sezon olarak bir önceki yılı da hazır tutalım
        backup_season = season - 1
        
        self.stdout.write(self.style.WARNING(f"Maçlar {season} sezonu için çekilecek (yoksa {backup_season} denenecek)"))
        # Ilgili ligleri ID'leri ile birlikte yazdir
        self.stdout.write(self.style.WARNING(f"Toplam {leagues.count()} lig icin veri cekiliyor..."))
        
        for idx, league in enumerate(leagues, 1):
            league_id = getattr(league, 'id', None)
            if not league_id:
                continue
                
            self.stdout.write(f"[{idx}/{leagues.count()}] {league.name} ({league.country}) - ID: {league_id}")
            
            # Parametre değerlerini al
            last_days = options.get('last', 14)
            next_days = options.get('next', 14)
            
            if specific_date:
                # Sadece belirtilen tarih için maçları çek
                specific_date_url = f"{base_url}/fixtures?league={league_id}&season={season}&date={specific_date}"
                urls = [(specific_date_url, f"{specific_date} tarihi")]
                self.stdout.write(self.style.WARNING(f"{specific_date} tarihi için maçlar çekilecek"))
            else:
                # Once gecmis maclari cekelim (son iki hafta)
                past_url = f"{base_url}/fixtures?league={league_id}&season={season}&last={last_days}"
                
                # Sonra gelecek maclari cekelim (onumuzdeki iki hafta)
                next_url = f"{base_url}/fixtures?league={league_id}&season={season}&next={next_days}"
                
                # Bugunku maclari cekelim
                today_url = f"{base_url}/fixtures?league={league_id}&season={season}&date={datetime.datetime.now().strftime('%Y-%m-%d')}"
                
                # URL listesi oluştur
                urls = [(past_url, "Gecmis"), (today_url, "Bugun"), (next_url, "Gelecek")]
            
            for url, url_type in urls:
                try:
                    self.stdout.write(f"  Cekiliyor: {league.name} - {url_type} maclari...")
                    try:
                        resp = requests.get(url, headers=headers, timeout=30)
                        
                        # API yanit durum kodunu kontrol et
                        if resp.status_code != 200:
                            self.stdout.write(self.style.ERROR(f"  API Hatasi ({resp.status_code}): {resp.text}"))
                            continue
                            
                        data = resp.json()
                    except requests.exceptions.RequestException as e:
                        self.stdout.write(self.style.ERROR(f"  HTTP istegi hatasi: {str(e)}"))
                        continue
                    
                    # API yanıt içeriğini kontrol et
                    if data.get("errors"):
                        self.stdout.write(self.style.ERROR(f"  API Hata döndürdü: {data.get('errors')}"))
                        continue
                    
                    # API yanıtında "response" alanı yoksa önceki sezonu deneyelim
                    if not data.get("response"):
                        self.stdout.write(self.style.WARNING(f"  {league.name} için {url_type} maçları bulunamadı. Önceki sezonu deniyorum..."))
                        # Önceki sezonu deneyelim
                        backup_url = url.replace(f"season={season}", f"season={backup_season}")
                        resp = requests.get(backup_url, headers=headers)
                        if resp.status_code != 200:
                            self.stdout.write(self.style.ERROR(f"  API Hatası (önceki sezon): {resp.status_code}"))
                            continue
                        data = resp.json()
                        
                        if not data.get("response"):
                            self.stdout.write(self.style.WARNING(f"  {league.name} için {url_type} maçları bulunamadı (önceki sezonda da)."))
                            continue
                    
                    # Gelen maçların sayısını bildirme
                    match_count = len(data.get("response", []))
                    self.stdout.write(f"  {match_count} maç bulundu.")
                    
                    # Maçları işleyelim
                    for match_data in data.get("response", []):
                        try:
                            fixture = match_data.get("fixture", {})
                            teams = match_data.get("teams", {})
                            goals = match_data.get("goals", {})
                            
                            if not fixture or not teams:
                                self.stdout.write(self.style.WARNING("  Eksik veri, bu maç atlanıyor."))
                                continue
                            
                            # Maçın skorunu alalım (eğer maç oynanmışsa)
                            home_score = goals.get("home")
                            away_score = goals.get("away")
                            score = None
                            if home_score is not None and away_score is not None:
                                score = f"{home_score}-{away_score}"
                            
                            # Takımları veritabanından çekelim
                            home_team_id = str(teams.get("home", {}).get("id", ""))
                            away_team_id = str(teams.get("away", {}).get("id", ""))
                            
                            if not home_team_id or not away_team_id:
                                self.stdout.write(self.style.WARNING("  Takım ID'leri eksik, bu maç atlanıyor."))
                                continue
                            
                            home_team = Team.objects.filter(id=home_team_id).first()
                            away_team = Team.objects.filter(id=away_team_id).first()
                            
                            # Takımlar veritabanında yoksa, oluşturalım
                            if not home_team:
                                try:
                                    home_team, created = Team.objects.get_or_create(
                                        id=home_team_id,
                                        defaults={
                                            "name": teams.get("home", {}).get("name", "Bilinmeyen Takım"),
                                            "logo": teams.get("home", {}).get("logo"),
                                            "league": league
                                        }
                                    )
                                    if created:
                                        self.stdout.write(f"    + Yeni ev sahibi takım eklendi: {home_team.name}")
                                except Exception as e:
                                    self.stdout.write(self.style.ERROR(f"    Ev sahibi takım oluşturulurken hata: {str(e)}"))
                                    continue
                            
                            if not away_team:
                                try:
                                    away_team, created = Team.objects.get_or_create(
                                        id=away_team_id,
                                        defaults={
                                            "name": teams.get("away", {}).get("name", "Bilinmeyen Takım"),
                                            "logo": teams.get("away", {}).get("logo"),
                                            "league": league
                                        }
                                    )
                                    if created:
                                        self.stdout.write(f"    + Yeni deplasman takımı eklendi: {away_team.name}")
                                except Exception as e:
                                    self.stdout.write(self.style.ERROR(f"    Deplasman takımı oluşturulurken hata: {str(e)}"))
                                    continue
                                    
                            # Maç verisini kaydetmek için tarih-saat verisi kontrol etmeliyiz
                            match_date_str = fixture.get("date")
                            if not match_date_str:
                                self.stdout.write(self.style.WARNING("    Maç tarihi bulunamadı, bu maç atlanıyor."))
                                continue
                            
                            try:
                                # ISO formatındaki tarih-saat verisini parse et
                                match_date = parse_datetime(match_date_str)
                                
                                if not match_date:
                                    # Alternatif olarak Python'un kendi parser'ını deneyelim
                                    from datetime import datetime as dt
                                    match_date = dt.fromisoformat(match_date_str.replace('Z', '+00:00'))
                                    
                                if not match_date:
                                    self.stdout.write(self.style.WARNING(f"    Maç tarihi ayrıştırılamadı: {match_date_str}"))
                                    continue
                                    
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"    Tarih ayrıştırma hatası: {str(e)} - Tarih: {match_date_str}"))
                                continue
                            
                            # Benzersiz ID'yi oluşturalım
                            match_id = str(fixture.get("id", ""))
                            if not match_id:
                                self.stdout.write(self.style.WARNING("    Maç ID'si bulunamadı, bu maç atlanıyor."))
                                continue
                            
                            # Transaction içinde güvenle kaydedelim
                            with transaction.atomic():
                                match, created = Match.objects.update_or_create(
                                    id=match_id,
                                    defaults={
                                        "home_team": home_team,
                                        "away_team": away_team,
                                        "match_date": match_date,
                                        "league": league,
                                        "stadium": fixture.get("venue", {}).get("name", ""),
                                        "score": score,
                                        "round": match_data.get("league", {}).get("round", ""),
                                        "season": str(match_data.get("league", {}).get("season", "")),
                                        "status": fixture.get("status", {}).get("short", "")
                                    }
                                )
                                
                                if created:
                                    self.stdout.write(f"    + Yeni maç eklendi: {home_team.name} vs {away_team.name} ({match_date.strftime('%Y-%m-%d %H:%M')})")
                                else:
                                    self.stdout.write(f"    * Maç güncellendi: {home_team.name} vs {away_team.name} ({match_date.strftime('%Y-%m-%d %H:%M')})")
                                
                                total += 1
                                
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"    Maç kaydedilirken hata: {str(e)}"))
                            continue
                            
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  API isteği sırasında hata: {str(e)}"))
                    continue
        
        # Bir özetleme yapalım
        try:
            today = datetime.datetime.now().date()
            today_matches = Match.objects.filter(match_date__date=today).count()
            past_matches = Match.objects.filter(match_date__date__lt=today).count()
            future_matches = Match.objects.filter(match_date__date__gt=today).count()
            
            self.stdout.write(self.style.SUCCESS(f"Toplam {total} maç başarıyla kaydedildi."))
            self.stdout.write(self.style.SUCCESS(f"Bugünkü maçlar: {today_matches}"))
            self.stdout.write(self.style.SUCCESS(f"Geçmiş maçlar: {past_matches}"))
            self.stdout.write(self.style.SUCCESS(f"Gelecek maçlar: {future_matches}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Özet oluştururken hata: {str(e)}"))
