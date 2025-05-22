from django.db import models

class League(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.country})"

class Team(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='team_logos/', blank=True, null=True)
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

    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    position = models.CharField(max_length=2, choices=POSITION_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.get_position_display()} - {self.team})"

class Match(models.Model):
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    match_date = models.DateTimeField()
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    stadium = models.CharField(max_length=100)
    score = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
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

    def __str__(self):
        player_name = self.player.name if self.player else "Unknown Player"
        return f"{self.get_event_type_display()} at {self.minute}' by {player_name} ({self.match})"