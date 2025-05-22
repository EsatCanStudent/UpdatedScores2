from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField

class League(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.name} ({self.country})"

class Team(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    logo = models.URLField(max_length=255, blank=True, null=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams')

    def __str__(self):
        return self.name

class Player(models.Model):
    POSITION_CHOICES = [
        ('GK', 'Goalkeeper'),
        ('DF', 'Defender'),
        ('MF', 'Midfielder'),
        ('FW', 'Forward'),
    ]

    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    position = models.CharField(max_length=2, choices=POSITION_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.get_position_display()} - {self.team})"

class Match(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    match_date = models.DateTimeField()
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    stadium = models.CharField(max_length=100)
    score = models.CharField(max_length=10, blank=True, null=True)
    round = models.CharField(max_length=50, blank=True, null=True)
    season = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)  # Scheduled, Completed, Live

    def __str__(self):
        if self.score:
            return f"{self.home_team} {self.score} {self.away_team} ({self.match_date.strftime('%Y-%m-%d')})"
        return f"{self.home_team} vs {self.away_team} ({self.match_date.strftime('%Y-%m-%d')})"

class Event(models.Model):
    EVENT_TYPES = [
        ('GOAL', 'Goal'),
        ('ASSIST', 'Assist'),
        ('YELLOW', 'Yellow Card'),
        ('RED', 'Red Card'),
        ('SUB', 'Substitution'),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='events')
    minute = models.IntegerField()
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES)
    description = models.TextField()
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    # TheSportsDB API bazen aynı olaylar için farklı kayıtlar içerir, doğal bir anahtar olmadığı için bir bileşik anahtar kullanıyoruz
    class Meta:
        unique_together = ('match', 'minute', 'event_type', 'player')

    def __str__(self):
        player_name = self.player.name if self.player else "Unknown Player"
        return f"{self.get_event_type_display()} at {self.minute}' by {player_name} ({self.match})"

class MatchPreview(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='preview')
    home_form = models.CharField(max_length=50, blank=True, help_text="Son 5 maç (ör: WWLDW)")
    away_form = models.CharField(max_length=50, blank=True, help_text="Son 5 maç (ör: WWLDW)")
    home_stats = models.JSONField(default=dict, blank=True, help_text="Ev sahibi takım istatistikleri")
    away_stats = models.JSONField(default=dict, blank=True, help_text="Deplasman takım istatistikleri")
    key_players = models.TextField(blank=True, help_text="Maçın kilit oyuncuları")
    prediction = models.CharField(max_length=100, blank=True, help_text="Maç tahmini")
    preview_text = models.TextField(blank=True, help_text="Maç önizleme yazısı")
    head_to_head = models.JSONField(default=dict, blank=True, help_text="Karşılıklı maç istatistikleri")
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Önizleme: {self.match}"

class MatchAnalysis(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='analysis')
    possession = models.CharField(max_length=10, blank=True, help_text="Topla oynama istatistiği (ör: 55%-45%)")
    shots = models.CharField(max_length=10, blank=True, help_text="Şut istatistiği (ör: 12-8)")
    shots_on_target = models.CharField(max_length=10, blank=True, help_text="İsabetli şut (ör: 5-3)")
    corners = models.CharField(max_length=10, blank=True, help_text="Korner (ör: 7-4)")
    fouls = models.CharField(max_length=10, blank=True, help_text="Faul (ör: 10-12)")
    yellows = models.CharField(max_length=10, blank=True, help_text="Sarı kart (ör: 3-2)")
    reds = models.CharField(max_length=10, blank=True, help_text="Kırmızı kart (ör: 1-0)")
    analysis_text = models.TextField(blank=True, help_text="Maç analiz yazısı")
    key_moments = models.JSONField(default=list, blank=True, help_text="Maçın önemli anları listesi")
    player_ratings = models.JSONField(default=dict, blank=True, help_text="Oyuncu puanları")
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analiz: {self.match}"

class Profile(models.Model):
    NOTIFICATION_METHOD_CHOICES = [
        ('push', 'Push Bildirimi'),
        ('email', 'E-Posta'),
        ('both', 'Her İkisi')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    favorite_teams = models.ManyToManyField(Team, blank=True, related_name='fans')
    favorite_leagues = models.ManyToManyField(League, blank=True, related_name='fans')
    favorite_players = models.ManyToManyField(Player, blank=True, related_name='fans')
    
    # Bildirim tercihleri
    notify_goals = models.BooleanField(default=True, verbose_name='Gol Bildirimleri')
    notify_red_cards = models.BooleanField(default=True, verbose_name='Kırmızı Kart Bildirimleri')
    notify_lineup = models.BooleanField(default=True, verbose_name='İlk 11 Bildirimleri')
    notify_match_start = models.BooleanField(default=True, verbose_name='Maç Başlama Bildirimleri')
    notify_important_events = models.BooleanField(default=True, verbose_name='Önemli Olaylar')
    
    # Bildirim yöntemi
    notification_method = models.CharField(
        max_length=10,
        choices=NOTIFICATION_METHOD_CHOICES,
        default='push',
        verbose_name='Bildirim Yöntemi'
    )
    
    # İlave bildirim ayarları için JSON alanı (gelecekteki genişlemeler için)
    notification_settings = JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} Profili"


class Lineup(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='lineups')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='match_lineups')
    formation = models.CharField(max_length=10, blank=True, null=True)
    is_confirmed = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('match', 'team')
    
    def __str__(self):
        return f"{self.team.name} lineup for {self.match}"


class LineupPlayer(models.Model):
    lineup = models.ForeignKey(Lineup, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='lineup_appearances')
    is_starter = models.BooleanField(default=False)
    position = models.CharField(max_length=20, blank=True, null=True)
    shirt_number = models.PositiveSmallIntegerField(blank=True, null=True)
    
    class Meta:
        unique_together = ('lineup', 'player')
        
    def __str__(self):
        status = "Starting XI" if self.is_starter else "Substitute"
        return f"{self.player.name} - {status} ({self.lineup.team.name})"