from django.shortcuts import render, redirect, get_object_or_404
from .models import League, Team, Player, Match, Event, Profile
from django.db.models import Q
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib import messages
from django.core.management import call_command
from django.contrib.auth import login
from .forms import UserRegisterForm, ProfileForm
from django.contrib.auth.decorators import login_required
from rest_framework import routers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import LeagueSerializer, TeamSerializer, MatchSerializer, ProfileSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

def index(request):
    # Bugün ve yakın günlerdeki maçları göster
    today = timezone.now().date()
    
    # Veri yok mu diye kontrol edelim
    if Match.objects.count() == 0:
        try:
            # Yönetici hesabıyla giriş yapmış kullanıcılar için API'den veri çekelim
            if request.user.is_superuser:
                call_command('fetch_api_football_matches')
                messages.success(request, "Maç verileri API'den başarıyla çekildi!")
            else:
                messages.warning(request, "Veritabanında henüz maç verisi bulunmuyor. Yönetici, 'Verileri Güncelle' işlemini yapmalıdır.")
        except Exception as e:
            messages.error(request, f"API'den veri çekilemedi: {e}")
    
    # Son 3 gün ve önümüzdeki 7 günü göster
    start_date = today - timedelta(days=3)
    end_date = today + timedelta(days=7)
    
    # Tarihlere göre maç filtresi
    matches = Match.objects.filter(
        match_date__date__gte=start_date,
        match_date__date__lte=end_date
    ).order_by('match_date')
    
    # Ligler
    leagues = League.objects.all()
    
    # Bugünkü maçlar (saat sırasına göre)
    todays_matches = Match.objects.filter(match_date__date=today).order_by('match_date')
    
    # Bugün kaç maç var görelim ve bilgilendirme mesajı gösterelim
    match_count = todays_matches.count()
    if match_count == 0 and request.user.is_superuser:
        messages.info(request, f"Bugün ({today}) için hiç maç bulunamadı. 'Verileri Güncelle' butonu ile güncel maçları çekebilirsiniz.")
    
    # Geçmişteki maçlar (son 3 gün - en yeni maçlar üstte)
    past_matches = Match.objects.filter(
        match_date__date__lt=today,
        match_date__date__gte=start_date
    ).order_by('-match_date')
    
    # Gelecekteki maçlar (önümüzdeki 7 gün)
    future_matches = Match.objects.filter(
        match_date__date__gt=today,
        match_date__date__lte=end_date
    ).order_by('match_date')
    
    # Takım, oyuncu ve maç sayıları
    teams_count = Team.objects.count()
    players_count = Player.objects.count()
    matches_count = Match.objects.count()
    
    # Events (son 50 olay)
    recent_events = Event.objects.select_related('match', 'player').order_by('-match__match_date', '-minute')[:50]

    # Favori takımların bugünkü ve yaklaşan maçları (giriş yaptıysa)
    fav_today_matches = []
    fav_next_matches = []
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            favorite_teams = profile.favorite_teams.all()
            if favorite_teams.exists():
                # Bugünkü maçlar (önce favori takımların maçları, sonra diğerleri)
                fav_today_matches = Match.objects.filter(
                    Q(home_team__in=favorite_teams) | Q(away_team__in=favorite_teams),
                    match_date__date=today
                ).order_by('match_date')
                # Diğer bugünkü maçlar (favori takımlar hariç)
                other_today_matches = todays_matches.exclude(
                    Q(home_team__in=favorite_teams) | Q(away_team__in=favorite_teams)
                )
                # Eğer bugün maç yoksa, en yakın gelecek maçlar
                if not fav_today_matches:
                    fav_next_matches = Match.objects.filter(
                        Q(home_team__in=favorite_teams) | Q(away_team__in=favorite_teams),
                        match_date__date__gt=today
                    ).order_by('match_date')[:5]
            else:
                fav_today_matches = []
                other_today_matches = todays_matches
        except Profile.DoesNotExist:
            fav_today_matches = []
            other_today_matches = todays_matches
    else:
        fav_today_matches = []
        other_today_matches = todays_matches

    context = {
        'leagues': leagues,
        'todays_matches': todays_matches,
        'other_today_matches': other_today_matches,
        'past_matches': past_matches,
        'future_matches': future_matches,
        'teams_count': teams_count,
        'players_count': players_count,
        'matches_count': matches_count,
        'recent_events': recent_events,
        'today': today,
        'fav_today_matches': fav_today_matches,
        'fav_next_matches': fav_next_matches,
    }
    
    return render(request, 'scores/index.html', context)

