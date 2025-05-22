from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Creates a superuser for the production environment'

    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email=os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@example.com'),
                password=os.environ.get('DJANGO_ADMIN_PASSWORD', 'changeme123!')
            )
