# Match Preview and Analysis Feature

This document explains how to use the match preview and analysis features of UpdatedScores.

## Overview

The system can automatically generate:
1. **Match Previews** - Created for upcoming matches with:
   - Team form data (last 5 matches)
   - Head-to-head statistics
   - Predicted outcome
   - Key players to watch

2. **Match Analysis** - Created for completed matches with:
   - Possession statistics
   - Shots, corners, and other match data
   - Key moments of the match
   - Post-match commentary
   - Player ratings

## How It Works

### Automatic Generation

Previews and analyses are generated automatically:
- Match previews are created every day at 8:00 AM
- Match analyses are updated every 6 hours
- Data is automatically populated based on team history and match events

### Manual Generation

You can also manually generate previews and analyses:

```bash
# Generate previews for upcoming matches
python manage.py generate_match_analysis --preview

# Generate analyses for completed matches in the last day
python manage.py generate_match_analysis --analysis

# Generate for both
python manage.py generate_match_analysis

# Generate for a specific match
python manage.py generate_match_analysis --match_id=123456

# Generate for matches from the last 3 days
python manage.py generate_match_analysis --days=3
```

## Admin Panel Usage

To manage previews and analyses in the admin panel:

1. Go to "MatchPreview" or "MatchAnalysis" sections
2. Select an existing record or create a new one
3. Edit the content fields as needed
4. You can modify:
   - Preview text and predictions
   - Key player information
   - Statistical data (possession, shots, etc.)
   - Analysis commentary

## Frontend View

The match detail page now has 4 tabs:
1. **Match Events** - Shows goals, cards, and other match events
2. **Preview** - Shows pre-match information (available before and during the match)
3. **Analysis** - Shows post-match analysis (available after the match)
4. **History** - Shows previous encounters and team form

## Development Notes

- The system uses actual match data where available and supplements with generated content
- Preview and analysis data is stored in JSON fields for flexibility
- Forms for adding/editing data include rich text areas for detailed content
