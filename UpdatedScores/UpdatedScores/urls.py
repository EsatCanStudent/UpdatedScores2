from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# Add i18n URLs first
urlpatterns = [
    path('i18n/setlang/', include('django.conf.urls.i18n'), name='set_language'),  # Dil değiştirme view'ı
]

# Then add the rest of the URLs
urlpatterns += [
    path('admin/', admin.site.urls),
    path('', include('scores.urls', namespace='scores_main')),  # Ana dizine yönlendirme
    path('scores/', include('scores.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # Django'nun yerleşik kimlik doğrulama görünümleri
]

# Add URL patterns for serving media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)