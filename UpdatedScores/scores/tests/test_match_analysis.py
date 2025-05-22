from django.test import TestCase
from django.core import management
from scores.models import Match, League, Team, MatchPreview, MatchAnalysis
from django.utils import timezone
from datetime import timedelta

class MatchAnalysisCommandTest(TestCase):
    def setUp(self):
        # Test için gerekli verileri oluştur
        self.league = League.objects.create(id="test_league", name="Test Ligi", country="Test Ülkesi")
        
        self.team1 = Team.objects.create(id="team1", name="Test Takımı 1", league=self.league)
        self.team2 = Team.objects.create(id="team2", name="Test Takımı 2", league=self.league)
        
        # Gelecekteki bir maç
        self.future_match = Match.objects.create(
            id="future_match",
            home_team=self.team1,
            away_team=self.team2,
            match_date=timezone.now() + timedelta(days=1),
            league=self.league,
            stadium="Test Stadyumu",
            status="SCHEDULED"
        )
        
        # Geçmişteki tamamlanmış bir maç
        self.past_match = Match.objects.create(
            id="past_match",
            home_team=self.team1,
            away_team=self.team2,
            match_date=timezone.now() - timedelta(days=1),
            league=self.league,
            stadium="Test Stadyumu",
            score="2-1",
            status="FINISHED"
        )
    
    def test_generate_preview(self):
        """Maç önizlemesi oluşturulabilmeli"""
        # Önizleme oluştur
        management.call_command('generate_match_analysis', preview=True)
        
        # Önizleme oluşturulmuş mu kontrol et
        self.assertTrue(hasattr(self.future_match, 'preview'))
        
        preview = MatchPreview.objects.get(match=self.future_match)
        self.assertIsNotNone(preview.home_form)
        self.assertIsNotNone(preview.away_form)
        self.assertIsNotNone(preview.preview_text)
    
    def test_generate_analysis(self):
        """Maç analizi oluşturulabilmeli"""
        # Analiz oluştur
        management.call_command('generate_match_analysis', analysis=True)
        
        # Analiz oluşturulmuş mu kontrol et
        self.assertTrue(hasattr(self.past_match, 'analysis'))
        
        analysis = MatchAnalysis.objects.get(match=self.past_match)
        self.assertIsNotNone(analysis.possession)
        self.assertIsNotNone(analysis.shots)
        self.assertIsNotNone(analysis.analysis_text)
        
    def test_specific_match_analysis(self):
        """Belirli bir maç için analiz oluşturulabilmeli"""
        management.call_command('generate_match_analysis', match_id=self.past_match.id)
        
        # Analiz oluşturulmuş mu kontrol et
        analysis = MatchAnalysis.objects.get(match=self.past_match)
        self.assertIsNotNone(analysis)
