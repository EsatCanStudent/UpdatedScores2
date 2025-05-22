from django.core.management.base import BaseCommand
from scores.models import Match, Event, Profile
from scores.api_client import APIFootballClient
from scores.notification_service import send_notification
from django.db import transaction
from django.utils import timezone
import datetime
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Continuously check for live match events and send notifications"

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds between API checks (default: 60)',
        )
        parser.add_argument(
            '--log-level',
            type=str,
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Set the logging level',
        )

    def handle(self, *args, **options):
        interval = options.get('interval', 60)
        log_level = getattr(logging, options.get('log_level', 'INFO'))
        logging.basicConfig(level=log_level)
        
        self.stdout.write(self.style.SUCCESS(f"Starting live event monitoring with {interval} second interval"))
        
        # Track processed events to avoid duplicates
        processed_events = set()
        
        try:
            while True:
                self.stdout.write(f"Checking for live match events at {timezone.now().strftime('%H:%M:%S')}")
                
                # Get today's live matches
                live_matches = self.get_live_matches()
                
                if not live_matches:
                    self.stdout.write("No live matches at the moment. Waiting...")
                else:
                    self.stdout.write(f"Found {len(live_matches)} live matches")
                    
                    # Check each match for new events
                    for match in live_matches:
                        self.check_and_notify_match_events(match, processed_events)
                
                # Wait for next check
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Live event monitoring stopped by user"))
    
    def get_live_matches(self):
        """Get matches that are currently live"""
        today = timezone.now().date()
        
        # Status codes for live matches (based on API-FOOTBALL status codes)
        live_statuses = ['1H', '2H', 'HT', 'ET', 'BT', 'P', 'LIVE']
        
        return Match.objects.filter(
            match_date__date=today,
            status__in=live_statuses
        )
    
    def check_and_notify_match_events(self, match, processed_events):
        """Check for new events in a live match and send notifications"""
        client = APIFootballClient()
        
        try:
            # Fetch latest events
            events_data = client.get_events(match.id)
            
            if not events_data or "response" not in events_data:
                logger.warning(f"No event data received for match {match.id}")
                return
            
            # Process each event
            for event_data in events_data["response"]:
                # Create a unique identifier for this event
                event_type = event_data.get("type")
                if not event_type:
                    continue
                
                minute = event_data.get("time", {}).get("elapsed", 0)
                player_id = event_data.get("player", {}).get("id")
                detail = event_data.get("detail", "")
                team_id = event_data.get("team", {}).get("id")
                
                # Create unique event identifier
                event_key = f"{match.id}_{event_type}_{minute}_{player_id}_{detail}"
                
                # Skip if we've processed this event already
                if event_key in processed_events:
                    continue
                
                # Map event types
                if event_type == "Goal":
                    self.process_goal_event(match, event_data, processed_events, event_key)
                elif event_type == "Card" and detail == "Red Card":
                    self.process_red_card_event(match, event_data, processed_events, event_key)
                
                # Mark this event as processed
                processed_events.add(event_key)
            
            # Cleanup processed_events to prevent memory issues (keep only recent ones)
            if len(processed_events) > 1000:
                self.stdout.write("Cleaning up processed events cache...")
                processed_events.clear()
                
        except Exception as e:
            logger.error(f"Error checking events for match {match.id}: {str(e)}")
    
    def process_goal_event(self, match, event_data, processed_events, event_key):
        """Process and notify about a goal event"""
        minute = event_data.get("time", {}).get("elapsed", 0)
        player_name = event_data.get("player", {}).get("name", "Unknown Player")
        team_name = event_data.get("team", {}).get("name", "")
        team_id = str(event_data.get("team", {}).get("id", ""))
        
        # Determine if it's home or away team
        is_home = str(match.home_team.id) == team_id
        
        # Update score if possible
        if match.score:
            try:
                home_goals, away_goals = map(int, match.score.split('-'))
                if is_home:
                    home_goals += 1
                else:
                    away_goals += 1
                match.score = f"{home_goals}-{away_goals}"
                match.save(update_fields=['score'])
            except (ValueError, AttributeError):
                logger.warning(f"Could not update score for match {match.id}")
        
        # Create notification message
        message = f"⚽ GOAL! {minute}' - {player_name} scores for {team_name}!"
        
        # Add the score if available
        if match.score:
            message += f" Score: {match.home_team.name} {match.score} {match.away_team.name}"
        
        # Find profiles to notify (fans of the teams or players involved)
        self.send_notification_to_fans(match, message, player_id=event_data.get("player", {}).get("id"), 
                                     team_id=team_id, notify_type="notify_goals")
        
        self.stdout.write(self.style.SUCCESS(f"Goal notification sent: {message}"))
    
    def process_red_card_event(self, match, event_data, processed_events, event_key):
        """Process and notify about a red card event"""
        minute = event_data.get("time", {}).get("elapsed", 0)
        player_name = event_data.get("player", {}).get("name", "Unknown Player")
        team_name = event_data.get("team", {}).get("name", "")
        
        # Create notification message
        message = f"🔴 RED CARD! {minute}' - {player_name} ({team_name}) has been sent off!"
        
        # Find profiles to notify
        self.send_notification_to_fans(match, message, player_id=event_data.get("player", {}).get("id"), 
                                     team_id=str(event_data.get("team", {}).get("id", "")), 
                                     notify_type="notify_red_cards")
        
        self.stdout.write(self.style.SUCCESS(f"Red card notification sent: {message}"))
    
    def send_notification_to_fans(self, match, message, player_id=None, team_id=None, notify_type="notify_goals"):
        """Send notifications to relevant fans based on preferences"""
        try:
            # Find users who are interested in these teams or this league
            profiles = Profile.objects.filter(**{notify_type: True})
            
            # Filter for those following this league
            league_fans = profiles.filter(favorite_leagues=match.league)
            
            # Filter for those following the teams
            team_fans = Profile.objects.none()
            if team_id:
                team_fans = profiles.filter(favorite_teams__id=team_id)
            
            # Filter for those following the player
            player_fans = Profile.objects.none()
            if player_id:
                player_fans = profiles.filter(favorite_players__id=player_id)
            
            # Combine all relevant fans (without duplicates)
            fans = (league_fans | team_fans | player_fans).distinct()
            
            if not fans:
                logger.info(f"No fans to notify for this event")
                return
            
            # Send notifications
            for profile in fans:
                try:
                    # Choose notification method based on user preference
                    method = profile.notification_method
                    send_notification(
                        user=profile.user,
                        title=f"Match Update: {match.home_team.name} vs {match.away_team.name}",
                        message=message,
                        method=method,
                        match_id=match.id
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {profile.user.id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
