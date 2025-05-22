from django.core.management.base import BaseCommand
from scores.models import Match, Player, Team, Lineup, LineupPlayer
from scores.api_client import APIFootballClient
from django.db import transaction
import datetime


class Command(BaseCommand):
    help = "Fetch lineup data from API-FOOTBALL for recent or upcoming matches"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Fetch lineups for matches within this many days before and after today (default: 2)',
        )
        parser.add_argument(
            '--match-id',
            type=str,
            help='Fetch lineup for a specific match ID',
        )

    def handle(self, *args, **options):
        client = APIFootballClient()
        days = options.get('days', 2)
        specific_match_id = options.get('match_id')
        
        # Fetch lineups for specific match if ID provided
        if specific_match_id:
            try:
                match = Match.objects.get(id=specific_match_id)
                self.fetch_and_save_lineup(client, match)
                return
            except Match.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Match with ID {specific_match_id} not found"))
                return
        
        # Calculate date range
        today = datetime.datetime.now().date()
        from_date = today - datetime.timedelta(days=days)
        to_date = today + datetime.timedelta(days=days)
        
        # Get matches within date range
        matches = Match.objects.filter(
            match_date__date__gte=from_date,
            match_date__date__lte=to_date
        )
        
        if not matches:
            self.stdout.write(self.style.WARNING(f"No matches found between {from_date} and {to_date}"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"Found {matches.count()} matches within date range"))
        
        # Fetch lineups for each match
        for idx, match in enumerate(matches, 1):
            self.stdout.write(f"[{idx}/{matches.count()}] Fetching lineup for {match}")
            self.fetch_and_save_lineup(client, match)
    
    def fetch_and_save_lineup(self, client, match):
        """Fetch and save lineup data for a specific match"""
        self.stdout.write(f"Fetching lineup for match: {match}")
        
        try:
            lineup_data = client.get_lineups(match.id)
            
            # Check if API returned data
            if not lineup_data or "response" not in lineup_data or not lineup_data["response"]:
                self.stdout.write(self.style.WARNING(f"No lineup data available for match {match.id}"))
                return
            
            for team_lineup in lineup_data["response"]:
                team_id = str(team_lineup.get("team", {}).get("id"))
                if not team_id:
                    continue
                      # Get team from database
                try:
                    team = Team.objects.get(id=team_id)
                except Team.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Team with ID {team_id} not found"))
                    continue
                
                formation = team_lineup.get("formation")
                
                # Create or update the lineup record
                with transaction.atomic():
                    lineup, created = Lineup.objects.update_or_create(
                        match=match,
                        team=team,
                        defaults={
                            'formation': formation,
                            'is_confirmed': True
                        }
                    )
                    
                    status = "Created new" if created else "Updated existing"
                    self.stdout.write(f"{status} lineup for {team.name}")
                    
                    # First, clear any existing players from this lineup to avoid duplicates
                    LineupPlayer.objects.filter(lineup=lineup).delete()
                
                # Create or update players from starting XI
                for player_data in team_lineup.get("startXI", []):
                    self.process_player(player_data["player"], team, match, lineup, is_starter=True)
                
                # Create or update players from substitutes
                for player_data in team_lineup.get("substitutes", []):
                    self.process_player(player_data["player"], team, match, lineup, is_starter=False)
                    
                # Add coach if available
                if "coach" in team_lineup and team_lineup["coach"]:
                    coach_data = team_lineup["coach"]
                    coach_name = coach_data.get("name", "Unknown Coach")
                    self.stdout.write(f"Coach for {team.name}: {coach_name}")
                    
            self.stdout.write(self.style.SUCCESS(f"Successfully processed lineup for {match}"))
                      except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching lineup for match {match.id}: {str(e)}"))
            
    def process_player(self, player_data, team, match, lineup, is_starter=False):
        """Process player data and create or update Player record"""
        player_id = str(player_data.get("id"))
        if not player_id:
            return
        
        player_name = player_data.get("name", "Unknown Player")
        position = self.map_position(player_data.get("pos", ""))
        shirt_number = player_data.get("number")
        
        try:
            with transaction.atomic():
                player, created = Player.objects.get_or_create(
                    id=player_id,
                    defaults={
                        "name": player_name,
                        "team": team,
                        "position": position
                    }
                )
                
                if created:
                    self.stdout.write(f"Created new player: {player_name} ({position}) for {team.name}")
                else:
                    # Update player info if it has changed
                    if player.team != team:
                        player.team = team
                        player.save()
                        self.stdout.write(f"Updated player {player_name}'s team to {team.name}")
                
                # Create the lineup player record
                lineup_player = LineupPlayer.objects.create(
                    lineup=lineup,
                    player=player,
                    is_starter=is_starter,
                    position=player_data.get("pos"),
                    shirt_number=shirt_number
                )
                
                status = "Starting XI" if is_starter else "Substitute"
                self.stdout.write(f"Player {player_name} - {status} for {team.name}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing player {player_name}: {str(e)}"))
    
    def map_position(self, api_position):
        """Map API position codes to our model's position choices"""
        position_map = {
            "G": "GK",  # Goalkeeper
            "D": "DF",  # Defender
            "M": "MF",  # Midfielder
            "F": "FW",  # Forward
        }
        return position_map.get(api_position, "MF")  # Default to midfielder if unknown
