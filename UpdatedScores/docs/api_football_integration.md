# API-FOOTBALL Integration Guide

This document provides a comprehensive guide to the API-FOOTBALL integration with the UpdatedScores application.

## Overview

API-FOOTBALL is a premium sports data provider offering football data including:

- Fixtures & Results
- Live Scores
- Lineups
- Player Statistics
- Match Events
- Team Statistics
- Head-to-head Records
- Predictions

Our integration fetches and processes this data to provide users with rich, up-to-date football information.

## Environment Setup

To use the API-FOOTBALL integration, you must set the following environment variables:

```
API_FOOTBALL_KEY=your_api_key_here
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
```

You can obtain an API key by signing up at [api-football.com](https://api-football.com/).

## Available Management Commands

The following management commands are provided to fetch data from API-FOOTBALL:

### 1. fetch_api_football_matches

Fetches upcoming and past match fixtures.

```bash
python manage.py fetch_api_football_matches [--season YEAR] [--last DAYS] [--next DAYS] [--date DATE] [--no-delete]
```

Options:
- `--season`: The season to fetch matches for (e.g., 2025)
- `--last`: Number of days in the past to fetch matches for (default: 14)
- `--next`: Number of days in the future to fetch matches for (default: 14)
- `--date`: Fetch matches for a specific date (YYYY-MM-DD format)
- `--no-delete`: Don't delete existing match data before fetching new data

### 2. fetch_match_lineups

Fetches lineup data for upcoming or recent matches.

```bash
python manage.py fetch_match_lineups [--days DAYS] [--match-id MATCH_ID]
```

Options:
- `--days`: Fetch lineups for matches within this many days before and after today (default: 2)
- `--match-id`: Fetch lineup for a specific match ID

### 3. fetch_match_statistics

Fetches match statistics for completed matches.

```bash
python manage.py fetch_match_statistics [--days DAYS] [--match-id MATCH_ID]
```

Options:
- `--days`: Fetch statistics for matches within this many days before and after today (default: 2)
- `--match-id`: Fetch statistics for a specific match ID

### 4. fetch_match_events

Fetches match events (goals, cards, substitutions) for matches.

```bash
python manage.py fetch_match_events [--days DAYS] [--match-id MATCH_ID]
```

Options:
- `--days`: Fetch events for matches within this many days before and after today (default: 2)
- `--match-id`: Fetch events for a specific match ID

### 5. fetch_match_previews

Fetches match previews including head-to-head statistics and predictions.

```bash
python manage.py fetch_match_previews [--days DAYS] [--match-id MATCH_ID]
```

Options:
- `--days`: Fetch previews for matches within this many days after today (default: 2)
- `--match-id`: Fetch preview for a specific match ID

### 6. schedule_football_updates

Master command that runs all of the above commands in a logical sequence.

```bash
python manage.py schedule_football_updates [--continuous] [--interval SECONDS]
```

Options:
- `--continuous`: Run in continuous mode with specified intervals
- `--interval`: Interval in seconds between update checks in continuous mode (default: 300)

## Automatic Scheduled Updates

For production environments, it's recommended to configure a scheduled task (cron job) to run the update commands. Here's an example setup for a Linux environment:

```bash
# Run updates every 5 minutes
*/5 * * * * cd /path/to/project && python manage.py schedule_football_updates
```

For Windows environments, you can use Task Scheduler to set up a similar recurring task.

## API Client Usage

The `APIFootballClient` class provides a Python interface to interact with the API-FOOTBALL endpoints. Here's a simple example of how to use it:

```python
from scores.api_client import APIFootballClient

# Create client instance
client = APIFootballClient()

# Get Premier League fixtures for 2025 season
fixtures = client.get_fixtures(league_id=39, season=2025)

# Get lineup for a specific match
lineup = client.get_lineups(fixture_id=123456)

# Get events for a specific match
events = client.get_events(fixture_id=123456)
```

## Data Models

The API-FOOTBALL data is stored in the following models:

- `League`: League information
- `Team`: Team information
- `Player`: Player information
- `Match`: Match fixtures and results
- `Event`: Match events (goals, cards, substitutions)
- `MatchPreview`: Pre-match statistics and predictions
- `MatchAnalysis`: Post-match statistics and analysis

## Rate Limiting Considerations

API-FOOTBALL imposes rate limits on API requests:
- Free tier: 100 requests/day
- Pro tier: 1000 requests/minute

The integration is designed to be efficient with API calls, but be mindful of these limits when running commands frequently.

## Troubleshooting

If you encounter issues with the API-FOOTBALL integration:

1. Verify your API key is correct and active
2. Check that you have sufficient API request quota
3. Ensure your network allows outbound HTTPS connections
4. Review command logs for specific error messages

For more information on the API-FOOTBALL endpoints and responses, refer to their [official documentation](https://www.api-football.com/documentation-v3).

## Testing

The integration includes comprehensive tests to verify API client functionality and data processing:

```bash
python manage.py test scores.tests.test_api_football
```

## Support

If you need assistance with the API-FOOTBALL integration, please contact the development team at support@updatedscores.com.