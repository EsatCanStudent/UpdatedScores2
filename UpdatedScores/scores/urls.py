from django.urls import path, include
from . import views
from . import enhanced_views
from . import performance_views
from .views import router, FavoriteTeamsView

app_name = "scores"

urlpatterns = [
    path("", views.index, name="index"),
    path("refresh/", views.refresh_data, name="refresh_data"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("match/<int:match_id>/", enhanced_views.enhanced_match_detail, name="match_detail"),
    path("league/<int:league_id>/", views.league_detail, name="league_detail"),
    path("team/<int:team_id>/", views.team_detail, name="team_detail"),
    path('team/<str:team_id>/add_favorite/', views.add_favorite, name='add_favorite'),
    path('team/<str:team_id>/remove_favorite/', views.remove_favorite, name='remove_favorite'),
    path('league/<str:league_id>/add_favorite/', views.add_favorite_league, name='add_favorite_league'),
    path('league/<str:league_id>/remove_favorite/', views.remove_favorite_league, name='remove_favorite_league'),
    path('player/<str:player_id>/add_favorite/', views.add_favorite_player, name='add_favorite_player'),
    path('player/<str:player_id>/remove_favorite/', views.remove_favorite_player, name='remove_favorite_player'),
    # Performance monitoring - temporarily disabled for debugging
    # path('admin/performance/', performance_views.performance_dashboard, name='performance_dashboard'),
    # REST API endpoints
    path('api/favorites/', FavoriteTeamsView.as_view(), name='api-favorites'),
    path('api/', include(router.urls)),
    path('leagues/', views.leagues_list, name='leagues'),
    path('teams/', views.teams_list, name='teams'),
    path('today/', views.today_matches, name='today_matches'),
    path('upcoming/', views.upcoming_matches, name='upcoming_matches'),
]