def refresh_data(request):
    """API'den en son verileri çeker"""
    try:
        # Sadece admin kullanıcıların veri yenilemesine izin ver
        if not request.user.is_superuser:
            messages.error(request, "Bu işlemi gerçekleştirmek için admin yetkisi gereklidir.")
            return redirect('scores:index')
        
        # Veri türünü belirle
        data_type = request.GET.get('type', 'all')
        
        if data_type == 'matches':
            # Sadece maç verilerini güncelle
            call_command('fetch_api_football_matches')
            messages.success(request, "Maç verileri başarıyla güncellendi!")
        elif data_type == 'leagues':
            # Sadece lig verilerini güncelle
            call_command('fetch_api_football_leagues')
            messages.success(request, "Lig verileri başarıyla güncellendi!")
        elif data_type == 'teams':
            # Sadece takım verilerini güncelle
            call_command('fetch_api_football_teams')
            messages.success(request, "Takım verileri başarıyla güncellendi!")
        else:
            # Tüm verileri güncelle
            call_command('fetch_sports_data', full=True)
            messages.success(request, "Tüm veriler başarıyla güncellendi!")
    except Exception as e:
        messages.error(request, f"Veriler güncellenirken bir hata oluştu: {str(e)}")
    
    # Geri dönülecek URL'yi belirle
    next_url = request.GET.get('next', 'scores:index')
    return redirect(next_url)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect('scores:edit_profile')
    else:
        form = UserRegisterForm()
    return render(request, 'scores/register.html', {'form': form})

