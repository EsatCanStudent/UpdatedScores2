from django.core.management.base import BaseCommand
from scores.models import Match, MatchPreview, Team
from scores.api_client import APIFootballClient
from django.db import transaction
import datetime


class Command(BaseCommand):
    help = "Fetch match previews from API-FOOTBALL including head-to-head stats and predictions"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Fetch previews for matches within this many days after today (default: 2)',
        )
        parser.add_argument(
            '--match-id',
            type=str,
            help='Fetch preview for a specific match ID',
        )

    def handle(self, *args, **options):
        client = APIFootballClient()
        days = options.get('days', 2)
        specific_match_id = options.get('match_id')
        
        # Fetch preview for specific match if ID provided
        if specific_match_id:
            try:
                match = Match.objects.get(id=specific_match_id)
                self.fetch_and_save_preview(client, match)
                return
            except Match.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Match with ID {specific_match_id} not found"))
                return
        
        # Calculate date range - only upcoming matches need previews
        today = datetime.datetime.now().date()
        to_date = today + datetime.timedelta(days=days)
        
        # Get upcoming matches within date range
        matches = Match.objects.filter(
            match_date__date__gte=today,
            match_date__date__lte=to_date,
            status__in=['NS', 'TBD']  # Not started or to be determined
        )
        
        if not matches:
            self.stdout.write(self.style.WARNING(f"No upcoming matches found between {today} and {to_date}"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"Found {matches.count()} upcoming matches to fetch previews for"))
        
        # Fetch previews for each match
        for idx, match in enumerate(matches, 1):
            self.stdout.write(f"[{idx}/{matches.count()}] Fetching preview for {match}")
            self.fetch_and_save_preview(client, match)
    
    def fetch_and_save_preview(self, client, match):
        """Fetch and save preview data for a specific match"""
        self.stdout.write(f"Fetching preview for match: {match}")
        
        try:
            # Fetch predictions
            predictions_data = client.get_predictions(match.id)
            
            # Get head-to-head data for the two teams
            h2h_data = self.fetch_head_to_head(client, match.home_team.id, match.away_team.id)
            
            # Process prediction data
            prediction_info = {}
            h2h_info = {}
            
            if predictions_data and "response" in predictions_data and predictions_data["response"]:
                prediction = predictions_data["response"][0]
                
                # Extract prediction information
                prediction_info = {
                    "winner": prediction.get("predictions", {}).get("winner", {}).get("name"),
                    "win_or_draw": prediction.get("predictions", {}).get("win_or_draw", False),
                    "under_over": prediction.get("predictions", {}).get("under_over"),
                    "goals": prediction.get("predictions", {}).get("goals", {})
                }
                
                # Get form for both teams
                home_form = prediction.get("teams", {}).get("home", {}).get("league", {}).get("form", "")
                away_form = prediction.get("teams", {}).get("away", {}).get("league", {}).get("form", "")
                
                # Extract a summary from the detailed comparison
                comparison = prediction.get("comparison", {})
                key_players_info = []
                
                # Extract team statistics
                home_stats = {}
                away_stats = {}
                
                if "teams" in prediction:
                    if "home" in prediction["teams"]:
                        home_team_data = prediction["teams"]["home"]
                        if "league" in home_team_data:
                            league_stats = home_team_data["league"]
                            home_stats = {
                                "form": league_stats.get("form", ""),
                                "fixtures": league_stats.get("fixtures", {}),
                                "goals": league_stats.get("goals", {}),
                                "biggest": league_stats.get("biggest", {}),
                                "clean_sheet": league_stats.get("clean_sheet", {})
                            }
                    
                    if "away" in prediction["teams"]:
                        away_team_data = prediction["teams"]["away"]
                        if "league" in away_team_data:
                            league_stats = away_team_data["league"]
                            away_stats = {
                                "form": league_stats.get("form", ""),
                                "fixtures": league_stats.get("fixtures", {}),
                                "goals": league_stats.get("goals", {}),
                                "biggest": league_stats.get("biggest", {}),
                                "clean_sheet": league_stats.get("clean_sheet", {})
                            }
            
            # Process head-to-head data
            if h2h_data and "response" in h2h_data:
                h2h_matches = h2h_data.get("response", [])
                h2h_info = {
                    "total_matches": len(h2h_matches),
                    "matches": [],
                    "home_wins": 0,
                    "away_wins": 0,
                    "draws": 0
                }
                
                for h2h_match in h2h_matches[:10]:  # Limit to the 10 most recent matches
                    home_id = str(h2h_match.get("teams", {}).get("home", {}).get("id", ""))
                    home_goals = h2h_match.get("goals", {}).get("home", 0)
                    away_goals = h2h_match.get("goals", {}).get("away", 0)
                    
                    match_result = None
                    if home_goals > away_goals:
                        if home_id == match.home_team.id:
                            match_result = "home_win"
                            h2h_info["home_wins"] += 1
                        else:
                            match_result = "away_win"
                            h2h_info["away_wins"] += 1
                    elif away_goals > home_goals:
                        if home_id == match.away_team.id:
                            match_result = "away_win"
                            h2h_info["away_wins"] += 1
                        else:
                            match_result = "home_win"
                            h2h_info["home_wins"] += 1
                    else:
                        match_result = "draw"
                        h2h_info["draws"] += 1
                    
                    h2h_info["matches"].append({
                        "date": h2h_match.get("fixture", {}).get("date"),
                        "home_team": h2h_match.get("teams", {}).get("home", {}).get("name"),
                        "away_team": h2h_match.get("teams", {}).get("away", {}).get("name"),
                        "score": f"{home_goals}-{away_goals}",
                        "result": match_result
                    })
            
            # Create or update match preview
            with transaction.atomic():
                # Build preview text based on statistics and predictions
                home_team_name = match.home_team.name
                away_team_name = match.away_team.name
                
                # Generate a basic preview text using the available data
                preview_text = self.generate_preview_text(
                    home_team_name, 
                    away_team_name, 
                    home_stats, 
                    away_stats,
                    h2h_info,
                    prediction_info
                )
                
                # Generate a prediction string
                prediction_str = "Match too close to call"
                if "winner" in prediction_info and prediction_info["winner"]:
                    if prediction_info["winner"] == home_team_name:
                        prediction_str = f"{home_team_name} win"
                    else:
                        prediction_str = f"{away_team_name} win"
                
                # Create or update the preview
                preview, created = MatchPreview.objects.update_or_create(
                    match=match,
                    defaults={
                        "home_form": home_stats.get("form", ""),
                        "away_form": away_stats.get("form", ""),
                        "home_stats": home_stats,
                        "away_stats": away_stats,
                        "head_to_head": h2h_info,
                        "prediction": prediction_str,
                        "preview_text": preview_text
                    }
                )
                
                status = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(f"{status} match preview for {match}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching preview for match {match.id}: {str(e)}"))
    
    def fetch_head_to_head(self, client, home_team_id, away_team_id, limit=10):
        """Fetch head-to-head statistics between two teams"""
        try:
            # Construct endpoint parameters
            h2h_url = f"fixtures/headtohead"
            params = {
                'h2h': f"{home_team_id}-{away_team_id}",
                'last': limit
            }
            
            # Make API request using internal API client helper
            return client._make_request(h2h_url, params)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching head-to-head data: {str(e)}"))
            return None
    
    def generate_preview_text(self, home_team, away_team, home_stats, away_stats, h2h_info, prediction_info):
        """Generate preview text based on available data"""
        text = f"Match Preview: {home_team} vs {away_team}\n\n"
        
        # Add form information
        home_form = home_stats.get("form", "")
        away_form = away_stats.get("form", "")
        if home_form:
            text += f"{home_team} recent form: {home_form}\n"
        if away_form:
            text += f"{away_team} recent form: {away_form}\n"
        
        # Add head-to-head record
        if h2h_info:
            total = h2h_info.get("total_matches", 0)
            home_wins = h2h_info.get("home_wins", 0)
            away_wins = h2h_info.get("away_wins", 0)
            draws = h2h_info.get("draws", 0)
            
            if total > 0:
                text += f"\nHead-to-head record (last {min(total, 10)} matches):\n"
                text += f"{home_team} wins: {home_wins}\n"
                text += f"{away_team} wins: {away_wins}\n"
                text += f"Draws: {draws}\n"
        
        # Add goal statistics
        home_goals_for = home_stats.get("goals", {}).get("for", {}).get("total", {}).get("total")
        home_goals_against = home_stats.get("goals", {}).get("against", {}).get("total", {}).get("total")
        away_goals_for = away_stats.get("goals", {}).get("for", {}).get("total", {}).get("total")
        away_goals_against = away_stats.get("goals", {}).get("against", {}).get("total", {}).get("total")
        
        if home_goals_for is not None and home_goals_against is not None:
            text += f"\n{home_team} has scored {home_goals_for} and conceded {home_goals_against} goals this season.\n"
        if away_goals_for is not None and away_goals_against is not None:
            text += f"{away_team} has scored {away_goals_for} and conceded {away_goals_against} goals this season.\n"
        
        # Add prediction information
        if prediction_info and "winner" in prediction_info and prediction_info["winner"]:
            text += f"\nPrediction: {prediction_info['winner']} to win."
        else:
            text += "\nThis match is too close to call."
            
        return text
