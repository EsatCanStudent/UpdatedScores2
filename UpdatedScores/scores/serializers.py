from rest_framework import serializers
from .models import League, Team, Player, Match, Event, Profile
from django.contrib.auth.models import User

class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = ['id', 'name', 'country']

class TeamSerializer(serializers.ModelSerializer):
    league = LeagueSerializer(read_only=True)
    class Meta:
        model = Team
        fields = ['id', 'name', 'logo', 'league']

class MatchSerializer(serializers.ModelSerializer):
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    league = LeagueSerializer(read_only=True)
    class Meta:
        model = Match
        fields = ['id', 'home_team', 'away_team', 'match_date', 'league', 'stadium', 'score']

class ProfileSerializer(serializers.ModelSerializer):
    favorite_teams = TeamSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Profile
        fields = ['user', 'first_name', 'last_name', 'birth_date', 'favorite_teams']