@login_required
def edit_profile(request):
    # Get or create the profile
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # If profile was just created, set default values
    if created:
        profile.notify_goals = True
        profile.notify_red_cards = True
        profile.notify_match_start = True
        profile.save()
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil başarıyla güncellendi.")
            return redirect('scores:edit_profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'scores/edit_profile.html', {'form': form})

def match_detail(request, match_id):
    match = Match.objects.select_related('home_team', 'away_team', 'league').get(id=match_id)
    events = Event.objects.filter(match=match).select_related('player').order_by('minute')
    
    # Güncel tarih-saat bilgisini context'e ekle (maçın canlı olup olmadığını kontrol etmek için)
    now = timezone.now()
    
    # Maç önizleme ve analizini al (varsa)
    try:
        preview = match.preview
    except:
        preview = None
        
    try:
        analysis = match.analysis
    except:
        analysis = None
    
    # Son 5 maç sonuçlarını al
    home_team_last_matches = Match.objects.filter(
        Q(home_team=match.home_team) | Q(away_team=match.home_team),
        match_date__lt=match.match_date,
        score__isnull=False
    ).order_by('-match_date')[:5]
    
    away_team_last_matches = Match.objects.filter(
        Q(home_team=match.away_team) | Q(away_team=match.away_team),
        match_date__lt=match.match_date,
        score__isnull=False
    ).order_by('-match_date')[:5]
    
    # İki takım arasındaki son maçları al
    head_to_head = Match.objects.filter(
        Q(home_team=match.home_team, away_team=match.away_team) | 
        Q(home_team=match.away_team, away_team=match.home_team),
        match_date__lt=match.match_date,
        score__isnull=False
    ).order_by('-match_date')[:5]
    
    # Maçın durumu (canlı, tamamlanmış, yaklaşan)
    current_time = timezone.now()
    is_live = match.match_date <= current_time <= (match.match_date + timedelta(hours=2))
    is_completed = match.score is not None
    
    # Preprocess match statistics for faster template rendering
    match_stats = {}
    if analysis:
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
    
    # Prepare timeline event data for JavaScript
    timeline_events = []
    for event in events:
        if event.event_type in ('GOAL', 'RED', 'YELLOW'):
            team = 'home' if event.player and event.player.team == match.home_team else 'away'
            timeline_events.append({
                'minute': event.minute,
                'type': event.event_type,
                'team': team,
                'player': event.player.name if event.player else 'Unknown',
                'description': event.description
            })
    
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
    
    return render(request, 'scores/match_detail.html', context)


def league_detail(request, league_id):
    league = League.objects.get(id=league_id)
    matches = Match.objects.filter(league=league).order_by('match_date')
    teams = Team.objects.filter(league=league)
    # Puan durumu için: Her takımın oynadığı maçlardan puan hesapla
    standings = []
    for team in teams:
        played = Match.objects.filter(league=league).filter(Q(home_team=team) | Q(away_team=team)).count()
        won = draw = lost = goals_for = goals_against = 0
        for match in Match.objects.filter(league=league).filter(Q(home_team=team) | Q(away_team=team)):
            if match.score:
                try:
                    home_goals, away_goals = map(int, match.score.split('-'))
                except Exception:
                    continue
                is_home = match.home_team == team
                is_away = match.away_team == team
                if is_home:
                    goals_for += home_goals
                    goals_against += away_goals
                    if home_goals > away_goals:
                        won += 1
                    elif home_goals == away_goals:
                        draw += 1
                    else:
                        lost += 1
                elif is_away:
                    goals_for += away_goals
                    goals_against += home_goals
                    if away_goals > home_goals:
                        won += 1
                    elif home_goals == away_goals:
                        draw += 1
                    else:
                        lost += 1
        points = won * 3 + draw
        standings.append({'team': team, 'played': played, 'won': won, 'draw': draw, 'lost': lost, 'goals_for': goals_for, 'goals_against': goals_against, 'points': points})
    standings = sorted(standings, key=lambda x: x['points'], reverse=True)
    # En çok gol atan takımlar
    from django.db.models import Count, F, Sum, Value, Case, When
    
    # Ev sahibi takımın goller istatistiğini hesapla
    home_goals = Match.objects.filter(
        league=league, 
        score__isnull=False
    ).annotate(
        team_name=F('home_team__name'),
        team_id=F('home_team__id'),
        goals=Sum(Case(
            When(score__regex=r'^[0-9]+-[0-9]+$', then=Value(1)),
            default=Value(0)
        ))
    ).values('team_name', 'team_id', 'goals')
    
    # Deplasman takımının goller istatistiğini hesapla  
    away_goals = Match.objects.filter(
        league=league, 
        score__isnull=False
    ).annotate(
        team_name=F('away_team__name'),
        team_id=F('away_team__id'),
        goals=Sum(Case(
            When(score__regex=r'^[0-9]+-[0-9]+$', then=Value(1)),
            default=Value(0)
        ))
    ).values('team_name', 'team_id', 'goals')
    
    # Takım bazlı en çok gol atanlar
    team_goals = {}
    for team in standings:
        team_goals[team['team'].id] = {
            'name': team['team'].name,
            'goals': team['goals_for']
        }
    
    # En çok gol atan takımları al
    scorer_stats = []
    for team_id, stats in sorted(team_goals.items(), key=lambda x: x[1]['goals'], reverse=True)[:5]:
        scorer_stats.append({
            'team_id': team_id,
            'match__home_team__name': stats['name'],
            'gol': stats['goals']
        })
    # En az gol yiyen takımlar
    least_conceded = sorted(standings, key=lambda x: x['goals_against'])[:5]
    # Grafik için veri
    team_names = [row['team'].name for row in standings]
    goals_for_list = [row['goals_for'] for row in standings]
    goals_against_list = [row['goals_against'] for row in standings]
    context = {
        'league': league,
        'matches': matches,
        'standings': standings,
        'scorer_stats': scorer_stats,
        'least_conceded': least_conceded,
        'team_names': team_names,
        'goals_for_list': goals_for_list,
        'goals_against_list': goals_against_list,
    }
    return render(request, 'scores/league_detail.html', context)


def team_detail(request, team_id):
    team = Team.objects.select_related('league').get(id=team_id)
    players = Player.objects.filter(team=team)
    
    # Son 5 maç (tamamlanmış maçları filtrele)
    last_matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team),
        match_date__lt=timezone.now(),
        score__isnull=False  # Skoru olan maçlar (tamamlanmış maçlar)
    ).order_by('-match_date')[:5]
    
    # Yaklaşan maçlar (bugünden itibaren)
    next_matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team),
        match_date__gte=timezone.now()
    ).order_by('match_date')[:10]
    
    # Bugünkü maçları kontrol et (bugün oynanacak veya oynanan maçlar)
    today = timezone.now().date()
    today_matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team),
        match_date__date=today
    ).order_by('match_date')
    
    # Context'e eklemek için bugünkü maçlar var mı?
    has_today_matches = today_matches.exists()
    
    # Tüm maçlar (istatistik için)
    all_matches = Match.objects.filter(Q(home_team=team) | Q(away_team=team))
    won = draw = lost = goals_for = goals_against = 0
    for match in all_matches:
        if match.score:
            try:
                home_goals, away_goals = map(int, match.score.split('-'))
            except Exception:
                continue
            is_home = match.home_team == team
            is_away = match.away_team == team
            if is_home:
                goals_for += home_goals
                goals_against += away_goals
                if home_goals > away_goals:
                    won += 1
                elif home_goals == away_goals:
                    draw += 1
                else:
                    lost += 1
            elif is_away:
                goals_for += away_goals
                goals_against += home_goals
                if away_goals > home_goals:
                    won += 1
                elif home_goals == away_goals:
                    draw += 1
                else:
                    lost += 1
    # En çok gol atan oyuncular (oyuncu ID'siyle, hem ev hem deplasman golleri)
    from django.db.models import Count
    scorer_stats = (
        Event.objects
        .filter(match__in=all_matches, event_type='GOAL', player__isnull=False)
        .values('player__id', 'player__name')
        .annotate(gol=Count('id'))
        .order_by('-gol')[:5]
    )
    # Grafik için veri (son 5 maç)
    match_labels = [m.match_date.strftime('%d.%m') for m in last_matches][::-1]
    match_results = []
    for m in reversed(last_matches):
        if m.score:
            home_goals, away_goals = map(int, m.score.split('-'))
            if m.home_team == team:
                match_results.append(home_goals - away_goals)
            else:
                match_results.append(away_goals - home_goals)
        else:
            match_results.append(0)
    context = {
        'team': team,
        'players': players,
        'last_matches': last_matches,
        'next_matches': next_matches,
        'today_matches': today_matches,  # Bugünkü maçlar
        'has_today_matches': has_today_matches,  # Bugünkü maçlar var mı?
        'won': won,
        'draw': draw,
        'lost': lost,
        'goals_for': goals_for,
        'goals_against': goals_against,
        'scorer_stats': scorer_stats,
        'match_labels': match_labels,
        'match_results': match_results,
    }
    return render(request, 'scores/team_detail.html', context)


