import unittest
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from unittest.mock import patch, MagicMock

from ..models import Profile, Team, League, Player, Match, Event
from ..notification_service import NotificationService


class NotificationServiceTests(TestCase):
    def setUp(self):
        # Clear mail outbox before each test
        mail.outbox = []
        
        # Create test user and profile
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword'
        )
        self.profile = self.user.profile
        
        # Create test leagues, teams, and players
        self.league = League.objects.create(id='test-league', name='Test League', country='Test Country')
        
        self.team1 = Team.objects.create(id='team1', name='Team 1', league=self.league)
        self.team2 = Team.objects.create(id='team2', name='Team 2', league=self.league)
        
        self.player1 = Player.objects.create(id='player1', name='Player 1', team=self.team1, position='FW')
        self.player2 = Player.objects.create(id='player2', name='Player 2', team=self.team2, position='MF')
        
        # Create a test match
        self.match = Match.objects.create(
            id='match1',
            home_team=self.team1,
            away_team=self.team2,
            match_date=timezone.now() + timedelta(hours=1),
            league=self.league,
            stadium='Test Stadium'
        )
        
        # Add favorites to the profile
        self.profile.favorite_teams.add(self.team1)
        self.profile.favorite_players.add(self.player1)
        self.profile.favorite_leagues.add(self.league)
        
        # Configure notification preferences
        self.profile.notify_goals = True
        self.profile.notify_red_cards = True
        self.profile.notify_lineup = True
        self.profile.notify_match_start = True
        self.profile.notification_method = 'email'  # Use email for easy testing
        self.profile.save()
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_goal_notification(self):
        # Clear outbox before testing
        mail.outbox = []
        
        # Create a goal event
        goal_event = Event.objects.create(
            match=self.match,
            minute=30,
            event_type='GOAL',
            description='Goal for Team 1',
            player=self.player1
        )
        
        # Send notification about the goal
        NotificationService.notify_about_goal(goal_event)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('GOL!', mail.outbox[0].subject)
        self.assertIn(self.player1.name, mail.outbox[0].body)
        self.assertIn(self.team1.name, mail.outbox[0].body)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_red_card_notification(self):
        # Clear outbox before testing
        mail.outbox = []
        
        # Create a red card event
        red_card_event = Event.objects.create(
            match=self.match,
            minute=45,
            event_type='RED',
            description='Red card for Team 2',
            player=self.player2
        )
        
        # Add team2 to favorites to get notifications
        self.profile.favorite_teams.add(self.team2)
        
        # Send notification about the red card
        NotificationService.notify_about_red_card(red_card_event)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Kırmızı Kart', mail.outbox[0].subject)
        self.assertIn(self.player2.name, mail.outbox[0].body)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_match_start_notification(self):
        # Clear outbox before testing
        mail.outbox = []
        
        # Send notification about match start
        NotificationService.notify_match_start(self.match)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Maç Bildirimi', mail.outbox[0].subject)
        self.assertIn(self.team1.name, mail.outbox[0].body)
        self.assertIn(self.team2.name, mail.outbox[0].body)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_lineup_notification(self):
        # Clear outbox before testing
        mail.outbox = []
        
        # Send notification about lineup
        lineup_info = {
            'home_team': [self.player1.name],
            'away_team': [self.player2.name]
        }
        NotificationService.notify_lineup(self.match, lineup_info)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('İlk 11 Bildirimi', mail.outbox[0].subject)
        self.assertIn(self.team1.name, mail.outbox[0].body)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_notification_preferences_respected(self):
        # Clear outbox before testing
        mail.outbox = []
        
        # Disable goal notifications
        self.profile.notify_goals = False
        self.profile.save()
        
        # Create a goal event
        goal_event = Event.objects.create(
            match=self.match,
            minute=30,
            event_type='GOAL',
            description='Goal for Team 1',
            player=self.player1
        )
        
        # Try to send notification about the goal
        NotificationService.notify_about_goal(goal_event)
        
        # Check that no email was sent (preferences respected)
        self.assertEqual(len(mail.outbox), 0)


class UserProfileNotificationTests(TestCase):
    def setUp(self):
        # Create test user and login
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword'
        )
        self.client.login(username='testuser@example.com', password='testpassword')
        
        # Create test data
        self.league = League.objects.create(id='test-league', name='Test League', country='Test Country')
        self.team = Team.objects.create(id='team1', name='Team 1', league=self.league)
        self.player = Player.objects.create(id='player1', name='Player 1', team=self.team, position='FW')
    
    def test_profile_form_saves_notification_preferences(self):
        # Data to submit in the form
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'birth_date': '1990-01-01',
            'favorite_teams': [],
            'favorite_leagues': [],
            'favorite_players': [],
            'notify_goals': True,
            'notify_red_cards': False,
            'notify_lineup': True,
            'notify_match_start': False,
            'notify_important_events': True,
            'notification_method': 'email',
        }
        
        # Submit the form
        response = self.client.post(reverse('scores:edit_profile'), form_data)
        self.assertEqual(response.status_code, 302)  # Should redirect
        
        # Refresh profile from database
        self.user.profile.refresh_from_db()
        
        # Check that notification preferences were saved
        self.assertTrue(self.user.profile.notify_goals)
        self.assertFalse(self.user.profile.notify_red_cards)
        self.assertTrue(self.user.profile.notify_lineup)
        self.assertFalse(self.user.profile.notify_match_start)
        self.assertTrue(self.user.profile.notify_important_events)
        self.assertEqual(self.user.profile.notification_method, 'email')
