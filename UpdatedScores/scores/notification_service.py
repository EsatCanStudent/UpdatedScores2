import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from .models import Profile, Match, Event, Team, Player
from .notifications import Notification

logger = logging.getLogger(__name__)

class NotificationService:
    """Service to handle sending notifications to users based on their preferences."""
    
    @staticmethod
    def send_notification(user_profile, subject, message, event_type=None, url=None):
        """
        Send a notification to a user based on their notification preferences.
        
        Args:
            user_profile: Profile model instance
            subject: Notification subject
            message: Notification message
            event_type: Optional event type ("goal", "red_card", "lineup", "match_start", "important")
            url: Optional URL to include in the notification for direct navigation
        """
        notification_method = user_profile.notification_method
        
        # Check if this event type should be notified based on user preferences
        if event_type:
            if event_type == "goal" and not user_profile.notify_goals:
                return False
            elif event_type == "red_card" and not user_profile.notify_red_cards:
                return False
            elif event_type == "lineup" and not user_profile.notify_lineup:
                return False
            elif event_type == "match_start" and not user_profile.notify_match_start:
                return False
            elif event_type == "important" and not user_profile.notify_important_events:
                return False
        
        # Store notification in database regardless of delivery method
        try:
            # Create notification record
            Notification.objects.create(
                user=user_profile.user,
                notification_type=event_type if event_type else "system",
                title=subject,
                message=message,
                url=url
            )
            logger.info(f"Notification stored for user {user_profile.user.id}")
        except Exception as e:
            logger.error(f"Failed to store notification: {str(e)}")
            
        # Send based on notification method preference
        if notification_method in ["email", "both"]:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_profile.user.email],
                    fail_silently=False,
                )
                logger.info(f"Email notification sent to {user_profile.user.email}")
            except Exception as e:
                logger.error(f"Failed to send email notification: {str(e)}")
                return False
        
        if notification_method in ["push", "both"]:
            # In a real implementation, you would use a push notification service
            # This is a placeholder for future implementation
            try:
                logger.info(f"Push notification would be sent to user {user_profile.user.id}")
                # Implement push notifications here (Firebase, OneSignal, etc.)
                pass
            except Exception as e:
                logger.error(f"Failed to send push notification: {str(e)}")
                return False
                
        return True

    @classmethod
    def notify_about_goal(cls, event):
        """Send notifications for goal events."""
        match = event.match
        player = event.player
        message = f"GOL! {match.home_team.name} vs {match.away_team.name} maçında {player.name} ({player.team.name}) {event.minute}. dakikada gol attı!"
        subject = f" Gol: {player.team.name}"
        
        # Generate URL for the match detail page
        match_url = reverse("scores:match_detail", kwargs={"match_id": match.id})
        
        # Find users who follow this team or player
        team_followers = Profile.objects.filter(favorite_teams=player.team)
        player_followers = Profile.objects.filter(favorite_players=player)
        # Combine and remove duplicates
        followers = set(list(team_followers) + list(player_followers))
        
        for profile in followers:
            cls.send_notification(profile, subject, message, "goal", match_url)
    
    @classmethod
    def notify_about_red_card(cls, event):
        """Send notifications for red card events."""
        match = event.match
        player = event.player
        message = f"KIRMIZI KART! {match.home_team.name} vs {match.away_team.name} maçında {player.name} ({player.team.name}) {event.minute}. dakikada kırmızı kart gördü!"
        subject = f" Kırmızı Kart: {player.name}"
        
        # Generate URL for the match detail page
        match_url = reverse("scores:match_detail", kwargs={"match_id": match.id})
        
        # Find users who follow this team or player
        team_followers = Profile.objects.filter(favorite_teams=player.team)
        player_followers = Profile.objects.filter(favorite_players=player)
        # Combine and remove duplicates
        followers = set(list(team_followers) + list(player_followers))
        
        for profile in followers:
            cls.send_notification(profile, subject, message, "red_card", match_url)
    
    @classmethod
    def notify_match_start(cls, match):
        """Send notifications before a match starts."""
        # Find users who follow either team or the league
        home_followers = Profile.objects.filter(favorite_teams=match.home_team)
        away_followers = Profile.objects.filter(favorite_teams=match.away_team)
        league_followers = Profile.objects.filter(favorite_leagues=match.league)
        # Combine and remove duplicates
        followers = set(list(home_followers) + list(away_followers) + list(league_followers))
        
        message = f"Maç başlıyor! {match.home_team.name} vs {match.away_team.name} maçı 15 dakika içinde başlayacak. Yer: {match.stadium}"
        subject = f" Maç Bildirimi: {match.home_team.name} vs {match.away_team.name}"
        
        # Generate URL for the match detail page
        match_url = reverse("scores:match_detail", kwargs={"match_id": match.id})
        
        for profile in followers:
            cls.send_notification(profile, subject, message, "match_start", match_url)
    
    @classmethod
    def notify_lineup(cls, match, lineup_info):
        """Send notifications when lineups are announced."""
        # Find users who follow either team or the league
        home_followers = Profile.objects.filter(favorite_teams=match.home_team)
        away_followers = Profile.objects.filter(favorite_teams=match.away_team)
        league_followers = Profile.objects.filter(favorite_leagues=match.league)
        # Combine and remove duplicates
        followers = set(list(home_followers) + list(away_followers) + list(league_followers))
        
        # Format lineup information
        home_starters = ", ".join(lineup_info["home_team"][:11]) if len(lineup_info["home_team"]) >= 11 else ", ".join(lineup_info["home_team"])
        away_starters = ", ".join(lineup_info["away_team"][:11]) if len(lineup_info["away_team"]) >= 11 else ", ".join(lineup_info["away_team"])
        
        message = f"İlk 11 belli oldu! {match.home_team.name}: {home_starters} | {match.away_team.name}: {away_starters}"
        subject = f" İlk 11 Bildirimi: {match.home_team.name} vs {match.away_team.name}"
        
        # Generate URL for the match detail page
        match_url = reverse("scores:match_detail", kwargs={"match_id": match.id})
        
        for profile in followers:
            cls.send_notification(profile, subject, message, "lineup", match_url)

