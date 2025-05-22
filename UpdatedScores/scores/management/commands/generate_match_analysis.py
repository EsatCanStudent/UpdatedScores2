import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from scores.models import Match, MatchAnalysis, MatchPreview, Event, Player
from datetime import timedelta
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Maçlar için otomatik analiz ve önizleme oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Kaç gün öncesine kadar olan maçları analiz etmek istediğiniz'
        )
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Gelecek maçlar için önizleme oluştur'
        )
        parser.add_argument(
            '--analysis',
            action='store_true',
            help='Tamamlanmış maçlar için analiz oluştur'
        )
        parser.add_argument(
            '--match_id',
            type=str,
            help='Belirli bir maç için analiz veya önizleme oluştur'
        )

    def handle(self, *args, **options):
        days = options['days']
        generate_preview = options['preview']
        generate_analysis = options['analysis']
        match_id = options.get('match_id')
        
        # Varsayılan olarak her ikisini de oluştur
        if not generate_preview and not generate_analysis:
            generate_preview = True
            generate_analysis = True
            
        if match_id:
            try:
                match = Match.objects.get(id=match_id)
                if generate_preview:
                    self.generate_preview_for_match(match)
                if generate_analysis and match.score:  # Sadece skoru olan maçlar için analiz oluştur
                    self.generate_analysis_for_match(match)
                self.stdout.write(self.style.SUCCESS(f'Maç ID {match_id} için işlemler tamamlandı.'))
            except Match.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'ID: {match_id} olan maç bulunamadı.'))
            return

        # Tarih sınırlaması
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Önizleme oluşturma
        if generate_preview:
            # Gelecekteki veya son 1 gün içindeki henüz oynanmamış maçlar
            future_matches = Match.objects.filter(
                match_date__gte=timezone.now() - timedelta(hours=3),  # Biraz geçmiş maçları da dahil et
                match_date__lte=timezone.now() + timedelta(days=7),   # Gelecek 7 gündeki maçlar
                score__isnull=True  # Henüz oynanmamış maçlar
            ).order_by('match_date')
            
            # Preview oluştur
            for match in future_matches:
                if not self.has_preview(match):
                    self.generate_preview_for_match(match)
                    self.stdout.write(f'Önizleme oluşturuldu: {match}')
        
        # Analiz oluşturma
        if generate_analysis:
            # Son N gün içinde tamamlanmış maçlar
            completed_matches = Match.objects.filter(
                match_date__gte=cutoff_date,
                match_date__lte=timezone.now(),
                score__isnull=False  # Skoru olan (tamamlanmış) maçlar
            ).order_by('-match_date')
            
            # Analiz oluştur
            for match in completed_matches:
                if not self.has_analysis(match):
                    self.generate_analysis_for_match(match)
                    self.stdout.write(f'Analiz oluşturuldu: {match}')
        
        self.stdout.write(self.style.SUCCESS('İşlemler başarıyla tamamlandı!'))

    def has_preview(self, match):
        """Maçın önizlemesi var mı kontrol et"""
        return hasattr(match, 'preview')
        
    def has_analysis(self, match):
        """Maçın analizi var mı kontrol et"""
        return hasattr(match, 'analysis')
        
    def generate_preview_for_match(self, match):
        """Bir maç için önizleme oluştur"""
        try:
            # Eğer zaten varsa güncelle
            try:
                preview = match.preview
            except MatchPreview.DoesNotExist:
                preview = MatchPreview(match=match)
            
            # İlgili takımların son 5 maçını al
            home_last_matches = Match.objects.filter(
                match_date__lt=match.match_date
            ).filter(
                home_team=match.home_team
            ).order_by('-match_date')[:5]
            
            away_last_matches = Match.objects.filter(
                match_date__lt=match.match_date
            ).filter(
                away_team=match.away_team
            ).order_by('-match_date')[:5]
            
            # Form verilerini hesapla
            home_form = self.calculate_form(home_last_matches, match.home_team)
            away_form = self.calculate_form(away_last_matches, match.away_team)
            
            preview.home_form = home_form
            preview.away_form = away_form
            
            # Karşılıklı maç istatistikleri
            h2h_matches = Match.objects.filter(
                match_date__lt=match.match_date,
                home_team__in=[match.home_team, match.away_team],
                away_team__in=[match.home_team, match.away_team],
                score__isnull=False
            ).order_by('-match_date')[:5]
            
            # H2H istatistiklerini JSON formatında kaydet
            h2h_stats = {
                'total': h2h_matches.count(),
                'home_wins': 0,
                'draws': 0,
                'away_wins': 0,
                'matches': []
            }
            
            for h2h in h2h_matches:
                if h2h.score:
                    try:
                        home_goals, away_goals = map(int, h2h.score.split('-'))
                        match_result = {}
                        
                        # Eğer ev sahibi takım bizim ev sahibimizse
                        if h2h.home_team == match.home_team:
                            if home_goals > away_goals:
                                h2h_stats['home_wins'] += 1
                                result = "HOME_WIN"
                            elif home_goals < away_goals:
                                h2h_stats['away_wins'] += 1
                                result = "AWAY_WIN"
                            else:
                                h2h_stats['draws'] += 1
                                result = "DRAW"
                        else:
                            if home_goals < away_goals:
                                h2h_stats['home_wins'] += 1
                                result = "HOME_WIN"
                            elif home_goals > away_goals:
                                h2h_stats['away_wins'] += 1
                                result = "AWAY_WIN"
                            else:
                                h2h_stats['draws'] += 1
                                result = "DRAW"
                                
                        match_result = {
                            'date': h2h.match_date.strftime('%Y-%m-%d'),
                            'home_team': h2h.home_team.name,
                            'away_team': h2h.away_team.name,
                            'score': h2h.score,
                            'result': result
                        }
                        h2h_stats['matches'].append(match_result)
                    except (ValueError, IndexError):
                        pass
            
            preview.head_to_head = h2h_stats
            
            # Takım istatistikleri
            home_stats = self.generate_team_stats(match.home_team)
            away_stats = self.generate_team_stats(match.away_team)
            
            preview.home_stats = home_stats
            preview.away_stats = away_stats
            
            # Tahmin ve önizleme metni
            preview.prediction = self.generate_prediction(match, home_form, away_form, h2h_stats)
            preview.preview_text = self.generate_preview_text(match, home_form, away_form, h2h_stats)
            preview.key_players = self.generate_key_players_text(match)
            
            preview.save()
            return preview
            
        except Exception as e:
            logger.error(f"Önizleme oluşturma hatası: {e}")
            self.stderr.write(self.style.ERROR(f"Hata: {e}"))
            return None
    
    def generate_analysis_for_match(self, match):
        """Bir maç için analiz oluştur"""
        try:
            # Eğer zaten varsa güncelle
            try:
                analysis = match.analysis
            except MatchAnalysis.DoesNotExist:
                analysis = MatchAnalysis(match=match)
            
            # Tamamlanmış maç için gerçekçi istatistikler oluştur
            if match.score:
                try:
                    home_goals, away_goals = map(int, match.score.split('-'))
                    
                    # Gol farkına göre istatistikler oluştur
                    goal_diff = home_goals - away_goals
                    if goal_diff > 0:  # Ev sahibi kazanmış
                        home_possession = random.randint(52, 65)
                    elif goal_diff < 0:  # Deplasman kazanmış
                        home_possession = random.randint(35, 48)
                    else:  # Beraberlik
                        home_possession = random.randint(45, 55)
                    
                    away_possession = 100 - home_possession
                    
                    # Şut istatistikleri, ev sahibinin daha çok topa sahip olmasıyla korele
                    home_shots = random.randint(max(5, home_goals * 2), 15 + home_goals * 2)
                    away_shots = random.randint(max(3, away_goals * 2), 12 + away_goals * 2)
                    
                    # İsabetli şutlar her zaman toplam şutlardan az olmalı ve gol sayısından fazla
                    home_shots_on_target = random.randint(home_goals, min(home_shots, home_goals + 5))
                    away_shots_on_target = random.randint(away_goals, min(away_shots, away_goals + 5))
                    
                    # Diğer istatistikler
                    home_corners = random.randint(max(2, home_shots // 3), home_shots // 2 + 3)
                    away_corners = random.randint(max(1, away_shots // 3), away_shots // 2 + 2)
                    
                    home_fouls = random.randint(5, 15)
                    away_fouls = random.randint(5, 15)
                    
                    # Kart istatistikleri
                    home_yellows = random.randint(0, min(5, home_fouls // 3 + 1))
                    away_yellows = random.randint(0, min(5, away_fouls // 3 + 1))
                    
                    home_reds = 1 if random.random() < 0.05 else 0  # %5 ihtimalle kırmızı kart
                    away_reds = 1 if random.random() < 0.05 else 0
                    
                    # İstatistikleri analiz nesnesine ata
                    analysis.possession = f"{home_possession}%-{away_possession}%"
                    analysis.shots = f"{home_shots}-{away_shots}"
                    analysis.shots_on_target = f"{home_shots_on_target}-{away_shots_on_target}"
                    analysis.corners = f"{home_corners}-{away_corners}"
                    analysis.fouls = f"{home_fouls}-{away_fouls}"
                    analysis.yellows = f"{home_yellows}-{away_yellows}"
                    analysis.reds = f"{home_reds}-{away_reds}"
                    
                    # Gerçek olayları al ve anahtar anları oluştur
                    events = Event.objects.filter(match=match).order_by('minute')
                    key_moments = []
                    
                    for event in events:
                        if event.event_type in ['GOAL', 'RED']:  # Önemli olaylar
                            key_moments.append({
                                'minute': event.minute,
                                'type': event.event_type,
                                'description': event.description,
                                'player': event.player.name if event.player else "Bilinmiyor"
                            })
                    
                    # Eğer az sayıda anahtar an varsa, rastgele birkaç tane ekle
                    if len(key_moments) < 3:
                        additional_moments = [
                            {'minute': random.randint(10, 40), 'type': 'CHANCE', 
                             'description': f"{match.home_team.name} tehlikeli bir atak geliştirdi ama değerlendiremedi.", 
                             'player': ""},
                            {'minute': random.randint(50, 80), 'type': 'CHANCE', 
                             'description': f"{match.away_team.name} kaleci ile karşı karşıya kaldı ancak şansını değerlendiremedi.", 
                             'player': ""},
                            {'minute': random.randint(25, 65), 'type': 'TACTICAL', 
                             'description': f"Taktiksel değişiklik yapıldı ve oyunun dengesi değişti.", 
                             'player': ""}
                        ]
                        key_moments.extend(additional_moments[:3-len(key_moments)])
                    
                    # Anahtar anları dakika sırasına göre sırala
                    key_moments.sort(key=lambda x: x['minute'])
                    analysis.key_moments = key_moments
                    
                    # Genel maç analizini oluştur
                    analysis.analysis_text = self.generate_analysis_text(match, home_goals, away_goals, home_possession, home_shots)
                    
                    # Oyuncu puanlarını oluştur
                    analysis.player_ratings = self.generate_player_ratings(match, home_goals, away_goals)
                    
                    analysis.save()
                    return analysis
                    
                except (ValueError, IndexError) as e:
                    logger.error(f"Skor analizi hatası: {e}")
                    self.stderr.write(self.style.ERROR(f"Skor analiz hatası: {e}"))
            
            return None
            
        except Exception as e:
            logger.error(f"Analiz oluşturma hatası: {e}")
            self.stderr.write(self.style.ERROR(f"Hata: {e}"))
            return None
    
    def calculate_form(self, matches, team):
        """Son 5 maçtan form hesapla (WWDLL gibi)"""
        form = ""
        for match in matches:
            if not match.score:
                continue
                
            try:
                home_goals, away_goals = map(int, match.score.split('-'))
                
                if match.home_team == team:
                    if home_goals > away_goals:
                        form += "W"
                    elif home_goals < away_goals:
                        form += "L"
                    else:
                        form += "D"
                else:
                    if away_goals > home_goals:
                        form += "W"
                    elif away_goals < home_goals:
                        form += "L"
                    else:
                        form += "D"
            except (ValueError, IndexError):
                pass
                
        if not form:
            # Form bilgisi yoksa rastgele form oluştur
            forms = ["W", "D", "L"]
            weights = [0.45, 0.3, 0.25]  # Kazanmanın biraz daha olası olması için
            form = ''.join(random.choices(forms, weights=weights, k=5))
            
        return form
    
    def generate_team_stats(self, team):
        """Takım için istatistikler oluştur"""
        # Son 5 maçtaki gol ortalaması
        recent_matches = Match.objects.filter(
            score__isnull=False,
            home_team=team 
        ).order_by('-match_date')[:5]
        
        goals_scored = 0
        goals_conceded = 0
        matches_played = 0
        
        for match in recent_matches:
            try:
                home_goals, away_goals = map(int, match.score.split('-'))
                goals_scored += home_goals
                goals_conceded += away_goals
                matches_played += 1
            except (ValueError, IndexError):
                pass
        
        away_matches = Match.objects.filter(
            score__isnull=False,
            away_team=team
        ).order_by('-match_date')[:5]
        
        for match in away_matches:
            try:
                home_goals, away_goals = map(int, match.score.split('-'))
                goals_scored += away_goals
                goals_conceded += home_goals
                matches_played += 1
            except (ValueError, IndexError):
                pass
        
        avg_goals_scored = goals_scored / matches_played if matches_played > 0 else 1.5
        avg_goals_conceded = goals_conceded / matches_played if matches_played > 0 else 1.0
        
        return {
            'avg_goals_scored': round(avg_goals_scored, 2),
            'avg_goals_conceded': round(avg_goals_conceded, 2),
            'clean_sheets': random.randint(0, 3),  # Rastgele temiz kağıt sayısı
            'avg_shots_per_game': round(random.uniform(8, 16), 1),  # Rastgele maç başına şut
            'avg_possession': f"{random.randint(45, 60)}%",  # Rastgele ortalama topa sahip olma
        }
    
    def generate_prediction(self, match, home_form, away_form, h2h_stats):
        """Maç tahmini oluştur"""
        predictions = [
            f"{match.home_team.name} 2-1 {match.away_team.name}",
            f"{match.home_team.name} 1-0 {match.away_team.name}",
            f"{match.home_team.name} 1-1 {match.away_team.name}",
            f"{match.home_team.name} 0-0 {match.away_team.name}",
            f"{match.home_team.name} 2-2 {match.away_team.name}",
            f"{match.home_team.name} 0-1 {match.away_team.name}",
        ]
        
        # Home form performance'ına bağlı olarak ağırlık ver
        home_wins = home_form.count('W')
        away_wins = away_form.count('W')
        
        # Karşılıklı maç geçmişine dayalı ağırlıklar
        h2h_home_bias = 0
        if h2h_stats['total'] > 0:
            h2h_home_bias = (h2h_stats['home_wins'] - h2h_stats['away_wins']) / h2h_stats['total']
        
        # Form ve h2h geçmişini kullanarak tahmin yap
        if home_wins >= 3 or (h2h_home_bias > 0.3):  # Ev sahibi formda veya h2h avantajı varsa
            weights = [0.35, 0.25, 0.15, 0.1, 0.1, 0.05]  # Ev sahibi galibiyet olasılığı yüksek
        elif away_wins >= 3 or (h2h_home_bias < -0.3):  # Deplasman formda veya h2h avantajı varsa
            weights = [0.1, 0.15, 0.2, 0.15, 0.1, 0.3]   # Deplasman galibiyet olasılığı yüksek
        else:  # Dengeli
            weights = [0.2, 0.2, 0.25, 0.15, 0.15, 0.05]  # Beraberlik olasılığı yüksek
            
        # Ağırlıklı rastgele seçim
        return random.choices(predictions, weights=weights, k=1)[0]
    
    def generate_preview_text(self, match, home_form, away_form, h2h_stats):
        """Maç önizleme metni oluştur"""
        # Takımların son formuna göre metinler
        home_form_text = self._get_form_text(home_form, match.home_team.name)
        away_form_text = self._get_form_text(away_form, match.away_team.name)
        
        # Karşılıklı maç geçmişine göre metin
        h2h_text = ""
        if h2h_stats['total'] > 0:
            if h2h_stats['home_wins'] > h2h_stats['away_wins']:
                h2h_text = f"İki takımın son karşılaşmalarında {match.home_team.name}, {match.away_team.name}'a karşı {h2h_stats['home_wins']}-{h2h_stats['away_wins']} üstünlük sağladı."
            elif h2h_stats['home_wins'] < h2h_stats['away_wins']:
                h2h_text = f"İki takımın son karşılaşmalarında {match.away_team.name}, {match.home_team.name}'a karşı {h2h_stats['away_wins']}-{h2h_stats['home_wins']} üstünlük sağladı."
            else:
                h2h_text = f"İki takımın son {h2h_stats['total']} karşılaşmasında eşitlik hakim oldu."
        else:
            h2h_text = f"Bu iki ekip yakın zamanda birbirleriyle karşılaşmadı."
        
        # Metin parçalarını birleştir
        preview_text = f"""
{match.league.name} kapsamında {match.match_date.strftime('%d.%m.%Y')} tarihinde {match.home_team.name} ile {match.away_team.name} karşı karşıya geliyor.

{home_form_text}

{away_form_text}

{h2h_text}

Bu önemli mücadelede iki takım da sahada üstünlük kurmak için elinden geleni yapacak. {match.stadium}'daki atmosfer, maçın sonucunda önemli bir faktör olabilir.
        """
        
        return preview_text.strip()
    
    def _get_form_text(self, form, team_name):
        """Form durumuna göre metin oluştur"""
        win_count = form.count('W')
        loss_count = form.count('L')
        draw_count = form.count('D')
        
        if win_count >= 3:
            return f"{team_name}, son maçlarında {win_count} galibiyet alarak çok iyi bir form yakaladı."
        elif loss_count >= 3:
            return f"{team_name}, son {loss_count} maçında mağlubiyet alarak formsuz bir görüntü çiziyor."
        elif draw_count >= 3:
            return f"{team_name}, son {draw_count} maçında berabere kalarak istikrarlı ancak galibiyete hasret bir performans sergiliyor."
        else:
            return f"{team_name}, son maçlarında {win_count} galibiyet, {draw_count} beraberlik ve {loss_count} mağlubiyetle inişli çıkışlı bir performans sergiledi."
    
    def generate_key_players_text(self, match):
        """Önemli oyuncular metni oluştur"""
        # Şablon kilit oyuncu metinleri
        key_player_templates = [
            "{player} bu maçta takımının en önemli silahı olacak.",
            "{player} son haftalardaki performansıyla dikkat çekiyor.",
            "{player} gol yollarında etkili olabilir.",
            "{player} defansta sağlam duruş sergilemesi gereken isim.",
            "{player} orta alanda oyun kuruculuk göreviyle öne çıkıyor."
        ]
        
        # Takımlardaki oyuncuları al
        home_players = Player.objects.filter(team=match.home_team)
        away_players = Player.objects.filter(team=match.away_team)
        
        # Rastgele oyuncu seç
        key_players_text = "Kilit Oyuncular:\n\n"
        
        # Ev sahibi takım oyuncuları
        key_players_text += f"{match.home_team.name}:\n"
        for _ in range(min(2, home_players.count())):
            if home_players.exists():
                player = random.choice(home_players)
                template = random.choice(key_player_templates)
                key_players_text += "- " + template.format(player=player.name) + "\n"
                
        # Deplasman takımı oyuncuları
        key_players_text += f"\n{match.away_team.name}:\n"
        for _ in range(min(2, away_players.count())):
            if away_players.exists():
                player = random.choice(away_players)
                template = random.choice(key_player_templates)
                key_players_text += "- " + template.format(player=player.name) + "\n"
                
        return key_players_text
        
    def generate_analysis_text(self, match, home_goals, away_goals, home_possession, home_shots):
        """Maç analiz metni oluştur"""
        team_dominant = match.home_team.name if home_possession > 50 else match.away_team.name
        team_clinical = match.home_team.name if home_goals > away_goals else match.away_team.name if away_goals > home_goals else None
        
        if home_goals > away_goals:
            result_text = f"{match.home_team.name}, {match.away_team.name}'u {match.score} mağlup etti."
        elif home_goals < away_goals:
            result_text = f"{match.away_team.name}, {match.home_team.name}'u deplasmanda {match.score} yendi."
        else:
            result_text = f"Mücadele {match.score} beraberlikle tamamlandı."
            
        analysis = f"""
{result_text}

{team_dominant} maç boyunca topa daha fazla sahip oldu ve oyun kontrolünü elinde tutmaya çalıştı. """
        
        if team_clinical and team_clinical != team_dominant:
            analysis += f"Ancak {team_clinical} pozisyonları daha iyi değerlendirerek sahadan galibiyetle ayrıldı."
        elif team_clinical and team_clinical == team_dominant:
            analysis += f"{team_clinical} hem oyun kontrolü hem de gol yollarında etkili olarak hak ettiği galibiyeti aldı."
        else:
            analysis += f"İki takım da gol fırsatlarını değerlendiremedi ve karşılaşma beraberlikle sona erdi."
            
        analysis += f"""

Maçın en önemli anlarından biri {random.randint(15, 75)}. dakikada yaşandı. {match.stadium}'da {random.randint(5000, 30000)} taraftar önünde oynanan karşılaşma, taraftarlara futbol ziyafeti sundu.
        """
        
        return analysis
        
    def generate_player_ratings(self, match, home_goals, away_goals):
        """Oyuncu puanlamaları oluştur"""
        player_ratings = {"home_team": {}, "away_team": {}}
        
        # Ev sahibi takım oyuncuları
        home_players = Player.objects.filter(team=match.home_team)
        for player in home_players:
            # Eğer gol atmışsa puanı yüksek olsun
            goal_event = Event.objects.filter(match=match, player=player, event_type='GOAL').exists()
            assist_event = Event.objects.filter(match=match, player=player, event_type='ASSIST').exists()
            card_event = Event.objects.filter(match=match, player=player, event_type__in=['YELLOW', 'RED']).exists()
            
            base_rating = 6.0 + random.uniform(0, 1)  # Temel puan 6-7 arası
            
            if goal_event:
                base_rating += 1.5  # Gol atan oyuncu +1.5 puan
            if assist_event:
                base_rating += 1.0  # Asist yapan oyuncu +1 puan
            if card_event:
                base_rating -= 0.5  # Kart gören oyuncu -0.5 puan
                
            # Takımları kazandıysa veya berabere kaldıysa puan artışı
            if home_goals > away_goals:
                base_rating += 0.5
            elif home_goals == away_goals:
                base_rating += 0.2
                
            # Puanı 10'dan fazla olmasın
            rating = min(round(base_rating, 1), 10.0)
            
            player_ratings["home_team"][player.name] = rating
            
        # Deplasman takımı oyuncuları
        away_players = Player.objects.filter(team=match.away_team)
        for player in away_players:
            goal_event = Event.objects.filter(match=match, player=player, event_type='GOAL').exists()
            assist_event = Event.objects.filter(match=match, player=player, event_type='ASSIST').exists()
            card_event = Event.objects.filter(match=match, player=player, event_type__in=['YELLOW', 'RED']).exists()
            
            base_rating = 6.0 + random.uniform(0, 1)
            
            if goal_event:
                base_rating += 1.5
            if assist_event:
                base_rating += 1.0
            if card_event:
                base_rating -= 0.5
                
            if away_goals > home_goals:
                base_rating += 0.5
            elif home_goals == away_goals:
                base_rating += 0.2
                
            rating = min(round(base_rating, 1), 10.0)
            
            player_ratings["away_team"][player.name] = rating
            
        return player_ratings