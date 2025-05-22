from django.core.management.base import BaseCommand
from scores.models import Match, Event, Player
from scores.api_client import APIFootballClient
from django.db import transaction
import datetime


class Command(BaseCommand):
    help = "Fetch match events (goals, cards, substitutions) from API-FOOTBALL"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Fetch events for matches within this many days before and after today (default: 2)',
        )
        parser.add_argument(
            '--match-id',
            type=str,
            help='Fetch events for a specific match ID',
        )

    def handle(self, *args, **options):
        client = APIFootballClient()
        days = options.get('days', 2)
        specific_match_id = options.get('match_id')
        
        # Fetch events for specific match if ID provided
        if specific_match_id:
            try:
                match = Match.objects.get(id=specific_match_id)
                self.fetch_and_save_events(client, match)
                return
            except Match.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Match with ID {specific_match_id} not found"))
                return
        
        # Calculate date range
        today = datetime.datetime.now().date()
        from_date = today - datetime.timedelta(days=days)
        to_date = today + datetime.timedelta(days=days)
        
        # Get matches within date range, focusing on completed or ongoing matches
        matches = Match.objects.filter(
            match_date__date__gte=from_date,
            match_date__date__lte=to_date,
            status__in=['FT', 'HT', '1H', '2H', 'ET', 'BT', 'P', 'SUSP', 'INT', 'AET', 'PEN']  # Matches that might have events
        )
        
        if not matches:
            self.stdout.write(self.style.WARNING(f"No matches with events found between {from_date} and {to_date}"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"Found {matches.count()} matches to fetch events for"))
        
        # Fetch events for each match
        for idx, match in enumerate(matches, 1):
            self.stdout.write(f"[{idx}/{matches.count()}] Fetching events for {match}")
            self.fetch_and_save_events(client, match)
    
    def fetch_and_save_events(self, client, match):
        """Fetch and save event data for a specific match"""
        self.stdout.write(f"Fetching events for match: {match}")
        
        try:
            events_data = client.get_events(match.id)
            
            # Check if API returned data
            if not events_data or "response" not in events_data or not events_data["response"]:
                self.stdout.write(self.style.WARNING(f"No event data available for match {match.id}"))
                return
            
            # First, clear existing events for this match to avoid duplicates
            Event.objects.filter(match=match).delete()
            
            # Process events
            for event_data in events_data["response"]:
                self.process_event(event_data, match)
                
            self.stdout.write(self.style.SUCCESS(f"Successfully processed events for {match}"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching events for match {match.id}: {str(e)}"))
    
    def process_event(self, event_data, match):
        """Process event data and create Event record"""
        event_type = event_data.get("type")
        detail = event_data.get("detail")
        
        if not event_type:
            return
        
        # Map API event types to our model's event types
        event_type_mapping = {
            "Goal": "GOAL",
            "Card": "YELLOW" if detail == "Yellow Card" else "RED",
            "subst": "SUB",
            "Var": "GOAL" if "Goal" in detail else None,  # VAR decisions can be different types
        }
        
        model_event_type = event_type_mapping.get(event_type)
        if not model_event_type:
            # Skip events we don't track
            return
        
        # Get minute
        minute = event_data.get("time", {}).get("elapsed", 0)
          # Get player information
        player_id = None
        player_name = "Unknown Player"
        player_obj = None
        
        if "player" in event_data and event_data["player"]:
            player_id = str(event_data["player"].get("id", ""))
            player_name = event_data["player"].get("name", "Unknown Player")
            
            if player_id:
                # Try to find player in database
                player_obj = Player.objects.filter(id=player_id).first()
                
                # If player not found, try to create it
                if not player_obj and player_id and player_name:
                    try:
                        team_id = str(event_data.get("team", {}).get("id", ""))
                        team = Team.objects.filter(id=team_id).first()
                        if team:
                            # Determine likely position based on event type
                            event_type = event_data.get("type")
                            position = "MF"  # Default to midfielder
                            if event_type == "Goal":
                                position = "FW"  # Goal scorer likely forward
                            elif event_type == "Card" and event_data.get("detail") == "Red Card":
                                position = "DF"  # Red cards often to defenders
                                
                            player_obj, created = Player.objects.get_or_create(
                                id=player_id,
                                defaults={
                                    "name": player_name,
                                    "team": team,
                                    "position": position
                                }
                            )
                            if created:
                                self.stdout.write(f"Created new player: {player_name} for {team.name}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error creating player: {str(e)}"))
        
        # Build description
        team_name = event_data.get("team", {}).get("name", "Unknown Team")
        
        if model_event_type == "GOAL":
            assist_name = event_data.get("assist", {}).get("name")
            description = f"Goal by {player_name} for {team_name}"
            if assist_name:
                description += f" (Assisted by {assist_name})"
            if detail in ["Penalty", "Penalty Kick"]:
                description += " (Penalty)"
            elif detail == "Own Goal":
                description += " (Own Goal)"
        elif model_event_type in ["YELLOW", "RED"]:
            description = f"{detail} for {player_name} ({team_name})"
        elif model_event_type == "SUB":
            player_in = event_data.get("assist", {}).get("name", "Unknown Player")
            description = f"Substitution for {team_name}: {player_in} replaces {player_name}"
        else:
            description = f"{event_type} - {detail} - {player_name} ({team_name})"
        
        try:
            with transaction.atomic():
                # Create event record
                event = Event.objects.create(
                    match=match,
                    minute=minute,
                    event_type=model_event_type,
                    description=description,
                    player=player_obj  # May be None
                )
                
                self.stdout.write(f"Created event: {description} at {minute}'")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating event: {str(e)}"))
