from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, Event, Match
import logging

logger = logging.getLogger(__name__)

# Prevent circular imports
def get_notification_service():
    from .notification_service import NotificationService
    return NotificationService

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        if hasattr(instance, 'profile'):
            instance.profile.save()
    except Profile.DoesNotExist:
        # If profile doesn't exist, create it with default values
        Profile.objects.create(
            user=instance,
            notify_goals=True,
            notify_red_cards=True,
            notify_match_start=True
        )

@receiver(post_save, sender=Event)
def handle_event_notification(sender, instance, created, **kwargs):
    """Send notifications based on event type when a new event is created."""
    if created:
        try:
            notification_service = get_notification_service()
            # Handle different event types
            if instance.event_type == 'GOAL':
                logger.info(f"Goal event detected: {instance.description}")
                notification_service.notify_about_goal(instance)
            elif instance.event_type == 'RED':
                logger.info(f"Red card event detected: {instance.description}")
                notification_service.notify_about_red_card(instance)
            # Add more event types as needed
        except Exception as e:
            logger.error(f"Failed to process event notification: {str(e)}")

@receiver(post_save, sender=Match)
def handle_match_status_changes(sender, instance, **kwargs):
    """Handle notifications for match status changes."""
    try:
        notification_service = get_notification_service()
        # Check if status is newly updated to indicate lineups are available
        if instance.status == 'LINEUP':
            notification_service.notify_lineup(instance, {})  # Pass empty dict for now
        
        # Check if match is about to start (e.g., status changed to 'PRE_MATCH')
        if instance.status == 'PRE_MATCH':
            notification_service.notify_match_start(instance)
    except Exception as e:
        logger.error(f"Failed to process match notification: {str(e)}")
