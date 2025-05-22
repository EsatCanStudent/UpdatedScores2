# API-FOOTBALL Quick Start Guide

This guide will help you quickly set up and start using the API-FOOTBALL integration in UpdatedScores.

## 1. Prerequisites

- An active API-FOOTBALL API key
- Django project with UpdatedScores installed
- Python 3.8 or higher

## 2. Environment Setup

Add the following environment variables to your project:

```
API_FOOTBALL_KEY=your_api_key_here
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
```

You can set these in your `.env` file or directly in your system environment.

## 3. Verify API Connection

Test your API connection by running:

```python
python manage.py shell

# In the shell:
from scores.api_client import APIFootballClient
client = APIFootballClient()
leagues = client.get_leagues()
print(f"Retrieved {len(leagues.get('response', []))} leagues")
```

If successful, you should see the leagues count displayed.

## 4. Fetch Initial Data

Run the following commands to populate your database with football data:

```bash
# Fetch league matches (last 14 days and next 14 days)
python manage.py fetch_api_football_matches

# Fetch lineup data for recent and upcoming matches
python manage.py fetch_match_lineups

# Fetch match statistics for completed matches
python manage.py fetch_match_statistics

# Fetch match events
python manage.py fetch_match_events

# Fetch match previews for upcoming matches
python manage.py fetch_match_previews
```

## 5. Set Up Automated Updates

For continuous updates, use the master command:

```bash
# Run once
python manage.py schedule_football_updates

# Run in continuous mode (updates every 5 minutes)
python manage.py schedule_football_updates --continuous --interval 300
```

For production environments, set up a scheduled task using cron (Linux) or Task Scheduler (Windows).

## 6. Verify Data

Check that data has been properly imported:

```python
python manage.py shell

# In the shell:
from scores.models import Match
today_matches = Match.objects.filter(match_date__date=datetime.now().date())
print(f"Today's matches: {today_matches.count()}")

# List today's matches
for match in today_matches:
    print(f"{match.home_team} vs {match.away_team} - {match.match_date.strftime('%H:%M')}")
```

## 7. Run Tests

Verify the integration is working with the test suite:

```bash
python manage.py test scores.tests.test_api_football
```

## 8. Common Issues

1. **API Key Issues**: If you see 401 errors, verify your API key is correct and active.
2. **Rate Limiting**: If you're hitting rate limits, increase the intervals between API calls.
3. **Empty Results**: Some leagues may not have current matches; try different leagues or seasons.

## 9. Next Steps

- Explore the `scores.api_client.APIFootballClient` class to see all available methods
- Check the full documentation in `docs/api_football_integration.md`
- Review model structures to understand how data is stored