#!/usr/bin/env python
"""
API-FOOTBALL integration validation script.
This script tests the API-FOOTBALL integration by making sample API calls
and verifying the data models are properly populated.
"""

import os
import sys
import django
import argparse
from datetime import datetime, timedelta

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UpdatedScores.settings')
django.setup()

from django.core.management import call_command
from scores.api_client import APIFootballClient
from scores.models import League, Team, Match, Player, Event, Lineup, MatchPreview, MatchAnalysis

def validate_api_connection():
    """Test the API connection by retrieving leagues."""
    print("\n\033[1m1. Testing API Connection\033[0m")
    client = APIFootballClient()
    
    try:
        response = client.get_leagues()
        if not response or "response" not in response:
            print("❌ API connection failed. Check your API key and internet connection.")
            return False
            
        league_count = len(response.get("response", []))
        print(f"✅ API connection successful. Retrieved {league_count} leagues.")
        return True
    except Exception as e:
        print(f"❌ API connection error: {str(e)}")
        return False

def validate_models():
    """Verify that database models exist and have the correct structure."""
    print("\n\033[1m2. Validating Data Models\033[0m")
    models_to_check = [
        (League, ["id", "name", "country"]),
        (Team, ["id", "name", "logo", "league"]),
        (Player, ["id", "name", "team", "position"]),
        (Match, ["id", "home_team", "away_team", "match_date", "league", "score", "status"]),
        (Event, ["match", "minute", "event_type", "description", "player"]),
        (Lineup, ["match", "team", "formation", "is_confirmed"]),
        (MatchPreview, ["match", "home_form", "away_form", "prediction"]),
        (MatchAnalysis, ["match", "possession", "shots", "corners", "player_ratings"])
    ]
    
    all_valid = True
    for model, fields in models_to_check:
        try:
            # Check if all required fields exist
            for field in fields:
                model._meta.get_field(field)
            print(f"✅ {model.__name__} model is valid.")
        except Exception as e:
            print(f"❌ {model.__name__} model validation failed: {str(e)}")
            all_valid = False
            
    return all_valid

def test_fetch_commands():
    """Test the management commands for fetching data."""
    print("\n\033[1m3. Testing Management Commands\033[0m")
    commands = [
        "fetch_api_football_matches --date 2025-05-22 --no-delete",
        "fetch_match_lineups --days 1",
        "fetch_match_events --days 1", 
        "fetch_match_statistics --days 1",
        "fetch_match_previews --days 1"
    ]
    
    success_count = 0
    for cmd in commands:
        try:
            print(f"Running command: {cmd}")
            args = cmd.split()
            call_command(args[0], *args[1:])
            print(f"✅ Successfully executed: {cmd}")
            success_count += 1
        except Exception as e:
            print(f"❌ Command failed: {cmd}")
            print(f"   Error: {str(e)}")
    
    return success_count == len(commands)

def check_data_consistency():
    """Check if data is consistent across models."""
    print("\n\033[1m4. Checking Data Consistency\033[0m")
    
    try:
        # Get count of objects in each model
        league_count = League.objects.count()
        team_count = Team.objects.count()
        match_count = Match.objects.count()
        player_count = Player.objects.count()
        event_count = Event.objects.count()
        lineup_count = Lineup.objects.count()
        preview_count = MatchPreview.objects.count()
        analysis_count = MatchAnalysis.objects.count()
        
        print(f"Current data counts:")
        print(f"- Leagues: {league_count}")
        print(f"- Teams: {team_count}")
        print(f"- Matches: {match_count}")
        print(f"- Players: {player_count}")
        print(f"- Events: {event_count}")
        print(f"- Lineups: {lineup_count}")
        print(f"- Match Previews: {preview_count}")
        print(f"- Match Analyses: {analysis_count}")
        
        # Check if we have at least some data
        if league_count == 0 or team_count == 0 or match_count == 0:
            print("❌ Insufficient data found in the database.")
            return False
            
        # Pick a random match and check related data
        if match_count > 0:
            match = Match.objects.order_by('?').first()
            print(f"\nChecking data consistency for match: {match}")
            
            # Check if match has related teams
            if not match.home_team or not match.away_team:
                print("❌ Match is missing team data.")
                return False
                
            print(f"✅ Match has valid team references: {match.home_team} vs {match.away_team}")
        
        return True
    except Exception as e:
        print(f"❌ Data consistency check failed: {str(e)}")
        return False

def check_update_schedule():
    """Verify that the football update scheduler can be run."""
    print("\n\033[1m5. Testing Update Scheduler\033[0m")
    
    try:
        # Only test for a very short time
        call_command('schedule_football_updates')
        print("✅ Update scheduler executed successfully.")
        return True
    except Exception as e:
        print(f"❌ Update scheduler failed: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Validate API-FOOTBALL Integration')
    parser.add_argument('--full', action='store_true', help='Run all tests including data fetching')
    args = parser.parse_args()
    
    print("\033[1m======= API-FOOTBALL Integration Validation =======\033[0m")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Step 1: Test API connection
    api_connection_valid = validate_api_connection()
    results.append(("API Connection", api_connection_valid))
    
    # Step 2: Validate models
    models_valid = validate_models()
    results.append(("Data Models", models_valid))
    
    # Step 3: Test fetch commands (only if --full is specified)
    if args.full:
        fetch_commands_valid = test_fetch_commands()
        results.append(("Fetch Commands", fetch_commands_valid))
    else:
        print("\n\033[1m3. Skipping Management Commands Test\033[0m")
        print("Use --full to run all tests including data fetching.")
    
    # Step 4: Check data consistency
    data_consistent = check_data_consistency()
    results.append(("Data Consistency", data_consistent))
    
    # Step 5: Test update scheduler (only if --full is specified)
    if args.full:
        scheduler_valid = check_update_schedule()
        results.append(("Update Scheduler", scheduler_valid))
    else:
        print("\n\033[1m5. Skipping Update Scheduler Test\033[0m")
        
    # Print summary
    print("\n\033[1m======= Validation Summary =======\033[0m")
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n\033[1;32mAPI-FOOTBALL Integration is VALID!\033[0m")
        return 0
    else:
        print("\n\033[1;31mAPI-FOOTBALL Integration has ISSUES that need to be addressed.\033[0m")
        return 1

if __name__ == "__main__":
    sys.exit(main())
