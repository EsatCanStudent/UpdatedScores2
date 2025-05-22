# Import necessary modules
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from .models import Match, MatchPreview, MatchAnalysis, Event, Team, Player
from .performance import timing_decorator, caching_decorator, query_debugger
from .cache_utils import CacheManager

# Enhanced view function for match detail with optimizations
@timing_decorator
@query_debugger
def enhanced_match_detail(request, match_id):
    # Check if we have the match data in cache
    cached_context = CacheManager.get_match_data(match_id)
    if cached_context and not request.GET.get('bypass_cache'):
        return render(request, 'scores/match_detail.html', cached_context)
    
    # Get match with related team data in a single query to avoid N+1 queries
    match = get_object_or_404(
        Match.objects.select_related('home_team', 'away_team', 'league'),
        pk=match_id
    )
    
    # Get all events for the match in a single query
    events = Event.objects.filter(match=match).select_related('player', 'player__team').order_by('minute')
    
    # Try to get match preview and analysis - use select_related to avoid extra queries
    try:
        preview = MatchPreview.objects.get(match=match)
    except MatchPreview.DoesNotExist:
        preview = None
        
    try:
        analysis = MatchAnalysis.objects.get(match=match)
    except MatchAnalysis.DoesNotExist:
        analysis = None
    
    # Get the last matches with efficient querying
    def get_last_matches(team, match_date):
        """Get last 5 matches for a team with efficient querying"""
        cache_key = f"last_matches_{team.id}_{match_date.date()}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        last_matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            match_date__lt=match_date,
            score__isnull=False
        ).select_related('home_team', 'away_team').order_by('-match_date')[:5]
        
        cache.set(cache_key, last_matches, 3600)  # Cache for 1 hour
        return last_matches
    
    # Get last 5 match results for each team
    home_team_last_matches = get_last_matches(match.home_team, match.match_date)
    away_team_last_matches = get_last_matches(match.away_team, match.match_date)
    
    # Head-to-head matches with efficient querying
    head_to_head_cache_key = f"h2h_{match.home_team.id}_{match.away_team.id}_{match.match_date.date()}"
    head_to_head = cache.get(head_to_head_cache_key)
    
    if not head_to_head:
        head_to_head = Match.objects.filter(
            Q(home_team=match.home_team, away_team=match.away_team) | 
            Q(home_team=match.away_team, away_team=match.home_team),
            match_date__lt=match.match_date,
            score__isnull=False
        ).select_related('home_team', 'away_team').order_by('-match_date')[:5]
        
        cache.set(head_to_head_cache_key, head_to_head, 3600)  # Cache for 1 hour
    
    # Match status (live, completed, upcoming)
    current_time = timezone.now()
    is_live = match.match_date <= current_time <= (match.match_date + timedelta(hours=2))
    is_completed = match.score is not None
    
    # Check if match stats are already cached
    match_stats = CacheManager.get_match_stats(match_id)
    
    if not match_stats and analysis:
        match_stats = {}
        # Process possession
        if analysis.possession:
            try:
                possession_parts = analysis.possession.split('-')
                match_stats['home_possession'] = possession_parts[0].replace('%', '').strip()
                match_stats['away_possession'] = possession_parts[1].replace('%', '').strip()
            except (IndexError, ValueError):
                match_stats['home_possession'] = match_stats['away_possession'] = "50"
        else:
            match_stats['home_possession'] = match_stats['away_possession'] = "50"
            
        # Process shots
        if analysis.shots:
            try:
                shots_parts = analysis.shots.split('-')
                match_stats['home_shots'] = int(shots_parts[0].strip())
                match_stats['away_shots'] = int(shots_parts[1].strip())
                match_stats['total_shots'] = match_stats['home_shots'] + match_stats['away_shots']
            except (IndexError, ValueError):
                match_stats['home_shots'] = match_stats['away_shots'] = match_stats['total_shots'] = 0
        else:
            match_stats['home_shots'] = match_stats['away_shots'] = match_stats['total_shots'] = 0
            
        # Process shots on target
        if analysis.shots_on_target:
            try:
                shots_on_target_parts = analysis.shots_on_target.split('-')
                match_stats['home_shots_on_target'] = int(shots_on_target_parts[0].strip())
                match_stats['away_shots_on_target'] = int(shots_on_target_parts[1].strip())
                match_stats['total_shots_on_target'] = match_stats['home_shots_on_target'] + match_stats['away_shots_on_target']
            except (IndexError, ValueError):
                match_stats['home_shots_on_target'] = match_stats['away_shots_on_target'] = match_stats['total_shots_on_target'] = 0
        else:
            match_stats['home_shots_on_target'] = match_stats['away_shots_on_target'] = match_stats['total_shots_on_target'] = 0
            
        # Process corners
        if analysis.corners:
            try:
                corners_parts = analysis.corners.split('-')
                match_stats['home_corners'] = int(corners_parts[0].strip())
                match_stats['away_corners'] = int(corners_parts[1].strip())
                match_stats['total_corners'] = match_stats['home_corners'] + match_stats['away_corners']
            except (IndexError, ValueError):
                match_stats['home_corners'] = match_stats['away_corners'] = match_stats['total_corners'] = 0
        else:
            match_stats['home_corners'] = match_stats['away_corners'] = match_stats['total_corners'] = 0
            
        # Process fouls
        if analysis.fouls:
            try:
                fouls_parts = analysis.fouls.split('-')
                match_stats['home_fouls'] = int(fouls_parts[0].strip())
                match_stats['away_fouls'] = int(fouls_parts[1].strip())
                match_stats['total_fouls'] = match_stats['home_fouls'] + match_stats['away_fouls']
            except (IndexError, ValueError):
                match_stats['home_fouls'] = match_stats['away_fouls'] = match_stats['total_fouls'] = 0
        else:
            match_stats['home_fouls'] = match_stats['away_fouls'] = match_stats['total_fouls'] = 0
        
        # Process cards
        if analysis.yellows:
            try:
                yellows_parts = analysis.yellows.split('-')
                match_stats['home_yellows'] = int(yellows_parts[0].strip())
                match_stats['away_yellows'] = int(yellows_parts[1].strip())
                match_stats['total_yellows'] = match_stats['home_yellows'] + match_stats['away_yellows']
            except (IndexError, ValueError):
                match_stats['home_yellows'] = match_stats['away_yellows'] = match_stats['total_yellows'] = 0
        else:
            match_stats['home_yellows'] = match_stats['away_yellows'] = match_stats['total_yellows'] = 0
            
        if analysis.reds:
            try:
                reds_parts = analysis.reds.split('-')
                match_stats['home_reds'] = int(reds_parts[0].strip())
                match_stats['away_reds'] = int(reds_parts[1].strip())
                match_stats['total_reds'] = match_stats['home_reds'] + match_stats['away_reds']
            except (IndexError, ValueError):
                match_stats['home_reds'] = match_stats['away_reds'] = match_stats['total_reds'] = 0
        else:
            match_stats['home_reds'] = match_stats['away_reds'] = match_stats['total_reds'] = 0
            
        # Process head-to-head stats
        if preview and preview.head_to_head:
            try:
                h2h = preview.head_to_head
                match_stats['home_wins'] = h2h.get('home_wins', 0)
                match_stats['away_wins'] = h2h.get('away_wins', 0)
                match_stats['draws'] = h2h.get('draws', 0)
                total_h2h = match_stats['home_wins'] + match_stats['away_wins'] + match_stats['draws']
                
                if total_h2h > 0:
                    match_stats['home_win_percentage'] = int((match_stats['home_wins'] / total_h2h) * 100)
                    match_stats['away_win_percentage'] = int((match_stats['away_wins'] / total_h2h) * 100)
                    match_stats['draw_percentage'] = int((match_stats['draws'] / total_h2h) * 100)
                else:
                    match_stats['home_win_percentage'] = match_stats['away_win_percentage'] = match_stats['draw_percentage'] = 33
            except (TypeError, ZeroDivisionError):
                match_stats['home_wins'] = match_stats['away_wins'] = match_stats['draws'] = 0
                match_stats['home_win_percentage'] = match_stats['away_win_percentage'] = match_stats['draw_percentage'] = 33
        
        # Pre-process player ratings for faster template rendering
        if analysis and analysis.player_ratings:
            try:
                # Initialize player ratings structure
                match_stats['player_ratings'] = {
                    'home_team': [],
                    'away_team': []
                }
                
                # Process home team player ratings
                if 'home_team' in analysis.player_ratings:
                    for player, rating in analysis.player_ratings.get('home_team', {}).items():
                        rating_class = 'rating-high' if float(rating) >= 8 else 'rating-mid' if float(rating) >= 6 else 'rating-low'
                        match_stats['player_ratings']['home_team'].append({
                            'name': player,
                            'rating': rating,
                            'rating_class': rating_class
                        })
                
                # Process away team player ratings
                if 'away_team' in analysis.player_ratings:
                    for player, rating in analysis.player_ratings.get('away_team', {}).items():
                        rating_class = 'rating-high' if float(rating) >= 8 else 'rating-mid' if float(rating) >= 6 else 'rating-low'
                        match_stats['player_ratings']['away_team'].append({
                            'name': player,
                            'rating': rating,
                            'rating_class': rating_class
                        })
            except (TypeError, ValueError, KeyError):
                # Fallback in case of errors with the player_ratings data
                match_stats['player_ratings'] = {'home_team': [], 'away_team': []}
        
        # Cache the match stats
        CacheManager.cache_match_stats(match_id, match_stats)
    
    # Check if we have timeline events in cache
    timeline_events = CacheManager.get_timeline_events(match_id)
    if not timeline_events:
        # Prepare timeline event data for JavaScript
        timeline_events = []
        for event in events:
            if event.event_type in ('GOAL', 'RED', 'YELLOW'):
                # We've already loaded the player and team with select_related
                team = 'home' if event.player and event.player.team == match.home_team else 'away'
                timeline_events.append({
                    'minute': event.minute,
                    'type': event.event_type.lower(),  # Lowercase for CSS class consistency
                    'team': team,
                    'player': event.player.name if event.player else 'Unknown',
                    'description': event.description,
                    'position': int(event.minute) / 90 * 100  # Position as percentage for timeline
                })
        
        # Cache the timeline events
        CacheManager.cache_timeline_events(match_id, timeline_events)
    
    context = {
        'match': match, 
        'events': events,
        'preview': preview,
        'analysis': analysis,
        'home_team_last_matches': home_team_last_matches,
        'away_team_last_matches': away_team_last_matches,
        'head_to_head': head_to_head,
        'current_time': current_time,
        'is_live': is_live,
        'is_completed': is_completed,
        'match_stats': match_stats,
        'timeline_events': timeline_events
    }
    
    # Cache the entire context for future requests
    CacheManager.cache_match_data(match_id, context)
    
    return render(request, 'scores/match_detail.html', context)
