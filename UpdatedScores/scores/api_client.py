import os
import requests
from datetime import datetime, timedelta

API_KEY = os.getenv("THESPORTSDB_API_KEY")
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/"

def fetch_leagues():
    url = BASE_URL + "all_leagues.php"
    return requests.get(url).json()

def fetch_events_by_league(league_id):
    url = BASE_URL + f"eventsnextleague.php?id={league_id}"
    return requests.get(url).json()

class TheSportsDBAPI:
    """TheSportsDB API ile iletişim kuran yardımcı sınıf"""
    
    def __init__(self):
        self.base_url = os.environ.get('THESPORTSDB_BASE_URL', 'https://www.thesportsdb.com/api/v1/json/1')
        self.api_key = os.environ.get('THESPORTSDB_API_KEY', '1')  # Ücretsiz API key
    
    def get_leagues(self):
        """Mevcut futbol liglerini getir"""
        url = f"{self.base_url}/all_leagues.php?s=Soccer"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('leagues', [])
        return []
    
    def get_teams_by_league(self, league_id):
        """Belirli bir ligteki takımları getir"""
        url = f"{self.base_url}/lookup_all_teams.php?id={league_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('teams', [])
        return []
    
    def get_team_players(self, team_id):
        """Belirli bir takıma ait oyuncuları getir"""
        url = f"{self.base_url}/lookup_all_players.php?id={team_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('player', [])
        return []
    
    def get_events_by_league_and_date(self, league_id, date_str=None):
        """Belirli bir lig ve tarihteki maçları getir"""
        # Tarih belirtilmezse bugünün tarihini kullan
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/eventsday.php?d={date_str}&l={league_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('events', [])
        return []
    
    def get_league_next_events(self, league_id, days=7):
        """Bir lig için gelecek maçları getir"""
        url = f"{self.base_url}/eventsnextleague.php?id={league_id}"
        response = requests.get(url)
        if response.status_code == 200:
            events = response.json().get('events', [])
            if events:
                # Bugünden itibaren belirli gün içindeki maçları filtrele
                today = datetime.now().date()
                filtered_events = []
                for event in events:
                    if 'dateEvent' in event:
                        event_date = datetime.strptime(event['dateEvent'], '%Y-%m-%d').date()
                        if event_date <= today + timedelta(days=days):
                            filtered_events.append(event)
                return filtered_events
        return []
    
    def get_event_details(self, event_id):
        """Belirli bir etkinliğin detaylarını getir"""
        url = f"{self.base_url}/lookupevent.php?id={event_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('events', [])
        return []

class APIFootballClient:
    def __init__(self):
        self.api_key = os.environ.get('API_FOOTBALL_KEY')
        self.base_url = os.environ.get('API_FOOTBALL_BASE_URL', 'https://v3.football.api-sports.io')
        self.headers = {
            'x-apisports-key': self.api_key
        }
        
    def _make_request(self, endpoint, params=None):
        """
        Helper method to make API requests with error handling
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {str(e)}")
            return None

    def get_leagues(self, country=None, season=None):
        """
        Get available leagues
        
        Args:
            country (str, optional): Filter leagues by country
            season (int, optional): Filter leagues by season
        
        Returns:
            dict: API response with leagues information
        """
        params = {}
        if country:
            params['country'] = country
        if season:
            params['season'] = season
            
        return self._make_request("leagues", params)
    
    def get_teams(self, league_id=None, season=None, team_id=None):
        """
        Get teams information
        
        Args:
            league_id (str, optional): Filter teams by league ID
            season (int, optional): Filter teams by season
            team_id (str, optional): Get specific team by ID
            
        Returns:
            dict: API response with teams information
        """
        params = {}
        if league_id:
            params['league'] = league_id
        if season:
            params['season'] = season
        if team_id:
            params['id'] = team_id
            
        return self._make_request("teams", params)
    
    def get_fixtures(self, league_id=None, team_id=None, date=None, season=None, 
                    next=None, last=None, from_date=None, to_date=None, fixture_id=None,
                    status=None, round=None):
        """
        Get fixtures (matches) with various filtering options
        
        Args:
            league_id (str, optional): Filter fixtures by league ID
            team_id (str, optional): Filter fixtures by team ID
            date (str, optional): Filter fixtures by date (YYYY-MM-DD format)
            season (int, optional): Filter fixtures by season
            next (int, optional): Get the next X fixtures
            last (int, optional): Get the last X fixtures
            from_date (str, optional): From date (YYYY-MM-DD format)
            to_date (str, optional): To date (YYYY-MM-DD format)
            fixture_id (str, optional): Get specific fixture by ID
            status (str, optional): Filter fixtures by status
            round (str, optional): Filter fixtures by round
            
        Returns:
            dict: API response with fixtures information
        """
        params = {}
        if league_id:
            params['league'] = league_id
        if team_id:
            params['team'] = team_id
        if date:
            params['date'] = date
        if season:
            params['season'] = season
        if next:
            params['next'] = next
        if last:
            params['last'] = last
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        if fixture_id:
            params['id'] = fixture_id
        if status:
            params['status'] = status
        if round:
            params['round'] = round
            
        return self._make_request("fixtures", params)
    
    def get_lineups(self, fixture_id):
        """
        Get lineups for a specific fixture
        
        Args:
            fixture_id (str): The fixture ID
            
        Returns:
            dict: API response with lineup information
        """
        params = {'fixture': fixture_id}
        return self._make_request("fixtures/lineups", params)
    
    def get_events(self, fixture_id):
        """
        Get events for a specific fixture (goals, cards, substitutions)
        
        Args:
            fixture_id (str): The fixture ID
            
        Returns:
            dict: API response with events information
        """
        params = {'fixture': fixture_id}
        return self._make_request("fixtures/events", params)
    
    def get_statistics(self, fixture_id, team_id=None):
        """
        Get statistics for a specific fixture
        
        Args:
            fixture_id (str): The fixture ID
            team_id (str, optional): Filter statistics by team ID
            
        Returns:
            dict: API response with statistics information
        """
        params = {'fixture': fixture_id}
        if team_id:
            params['team'] = team_id
            
        return self._make_request("fixtures/statistics", params)
    
    def get_player_statistics(self, fixture_id, team_id=None, player_id=None):
        """
        Get player statistics for a specific fixture
        
        Args:
            fixture_id (str): The fixture ID
            team_id (str, optional): Filter player statistics by team ID
            player_id (str, optional): Filter by player ID
            
        Returns:
            dict: API response with player statistics information
        """
        params = {'fixture': fixture_id}
        if team_id:
            params['team'] = team_id
        if player_id:
            params['player'] = player_id
            
        return self._make_request("fixtures/players", params)
    
    def get_predictions(self, fixture_id):
        """
        Get predictions for a specific fixture
        
        Args:
            fixture_id (str): The fixture ID
            
        Returns:
            dict: API response with predictions information
        """
        params = {'fixture': fixture_id}
        return self._make_request("predictions", params)
    
    def get_players(self, team_id, season=None, player_id=None):
        """
        Get players for a specific team and season
        
        Args:
            team_id (str): The team ID
            season (int, optional): The season
            player_id (str, optional): Filter by player ID
            
        Returns:
            dict: API response with player information
        """
        params = {'team': team_id}
        if season:
            params['season'] = season
        if player_id:
            params['id'] = player_id
            
        return self._make_request("players", params)

# Test amaçlı fonksiyon
if __name__ == "__main__":
    client = APIFootballClient()
    leagues = client.get_leagues()
    print(leagues)
