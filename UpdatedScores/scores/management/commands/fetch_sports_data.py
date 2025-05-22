import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from scores.api_client import TheSportsDBAPI, fetch_leagues, fetch_events_by_league
from scores.models import League, Team, Player, Match, Event
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'API-FOOTBALL ve TheSportsDB API ile spor verilerini günceller'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Tam bir güncelleme yapar (Ligler, takımlar, maçlar)',
        )
          parser.add_argument(
            '--no-warnings',
            action='store_true',
            help='Uyarıları gösterme',
        )
        
    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f'Veri güncelleme işlemi başladı: {start_time}')
        
        # Komutlarda sessiz mod için verbosity parametresi
        verbosity = 0 if options.get('no_warnings') else 1
        
        if options['full']:
            self.stdout.write(self.style.SUCCESS("API-FOOTBALL tam veri güncelleme başlatılıyor..."))
            try:
                from django.core.management import call_command
                
                # 1. Ligleri çek - Belirtilen 8 lig için
                self.stdout.write(self.style.SUCCESS("1/3: Ligleri çekiyorum..."))
                call_command('fetch_api_football_leagues', verbosity=verbosity)
                
                # 2. Takımları çek - Her lig için takımları
                self.stdout.write(self.style.SUCCESS("2/3: Takımları çekiyorum..."))
                call_command('fetch_api_football_teams', verbosity=verbosity)
                
                # 3. Maçları çek - Son 14 gün ve gelecek 14 gün
                self.stdout.write(self.style.SUCCESS("3/3: Maçları çekiyorum..."))
                call_command('fetch_api_football_matches', verbosity=verbosity)
                
                # Başarı mesajı
                self.stdout.write(self.style.SUCCESS("✓ Tüm veriler başarıyla güncellendi!"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"API-FOOTBALL veri güncelleme sırasında hata: {str(e)}"))
                
                # İstenirse eski yöntemi deneyebiliriz TheSportsDB ile
                if input("TheSportsDB API ile devam etmek istiyor musunuz? (e/h): ").lower() == 'e':
                    api = TheSportsDBAPI()
                    self.update_leagues(api)
                    self.update_teams(api)
                    self.update_players(api)
                    self.update_matches(api)
        else:
            # Sadece maç verilerini güncelle
            try:
                from django.core.management import call_command
                self.stdout.write(self.style.SUCCESS("API-FOOTBALL ile maç verilerini güncelliyorum..."))
                call_command('fetch_api_football_matches', verbosity=verbosity)
                self.stdout.write(self.style.SUCCESS("✓ Maç verileri başarıyla güncellendi!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"API-FOOTBALL maç verisi çekilirken hata: {str(e)}"))
        
        end_time = timezone.now()
        duration = end_time - start_time
        self.stdout.write(self.style.SUCCESS(f'Veri güncelleme tamamlandı. Süre: {duration}'))

    @transaction.atomic
    def update_leagues(self, api):
        """API'den lig verilerini çeker ve veritabanını günceller"""
        self.stdout.write('Lig verilerini güncelleme...')
        leagues_data = api.get_leagues()
        # Tüm futbol liglerini ekle (filtreleme yok)
        counter = 0
        for league_data in leagues_data:
            league_id = league_data.get('idLeague')
            league_name = league_data.get('strLeague')
            league_country = league_data.get('strCountry')
            
            if not all([league_id, league_name, league_country]):
                continue
                
            league, created = League.objects.update_or_create(
                id=league_id,
                defaults={
                    'name': league_name,
                    'country': league_country
                }
            )
            
            if created:
                counter += 1
                self.stdout.write(f'  + Yeni lig eklendi: {league_name}')
        
        self.stdout.write(self.style.SUCCESS(f'  {counter} yeni lig eklendi, toplam {len(leagues_data)} lig güncellendi.'))

    @transaction.atomic
    def update_teams(self, api):
        """API'den takım verilerini çeker ve veritabanını günceller"""
        self.stdout.write('Takım verilerini güncelleme...')
        leagues = League.objects.all()
        
        counter = 0
        for league in leagues:
            self.stdout.write(f'  {league.name} için takımlar getiriliyor...')
            teams_data = api.get_teams_by_league(league.id)
            
            for team_data in teams_data:
                team_id = team_data.get('idTeam')
                team_name = team_data.get('strTeam')
                team_logo = team_data.get('strTeamBadge')
                
                if not all([team_id, team_name]):
                    continue
                    
                team, created = Team.objects.update_or_create(
                    id=team_id,
                    defaults={
                        'name': team_name,
                        'logo': team_logo,
                        'league': league
                    }
                )
                
                if created:
                    counter += 1
                    self.stdout.write(f'    + Yeni takım eklendi: {team_name}')
        
        self.stdout.write(self.style.SUCCESS(f'  {counter} yeni takım eklendi.'))

    @transaction.atomic
    def update_players(self, api):
        """API'den oyuncu verilerini çeker ve veritabanını günceller"""
        self.stdout.write('Oyuncu verilerini güncelleme...')
        teams = Team.objects.all()
        
        counter = 0
        for team in teams:
            self.stdout.write(f'  {team.name} için oyuncular getiriliyor...')
            players_data = api.get_team_players(team.id)
            
            for player_data in players_data:
                player_id = player_data.get('idPlayer')
                player_name = player_data.get('strPlayer')
                player_position = player_data.get('strPosition')
                
                if not all([player_id, player_name]):
                    continue
                
                # Pozisyonu bizim sistemimize göre uyarla
                position_map = {
                    'Goalkeeper': 'GK',
                    'Defender': 'DF',
                    'Midfielder': 'MF',
                    'Forward': 'FW'
                }
                
                position = 'FW'  # Varsayılan
                for key, value in position_map.items():
                    if player_position and key.lower() in player_position.lower():
                        position = value
                        break
                
                player, created = Player.objects.update_or_create(
                    id=player_id,
                    defaults={
                        'name': player_name,
                        'team': team,
                        'position': position
                    }
                )
                
                if created:
                    counter += 1
            
        self.stdout.write(self.style.SUCCESS(f'  {counter} yeni oyuncu eklendi.'))

    @transaction.atomic
    def update_matches(self, api):
        """API'den maç verilerini çeker ve veritabanını günceller"""
        self.stdout.write('Maç verilerini güncelleme...')
        leagues = League.objects.all()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Son 7 güne ait maçları işle
        for league in leagues:
            self.stdout.write(f'  {league.name} için maçlar getiriliyor...')
            events = api.get_events_by_league_and_date(league.id, today)
            
            # Ayrıca gelecek maçları da al
            future_events = api.get_league_next_events(league.id)
            if future_events:
                events.extend(future_events)
            
            for event_data in events:
                self._process_event(api, event_data, league)
        
        self.stdout.write(self.style.SUCCESS(f'  Maç verileri güncellendi.'))

    def _process_event(self, api, event_data, league):
        """Bir maç verisi işler ve veritabanına kaydeder"""
        event_id = event_data.get('idEvent')
        home_team_id = event_data.get('idHomeTeam')
        away_team_id = event_data.get('idAwayTeam')
        match_date_str = event_data.get('dateEvent')
        match_time_str = event_data.get('strTime')
        stadium = event_data.get('strVenue')
        score = None
        
        if event_data.get('intHomeScore') is not None and event_data.get('intAwayScore') is not None:
            score = f"{event_data.get('intHomeScore')}-{event_data.get('intAwayScore')}"
        
        # Gerekli alanların varlığını kontrol et
        if not all([event_id, home_team_id, away_team_id, match_date_str]):
            return
        
        try:
            # Takımları bul
            home_team = Team.objects.get(id=home_team_id)
            away_team = Team.objects.get(id=away_team_id)
            
            # Tarih ve saat formatını düzenle
            match_datetime = None
            try:
                if match_time_str:
                    match_datetime = datetime.strptime(f"{match_date_str} {match_time_str}", '%Y-%m-%d %H:%M:%S')
                else:
                    match_datetime = datetime.strptime(match_date_str, '%Y-%m-%d')
            except ValueError:
                # Tarih formatı sorunluysa sadece tarihi kullan
                match_datetime = datetime.strptime(match_date_str, '%Y-%m-%d')
            
            # Maçı oluştur veya güncelle
            match, created = Match.objects.update_or_create(
                id=event_id,
                defaults={
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': match_datetime,
                    'league': league,
                    'stadium': stadium or 'Bilinmiyor',
                    'score': score
                }
            )
            
            if created:
                self.stdout.write(f'    + Yeni maç eklendi: {home_team.name} vs {away_team.name}')
            
            # Maç olaylarını işle
            if score:  # Skoru varsa olayları da ekle
                # Ev sahibi takım golleri
                home_goals = event_data.get('strHomeGoalDetails')
                if home_goals and home_goals != 'null':
                    self._add_events(match, home_goals, home_team, 'GOAL')
                
                # Deplasman takım golleri
                away_goals = event_data.get('strAwayGoalDetails')
                if away_goals and away_goals != 'null':
                    self._add_events(match, away_goals, away_team, 'GOAL')
                
                # Sarı kartlar
                home_yellow = event_data.get('strHomeYellowCards')
                if home_yellow and home_yellow != 'null':
                    self._add_events(match, home_yellow, home_team, 'YELLOW')
                
                away_yellow = event_data.get('strAwayYellowCards')
                if away_yellow and away_yellow != 'null':
                    self._add_events(match, away_yellow, away_team, 'YELLOW')
                
                # Kırmızı kartlar
                home_red = event_data.get('strHomeRedCards')
                if home_red and home_red != 'null':
                    self._add_events(match, home_red, home_team, 'RED')
                
                away_red = event_data.get('strAwayRedCards')
                if away_red and away_red != 'null':
                    self._add_events(match, away_red, away_team, 'RED')
                
        except Team.DoesNotExist:
            self.stderr.write(f'    ! Takım bulunamadı: {home_team_id} veya {away_team_id}')
            return
        except Exception as e:
            self.stderr.write(f'    ! Hata: {str(e)}')
            return
    
    def _add_events(self, match, events_str, team, event_type):
        """Maç olaylarını işle ve veritabanına ekle"""
        if not events_str:
            return
            
        events_list = events_str.split(';')
        for event_detail in events_list:
            if not event_detail.strip():
                continue
                
            # Format: '15:PlayerName' veya sadece 'PlayerName'
            parts = event_detail.strip().split(':', 1)
            
            minute = None
            player_name = None
            
            if len(parts) == 2:
                try:
                    minute = int(parts[0].strip())
                    player_name = parts[1].strip()
                except ValueError:
                    player_name = event_detail.strip()
            else:
                player_name = event_detail.strip()
            
            # Oyuncuyu bul
            player = None
            if player_name:
                # Önce takım içinde ara
                players = Player.objects.filter(team=team, name__icontains=player_name)
                if players.exists():
                    player = players.first()
            
            # Olay kaydı oluştur
            if minute is not None or player is not None:
                description = f"{player_name if player_name else 'Bilinmeyen oyuncu'}"
                if event_type == 'GOAL':
                    description += f" {team.name} için gol attı"
                elif event_type == 'YELLOW':
                    description += f" sarı kart gördü"
                elif event_type == 'RED':
                    description += f" kırmızı kart gördü"
                
                Event.objects.update_or_create(
                    match=match,
                    minute=minute or 0,
                    event_type=event_type,
                    player=player,
                    defaults={
                        'description': description
                    }
                )
        
        leagues = fetch_leagues().get("leagues", [])
        for league_data in leagues:
            league, _ = League.objects.get_or_create(
                name=league_data["strLeague"],
                defaults={"country": league_data.get("strCountry", "")}
            )
            events = fetch_events_by_league(league_data["idLeague"]).get("events", [])
            for event in events:
                home_team, _ = Team.objects.get_or_create(name=event["strHomeTeam"])
                away_team, _ = Team.objects.get_or_create(name=event["strAwayTeam"])
                match_date = parse_datetime(event["dateEvent"] + "T" + (event.get("strTime", "00:00:00")))
                Match.objects.update_or_create(
                    home_team=home_team,
                    away_team=away_team,
                    match_date=match_date,
                    league=league,
                    defaults={
                        "stadium": event.get("strVenue", ""),
                        "score": (str(event.get("intHomeScore", "")) + "-" + str(event.get("intAwayScore", ""))) if event.get("intHomeScore") is not None else None
                    }
                )
        self.stdout.write(self.style.SUCCESS("Sports data updated."))
