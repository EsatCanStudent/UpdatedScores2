# API-FOOTBALL Integration for UpdatedScores

This module integrates the API-FOOTBALL data service with the UpdatedScores Django application.

## Setup

1. **Set environment variables:**
   ```
   API_FOOTBALL_KEY=your_api_key_here
   API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
   ```

2. **Run migrations:**
   ```
   python manage.py migrate
   ```

## Available Commands

- **fetch_api_football_matches**: Fetch match fixtures and results
  ```
  python manage.py fetch_api_football_matches --last 14 --next 14
  ```

- **fetch_match_lineups**: Fetch team lineups
  ```
  python manage.py fetch_match_lineups --days 2
  ```

- **fetch_match_events**: Fetch match events (goals, cards, substitutions)
  ```
  python manage.py fetch_match_events --days 1
  ```

- **fetch_match_statistics**: Fetch detailed match statistics
  ```
  python manage.py fetch_match_statistics --days 2
  ```

- **fetch_match_previews**: Fetch match previews and predictions
  ```
  python manage.py fetch_match_previews --days 3
  ```

- **schedule_football_updates**: Run all update commands in sequence
  ```
  python manage.py schedule_football_updates [--continuous] [--interval 300]
  ```

## Scheduling

Use the provided PowerShell script to set up automatic updates:
```
.\setup_scheduler.ps1
```

This creates a scheduled task that runs updates every 30 minutes.

## Models

The integration uses these models:
- `League`: Competition information
- `Team`: Team details
- `Player`: Player information
- `Match`: Match fixtures and results
- `Event`: Match events (goals, cards, etc.)
- `Lineup`/`LineupPlayer`: Team lineups
- `MatchPreview`: Pre-match statistics and predictions
- `MatchAnalysis`: Post-match statistics

## API Client

The `APIFootballClient` class in `api_client.py` provides methods for interacting with all API-FOOTBALL endpoints.

## Documentation

For more detailed documentation, see:
- `docs/api_football_integration.md`: Complete integration guide
- `docs/api_football_quickstart.md`: Quick start guide

## Testing

Run the test suite to verify integration:
```
python manage.py test scores.tests.test_api_football
```