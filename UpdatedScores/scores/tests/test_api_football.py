from django.test import TestCase
from unittest.mock import patch, MagicMock
from scores.api_client import APIFootballClient
from scores.models import League, Team, Match, Player
import json
import os

class APIFootballClientTestCase(TestCase):
    
    def setUp(self):
        self.client = APIFootballClient()
    
    @patch('scores.api_client.requests.get')
    def test_get_leagues(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": [
                {
                    "league": {
                        "id": 39,
                        "name": "Premier League",
                        "type": "League",
                        "country": "England"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.get_leagues()
        
        # Assert results
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/leagues",
            headers=self.client.headers,
            params={},
            timeout=30
        )
        self.assertEqual(result["response"][0]["league"]["name"], "Premier League")
        
    @patch('scores.api_client.requests.get')
    def test_get_fixtures(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": [
                {
                    "fixture": {
                        "id": 123,
                        "date": "2025-05-28T14:00:00+00:00",
                        "venue": {
                            "name": "Emirates Stadium"
                        }
                    },
                    "league": {
                        "id": 39,
                        "name": "Premier League",
                        "season": 2024
                    },
                    "teams": {
                        "home": {
                            "id": 42,
                            "name": "Arsenal FC"
                        },
                        "away": {
                            "id": 51,
                            "name": "Brighton"
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method with parameters
        result = self.client.get_fixtures(league_id=39, season=2024)
        
        # Assert results
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/fixtures",
            headers=self.client.headers,
            params={'league': 39, 'season': 2024},
            timeout=30
        )
        self.assertEqual(result["response"][0]["teams"]["home"]["name"], "Arsenal FC")
        
    @patch('scores.api_client.requests.get')
    def test_get_lineups(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": [
                {
                    "team": {
                        "id": 42,
                        "name": "Arsenal FC"
                    },
                    "formation": "4-3-3",
                    "startXI": [
                        {
                            "player": {
                                "id": 1,
                                "name": "Goalkeeper",
                                "pos": "G"
                            }
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.get_lineups(fixture_id=123)
        
        # Assert results
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/fixtures/lineups",
            headers=self.client.headers,
            params={'fixture': 123},
            timeout=30
        )
        self.assertEqual(result["response"][0]["formation"], "4-3-3")
        
    @patch('scores.api_client.requests.get')
    def test_get_events(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": [
                {
                    "time": {
                        "elapsed": 23
                    },
                    "team": {
                        "id": 42,
                        "name": "Arsenal FC"
                    },
                    "player": {
                        "id": 2,
                        "name": "Goal Scorer"
                    },
                    "type": "Goal",
                    "detail": "Normal Goal"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.get_events(fixture_id=123)
        
        # Assert results
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/fixtures/events",
            headers=self.client.headers,
            params={'fixture': 123},
            timeout=30
        )
        self.assertEqual(result["response"][0]["type"], "Goal")
        
    @patch('scores.api_client.requests.get')
    def test_get_statistics(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": [
                {
                    "team": {
                        "id": 42,
                        "name": "Arsenal FC"
                    },
                    "statistics": [
                        {
                            "type": "Shots on Goal",
                            "value": 5
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.get_statistics(fixture_id=123)
        
        # Assert results
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/fixtures/statistics",
            headers=self.client.headers,
            params={'fixture': 123},
            timeout=30
        )
        self.assertEqual(result["response"][0]["statistics"][0]["type"], "Shots on Goal")
        
    @patch('scores.api_client.requests.get')
    def test_request_error_handling(self, mock_get):
        # Setup mock to raise exception
        mock_get.side_effect = Exception("API Error")
        
        # Call the method and verify it handles the error gracefully
        result = self.client.get_leagues()
        
        # Assert result is None due to error
        self.assertIsNone(result)


class ManagementCommandsTestCase(TestCase):
    
    def setUp(self):
        # Create test data
        self.league = League.objects.create(id="39", name="Premier League", country="England")
        self.home_team = Team.objects.create(id="42", name="Arsenal FC", league=self.league)
        self.away_team = Team.objects.create(id="51", name="Brighton", league=self.league)
        self.match = Match.objects.create(
            id="123",
            home_team=self.home_team,
            away_team=self.away_team,
            match_date="2025-05-28T14:00:00+00:00",
            league=self.league,
            stadium="Emirates Stadium"
        )
    
    @patch('scores.management.commands.fetch_match_lineups.APIFootballClient')
    def test_fetch_match_lineups_command(self, mock_client_class):
        # Setup mock client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock the get_lineups method to return test data
        mock_client.get_lineups.return_value = {
            "response": [
                {
                    "team": {
                        "id": "42",
                        "name": "Arsenal FC"
                    },
                    "formation": "4-3-3",
                    "startXI": [
                        {
                            "player": {
                                "id": "1",
                                "name": "Test Player",
                                "pos": "G"
                            }
                        }
                    ],
                    "substitutes": []
                }
            ]
        }
        
        # Import here to avoid early AppConfig initialization
        from django.core.management import call_command
        
        # Call the command with our test match ID
        call_command('fetch_match_lineups', match_id="123")
        
        # Verify the mock was called with the expected parameters
        mock_client.get_lineups.assert_called_once_with("123")
        
        # Verify a player was created
        self.assertTrue(Player.objects.filter(name="Test Player").exists())
    
    @patch('scores.management.commands.fetch_match_events.APIFootballClient')
    def test_fetch_match_events_command(self, mock_client_class):
        # Setup mock client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock the get_events method to return test data
        mock_client.get_events.return_value = {
            "response": [
                {
                    "time": {
                        "elapsed": 23
                    },
                    "team": {
                        "id": "42",
                        "name": "Arsenal FC"
                    },
                    "player": {
                        "id": "1",
                        "name": "Test Player"
                    },
                    "type": "Goal",
                    "detail": "Normal Goal"
                }
            ]
        }
        
        # Create test player
        player = Player.objects.create(id="1", name="Test Player", team=self.home_team, position="FW")
        
        # Import here to avoid early AppConfig initialization
        from django.core.management import call_command
        
        # Call the command with our test match ID
        call_command('fetch_match_events', match_id="123")
        
        # Verify the mock was called with the expected parameters
        mock_client.get_events.assert_called_once_with("123")
        
        # Verify an event was created
        from scores.models import Event
        self.assertTrue(Event.objects.filter(match=self.match, event_type="GOAL").exists())