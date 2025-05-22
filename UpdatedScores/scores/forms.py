from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, Team, League, Player

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='İsim', required=False)
    last_name = forms.CharField(label='Soyisim', required=False)
    birth_date = forms.DateField(
        label='Doğum Tarihi', 
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    # Favori seçimleri
    favorite_teams = forms.ModelMultipleChoiceField(
        label='Favori Takımlar',
        queryset=Team.objects.all().order_by('name'), 
        required=False, 
        widget=forms.CheckboxSelectMultiple
    )
    
    favorite_leagues = forms.ModelMultipleChoiceField(
        label='Favori Ligler',
        queryset=League.objects.all().order_by('name'), 
        required=False, 
        widget=forms.CheckboxSelectMultiple
    )
    
    favorite_players = forms.ModelMultipleChoiceField(
        label='Favori Oyuncular',
        queryset=Player.objects.all().order_by('name'), 
        required=False, 
        widget=forms.SelectMultiple(attrs={'class': 'select2'})
    )
    
    # Bildirim tercihleri için boolean alanlar
    notify_goals = forms.BooleanField(
        label='Gol Bildirimlerini Al', 
        required=False
    )
    notify_red_cards = forms.BooleanField(
        label='Kırmızı Kart Bildirimlerini Al', 
        required=False
    )
    notify_lineup = forms.BooleanField(
        label='İlk 11 Bildirimlerini Al', 
        required=False
    )
    notify_match_start = forms.BooleanField(
        label='Maç Başlamadan 15dk Önce Bildir', 
        required=False
    )
    notify_important_events = forms.BooleanField(
        label='Sadece Önemli Olayları Bildir', 
        required=False
    )
    
    notification_method = forms.ChoiceField(
        label='Bildirim Yöntemi',
        choices=Profile.NOTIFICATION_METHOD_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    
    class Meta:
        model = Profile
        fields = [
            'first_name', 'last_name', 'birth_date', 
            'favorite_teams', 'favorite_leagues', 'favorite_players',
            'notify_goals', 'notify_red_cards', 'notify_lineup', 
            'notify_match_start', 'notify_important_events',
            'notification_method'
        ]
