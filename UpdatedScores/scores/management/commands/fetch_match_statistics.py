from django.core.management.base import BaseCommand
from scores.models import Match, MatchAnalysis
from scores.api_client import APIFootballClient
from django.db import transaction
import datetime


class Command(BaseCommand):
    help = "Fetch match statistics from API-FOOTBALL and save to MatchAnalysis"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Fetch statistics for matches within this many days before and after today (default: 2)',
        )
        parser.add_argument(
            '--match-id',
            type=str,
            help='Fetch statistics for a specific match ID',
        )

    def handle(self, *args, **options):
        client = APIFootballClient()
        days = options.get('days', 2)
        specific_match_id = options.get('match_id')
        
        # Fetch statistics for specific match if ID provided
        if specific_match_id:
            try:
                match = Match.objects.get(id=specific_match_id)
                self.fetch_and_save_stats(client, match)
                return
            except Match.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Match with ID {specific_match_id} not found"))
                return
        
        # Calculate date range
        today = datetime.datetime.now().date()
        from_date = today - datetime.timedelta(days=days)
        to_date = today + datetime.timedelta(days=days)
        
        # Get matches within date range, focusing on completed matches
        matches = Match.objects.filter(
            match_date__date__gte=from_date,
            match_date__date__lte=to_date,
            status__in=['FT', 'AET', 'PEN']  # Completed matches
        )
        
        if not matches:
            self.stdout.write(self.style.WARNING(f"No completed matches found between {from_date} and {to_date}"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"Found {matches.count()} completed matches to fetch statistics for"))
        
        # Fetch statistics for each match
        for idx, match in enumerate(matches, 1):
            self.stdout.write(f"[{idx}/{matches.count()}] Fetching stats for {match}")
            self.fetch_and_save_stats(client, match)
    
    def fetch_and_save_stats(self, client, match):
        """Fetch and save statistics data for a specific match"""
        self.stdout.write(f"Fetching statistics for match: {match}")
        
        try:
            # Fetch team statistics
            stats_data = client.get_statistics(match.id)
            
            # Fetch player statistics
            player_stats_data = client.get_player_statistics(match.id)
            
            # Check if API returned data
            if not stats_data or "response" not in stats_data or not stats_data["response"]:
                self.stdout.write(self.style.WARNING(f"No statistics data available for match {match.id}"))
                return
            
            # Process team statistics
            home_team_stats = {}
            away_team_stats = {}
            
            for team_stats in stats_data["response"]:
                team_id = str(team_stats.get("team", {}).get("id"))
                if not team_id:
                    continue
                
                # Determine if it's home or away team
                is_home = str(match.home_team.id) == team_id
                target_dict = home_team_stats if is_home else away_team_stats
                
                # Extract statistics
                for stat in team_stats.get("statistics", []):
                    stat_type = stat.get("type")
                    stat_value = stat.get("value")
                    if stat_type and stat_value is not None:
                        target_dict[stat_type] = stat_value
            
            # Create or update match analysis
            with transaction.atomic():
                analysis, created = MatchAnalysis.objects.get_or_create(
                    match=match,
                    defaults={
                        "possession": f"{home_team_stats.get('Ball Possession', '0%')}-{away_team_stats.get('Ball Possession', '0%')}",
                        "shots": f"{home_team_stats.get('Total Shots', 0)}-{away_team_stats.get('Total Shots', 0)}",
                        "shots_on_target": f"{home_team_stats.get('Shots on Goal', 0)}-{away_team_stats.get('Shots on Goal', 0)}",
                        "corners": f"{home_team_stats.get('Corner Kicks', 0)}-{away_team_stats.get('Corner Kicks', 0)}",
                        "fouls": f"{home_team_stats.get('Fouls', 0)}-{away_team_stats.get('Fouls', 0)}",
                        "yellows": f"{home_team_stats.get('Yellow Cards', 0)}-{away_team_stats.get('Yellow Cards', 0)}",
                        "reds": f"{home_team_stats.get('Red Cards', 0)}-{away_team_stats.get('Red Cards', 0)}",
                        "player_ratings": self.process_player_ratings(player_stats_data)
                    }
                )
                
                if not created:
                    # Update analysis fields
                    analysis.possession = f"{home_team_stats.get('Ball Possession', '0%')}-{away_team_stats.get('Ball Possession', '0%')}"
                    analysis.shots = f"{home_team_stats.get('Total Shots', 0)}-{away_team_stats.get('Total Shots', 0)}"
                    analysis.shots_on_target = f"{home_team_stats.get('Shots on Goal', 0)}-{away_team_stats.get('Shots on Goal', 0)}"
                    analysis.corners = f"{home_team_stats.get('Corner Kicks', 0)}-{away_team_stats.get('Corner Kicks', 0)}"
                    analysis.fouls = f"{home_team_stats.get('Fouls', 0)}-{away_team_stats.get('Fouls', 0)}"
                    analysis.yellows = f"{home_team_stats.get('Yellow Cards', 0)}-{away_team_stats.get('Yellow Cards', 0)}"
                    analysis.reds = f"{home_team_stats.get('Red Cards', 0)}-{away_team_stats.get('Red Cards', 0)}"
                    analysis.player_ratings = self.process_player_ratings(player_stats_data)
                    analysis.save()
                
                status = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(f"{status} match analysis for {match}"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching statistics for match {match.id}: {str(e)}"))
    
    def process_player_ratings(self, player_stats_data):
        """Process player statistics and return ratings dictionary"""
        ratings = {"home": [], "away": []}
        
        if not player_stats_data or "response" not in player_stats_data:
            return ratings
        
        for team_data in player_stats_data.get("response", []):
            team_side = "home" if team_data.get("team", {}).get("name") == team_data.get("teams", {}).get("home", {}).get("name") else "away"
            
            for player in team_data.get("players", []):
                player_info = player.get("player", {})
                player_stats = player.get("statistics", [{}])[0] if player.get("statistics") else {}
                
                player_rating = {
                    "id": str(player_info.get("id", "")),
                    "name": player_info.get("name", "Unknown Player"),
                    "rating": player_stats.get("games", {}).get("rating", "N/A"),
                    "minutes": player_stats.get("games", {}).get("minutes", 0),
                    "goals": player_stats.get("goals", {}).get("total", 0),
                    "assists": player_stats.get("goals", {}).get("assists", 0),
                    "passes": player_stats.get("passes", {}).get("total", 0),
                    "key_passes": player_stats.get("passes", {}).get("key", 0),
                    "shots": player_stats.get("shots", {}).get("total", 0),
                }
                
                ratings[team_side].append(player_rating)
        
        return ratings
