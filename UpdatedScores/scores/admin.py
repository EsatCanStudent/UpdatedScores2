from django.contrib import admin
from django import forms
from .models import League, Team, Player, Match, Event, Profile, MatchPreview, MatchAnalysis
from .notifications import Notification
from datetime import datetime, timedelta

class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    search_fields = ('name', 'country')

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'position')
    list_filter = ('team', 'position')
    search_fields = ('name',)

class MatchAdmin(admin.ModelAdmin):
    list_display = ('home_team', 'away_team', 'league', 'match_date', 'stadium', 'score')
    list_filter = ('league', 'match_date')
    search_fields = ('home_team__name', 'away_team__name', 'stadium')
    date_hierarchy = 'match_date'

class EventAdmin(admin.ModelAdmin):
    list_display = ('match', 'minute', 'event_type', 'player', 'description')
    list_filter = ('event_type', 'match')
    search_fields = ('description', 'player__name')

class TeamAdmin(admin.ModelAdmin):
    pass

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'birth_date', 'notification_method')
    search_fields = ('user__username', 'user__email', 'first_name', 'last_name')
    list_filter = ('notification_method', 'notify_goals', 'notify_red_cards', 'notify_lineup')
    filter_horizontal = ('favorite_teams', 'favorite_leagues', 'favorite_players')
    fieldsets = (
        ('Kişisel Bilgiler', {
            'fields': ('user', 'first_name', 'last_name', 'birth_date')
        }),
        ('Favori Seçimleri', {
            'fields': ('favorite_teams', 'favorite_leagues', 'favorite_players')
        }),
        ('Bildirim Tercihleri', {
            'fields': (
                'notify_goals', 'notify_red_cards', 'notify_lineup', 
                'notify_match_start', 'notify_important_events', 
                'notification_method', 'notification_settings'
            )
        }),
    )

class MatchPreviewForm(forms.ModelForm):
    preview_text = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), required=False)
    key_players = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    
    class Meta:
        model = MatchPreview
        fields = '__all__'

class MatchPreviewAdmin(admin.ModelAdmin):
    form = MatchPreviewForm
    list_display = ('match', 'prediction', 'last_updated')
    search_fields = ('match__home_team__name', 'match__away_team__name')
    list_filter = ('last_updated',)
    readonly_fields = ('last_updated',)
    fieldsets = (
        ('Maç Bilgisi', {
            'fields': ('match',)
        }),
        ('Takım Formu', {
            'fields': ('home_form', 'away_form',)
        }),
        ('Önizleme İçeriği', {
            'fields': ('preview_text', 'prediction', 'key_players',)
        }),
        ('İstatistikler', {
            'classes': ('collapse',),
            'fields': ('home_stats', 'away_stats', 'head_to_head',)
        }),
        ('Sistem Bilgisi', {
            'fields': ('last_updated',),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        # En yakın tarihli ve gelecek maçları daha üstte göster
        qs = super().get_queryset(request)
        return qs.order_by('-match__match_date')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Maç seçim menüsünde gelecek maçları göster
        if db_field.name == "match":
            kwargs["queryset"] = Match.objects.filter(match_date__gte=datetime.now() - timedelta(days=1)).order_by('match_date')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class MatchAnalysisForm(forms.ModelForm):
    analysis_text = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), required=False)
    
    class Meta:
        model = MatchAnalysis
        fields = '__all__'

class MatchAnalysisAdmin(admin.ModelAdmin):
    form = MatchAnalysisForm
    list_display = ('match', 'possession', 'shots', 'last_updated')
    search_fields = ('match__home_team__name', 'match__away_team__name')
    list_filter = ('last_updated',)
    readonly_fields = ('last_updated',)
    fieldsets = (
        ('Maç Bilgisi', {
            'fields': ('match',)
        }),
        ('Ana İstatistikler', {
            'fields': ('possession', 'shots', 'shots_on_target', 'corners', 'fouls', 'yellows', 'reds',)
        }),
        ('Detaylı Analiz', {
            'fields': ('analysis_text', 'key_moments',)
        }),
        ('Oyuncu Değerlendirmeleri', {
            'fields': ('player_ratings',),
            'classes': ('collapse',),
        }),
        ('Sistem Bilgisi', {
            'fields': ('last_updated',),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        # Tamamlanmış maçları göster (en yakın tarihli olanlar üstte)
        qs = super().get_queryset(request)
        return qs.order_by('-match__match_date')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Maç seçiminde tamamlanan maçları göster
        if db_field.name == "match":
            kwargs["queryset"] = Match.objects.filter(score__isnull=False).order_by('-match_date')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'created_at', 'is_read')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'title', 'message', 'url')
        }),
        ('Status', {
            'fields': ('created_at', 'is_read')
        }),
    )

admin.site.register(League, LeagueAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Match, MatchAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(MatchPreview, MatchPreviewAdmin)
admin.site.register(MatchAnalysis, MatchAnalysisAdmin)
admin.site.register(Notification, NotificationAdmin)