@login_required
def profile(request):
    # Get or create the profile
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # If profile was just created, set default values
    if created:
        profile.notify_goals = True
        profile.notify_red_cards = True
        profile.notify_match_start = True
        profile.save()
    
    favorite_teams = profile.favorite_teams.all()
    favorite_leagues = profile.favorite_leagues.all()
    favorite_players = profile.favorite_players.all()
    return render(request, 'scores/profile.html', {
        'profile': profile, 
        'favorite_teams': favorite_teams,
        'favorite_leagues': favorite_leagues,
        'favorite_players': favorite_players
    })


@login_required
def add_favorite(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    request.user.profile.favorite_teams.add(team)
    return redirect('scores:team_detail', team_id=team_id)

@login_required
def remove_favorite(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    request.user.profile.favorite_teams.remove(team)
    return redirect('scores:team_detail', team_id=team_id)

@login_required
def add_favorite_league(request, league_id):
    league = get_object_or_404(League, id=league_id)
    request.user.profile.favorite_leagues.add(league)
    return redirect('scores:league_detail', league_id=league_id)

@login_required
def remove_favorite_league(request, league_id):
    league = get_object_or_404(League, id=league_id)
    request.user.profile.favorite_leagues.remove(league)
    return redirect('scores:league_detail', league_id=league_id)

@login_required
def add_favorite_player(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    request.user.profile.favorite_players.add(player)
    # Redirect to the team detail page which shows the player
    return redirect('scores:team_detail', team_id=player.team.id)

@login_required
def remove_favorite_player(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    request.user.profile.favorite_players.remove(player)
    # Redirect to the team detail page which shows the player
    return redirect('scores:team_detail', team_id=player.team.id)


# Ligler
class LeagueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer

# Takımlar
class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

# Maçlar
class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer

# Profil (sadece giriş yapan kullanıcının favori takımları)
class FavoriteTeamsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'leagues', LeagueViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'matches', MatchViewSet)

# urlpatterns eklenecek:
# path('api/favorites/', FavoriteTeamsView.as_view()),
# path('api/', include(router.urls)),

def today_matches(request):
    """Bugünkü ve yaklaşan maçları gösterir."""
    today = timezone.now().date()
    end_date = today + timedelta(days=5)  # Bugün ve sonraki 5 gün
    
    # Tüm ligleri al
    leagues = League.objects.all().order_by('name')
    
    # Bugünkü maçlar
    todays_matches = Match.objects.filter(
        match_date__date=today
    ).select_related('home_team', 'away_team', 'league').order_by('match_date')
    
    # Yaklaşan maçlar (sonraki 5 gün)
    upcoming_matches = Match.objects.filter(
        match_date__date__gt=today,
        match_date__date__lte=end_date
    ).select_related('home_team', 'away_team', 'league').order_by('match_date')
    
    # Liglere göre gruplandırılmış bugünkü maçlar
    leagues_with_todays_matches = []
    
    for league in leagues:
        matches = todays_matches.filter(league=league)
        if matches.exists():
            leagues_with_todays_matches.append({
                'league': league,
                'matches': matches
            })
    
    # Tarihlere göre gruplandırılmış yaklaşan maçlar
    dates_with_matches = []
    
    for i in range(1, 6):  # Sonraki 5 gün
        match_date = today + timedelta(days=i)
        matches = upcoming_matches.filter(match_date__date=match_date)
        
        if matches.exists():
            dates_with_matches.append({
                'date': match_date,
                'matches': matches
            })
    
    context = {
        'today': today,
        'todays_matches': todays_matches,
        'leagues_with_todays_matches': leagues_with_todays_matches,
        'dates_with_matches': dates_with_matches,
    }
    
    return render(request, 'scores/today_matches.html', context)

def teams_list(request):
    """Tüm takımların listesini gösterir."""
    # Ligleri alfabetik sıraya göre al
    leagues = League.objects.all().order_by('name')
    
    # Her lig için takımları hazırla
    leagues_with_teams = []
    for league in leagues:
        teams = Team.objects.filter(league=league).order_by('name')
        if teams.exists():
            leagues_with_teams.append({
                'league': league,
                'teams': teams
            })
    
    context = {
        'leagues_with_teams': leagues_with_teams,
    }
    
    return render(request, 'scores/teams_list.html', context)

def leagues_list(request):
    """Tüm liglerin listesini gösterir."""
    leagues = League.objects.all().order_by('name')
    
    # Her lig için takım sayısını hesapla
    leagues_with_teams_count = []
    for league in leagues:
        teams_count = Team.objects.filter(league=league).count()
        leagues_with_teams_count.append({
            'league': league,
            'teams_count': teams_count
        })
    
    context = {
        'leagues_with_teams_count': leagues_with_teams_count,
    }
    
    return render(request, 'scores/leagues_list.html', context)

def upcoming_matches(request):
    """Yaklaşan maçları gösterir (gelecek 7 gün)."""
    today = timezone.now().date()
    end_date = today + timedelta(days=7)  # Yaklaşan 7 gün
    
    # Tüm ligleri al
    leagues = League.objects.all().order_by('name')
    
    # Yaklaşan maçları al (bugün dahil)
    upcoming = Match.objects.filter(
        match_date__date__gte=today,
        match_date__date__lte=end_date
    ).select_related('home_team', 'away_team', 'league').order_by('match_date')
    
    # Tarihlere göre gruplandırılmış maçlar
    dates_with_matches = []
    
    for i in range(0, 8):  # Bugün ve sonraki 7 gün
        match_date = today + timedelta(days=i)
        matches = upcoming.filter(match_date__date=match_date)
        
        if matches.exists():
            # Liglere göre maçları grupla
            leagues_in_day = []
            for league in leagues:
                league_matches = matches.filter(league=league)
                if league_matches.exists():
                    leagues_in_day.append({
                        'league': league,
                        'matches': league_matches
                    })
            
            dates_with_matches.append({
                'date': match_date,
                'matches': matches,
                'leagues': leagues_in_day,
                'count': matches.count()
            })
    
    context = {
        'today': today,
        'dates_with_matches': dates_with_matches,
    }
    
    return render(request, 'scores/upcoming_matches.html', context)