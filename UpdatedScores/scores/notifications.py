from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('goal', 'Gol'),
        ('red_card', 'Kırmızı Kart'),
        ('lineup', 'İlk 11'),
        ('match_start', 'Maç Başlamak Üzere'),
        ('important', 'Önemli Olay'),
        ('system', 'Sistem Bildirimi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    url = models.CharField(max_length=255, blank=True, null=True)  # Optional link to relevant page
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()
