# UpdatedScores

UpdatedScores, TheSportsDB API ve API-FOOTBALL servislerini kullanarak dünya çapındaki futbol ligleri, takımları, oyuncuları ve maç sonuçlarını otomatik olarak çeken ve görüntüleyen bir Django web uygulamasıdır.

## Özellikler

### Temel Özellikler
- TheSportsDB ve API-FOOTBALL entegrasyonu
- Otomatik veri güncelleme (saatlik ve günlük)
- Ligler, takımlar, oyuncular
- Güncel maç skorları ve sonuçları
- Modern ve responsive tasarım
- Filtreleme ve kategorileme özellikleri

### Gelişmiş Özellikler
- Maç olayları (gol, kart, vb.) gerçek zamanlı takibi
- Maç kadroları ve formasyonlar
- Detaylı maç önizlemesi ve analizi
- Oyuncu puanlamaları ve detaylı istatistikler
- Karşılıklı maç geçmişi ve istatistikleri
- Canlı maç gösterimi ve geri sayım
- Favori takım, lig ve oyuncu takibi
- Kişiselleştirilmiş bildirimler (e-posta ve push)

## Kurulum

1. Depoyu klonlayın:
   ```
   git clone https://github.com/yourusername/UpdatedScores.git
   cd UpdatedScores
   ```

2. Sanal ortam oluşturun ve bağımlılıkları yükleyin:
   ```
   python -m venv venv
   venv\Scripts\activate (Windows) veya source venv/bin/activate (Linux/Mac)
   pip install -r requirements.txt
   ```

3. Veritabanını oluşturun:
   ```
   python manage.py migrate
   ```

4. Superuser oluşturun:
   ```
   python manage.py createsuperuser
   ```

5. API anahtarlarını ayarlayın:
   ```
   # TheSportsDB için (Windows PowerShell)
   $env:THESPORTSDB_API_KEY="your_thesportsdb_api_key"
   
   # API-FOOTBALL için (Windows PowerShell)
   $env:API_FOOTBALL_KEY="your_api_football_key"
   $env:API_FOOTBALL_BASE_URL="https://v3.football.api-sports.io"
   ```

6. Verileri API'den çekin:
   ```
   # TheSportsDB verilerini çekmek için
   python manage.py fetch_sports_data --full
   
   # API-FOOTBALL verilerini çekmek için
   python manage.py fetch_api_football_matches --next=14 --last=14
   python manage.py fetch_match_lineups
   python manage.py fetch_match_events
   python manage.py fetch_match_statistics
   python manage.py fetch_match_previews
   
   # Veya otomatik güncelleme için
   python manage.py schedule_football_updates --continuous
   ```

6. Sunucuyu başlatın:
   ```
   python manage.py runserver
   ```

7. Tarayıcınızı açın ve http://127.0.0.1:8000 adresine gidin.

## Planlı Görevler

Uygulama, verilerin otomatik olarak güncel tutulması için planlı görevlere sahiptir:

- Saatlik Güncelleme: Maç sonuçları ve olaylar her saat başı güncellenir.
- Günde 4 Kere Güncelleme: Bugünkü maçlar günün belirli saatlerinde (7:00, 12:00, 16:00, 20:00) güncellenir.
- Günlük Tam Güncelleme: Tüm veriler (ligler, takımlar, oyuncular dahil) her gün gece 03:00'da tamamen güncellenir.
- Maç Önizlemeleri: Gelecekteki maçlar için önizleme her gün sabah 08:00'de oluşturulur.
- Maç Analizleri: Tamamlanmış maçlar için analiz her 6 saatte bir güncellenir.

Scheduler'ı aktif etmek için aşağıdaki komutları kullanabilirsiniz:

```
# Tüm zamanlayıcılar için:
python manage.py run_scheduler

# Hemen maç analizleri oluşturmak için:
python manage.py run_scheduler --generate-analysis --now

# Hemen maç verilerini güncellemek için:
python manage.py run_scheduler --update-matches --now
```

Alternatif olarak `scores/apps.py` dosyasını `scores/apps_with_scheduler.py` ile değiştirebilirsiniz.

## API-FOOTBALL Entegrasyonu

UpdatedScores, API-FOOTBALL servisiyle tam entegrasyona sahiptir. Bu entegrasyon aşağıdaki özellikleri sağlar:

- **Maçlar**: Gelecek ve geçmiş maç bilgileri
- **Kadrolar**: Maç kadroları ve formasyonlar
- **Olaylar**: Goller, kartlar, değişiklikler vb. maç olayları
- **İstatistikler**: Detaylı maç istatistikleri ve oyuncu performansları
- **Önizlemeler**: Maç önizlemeleri ve tahminler

API-FOOTBALL entegrasyonunu yapılandırmak ve kullanmak için aşağıdaki belgelere bakabilirsiniz:

- [API-FOOTBALL Entegrasyon Rehberi](docs/api_football_integration.md)
- [API-FOOTBALL Hızlı Başlangıç](docs/api_football_quickstart.md)
- [Scores App API-FOOTBALL README](scores/README_API_FOOTBALL.md)

### Otomatik Güncelleme

API-FOOTBALL verilerini otomatik olarak güncel tutmak için şu komutları kullanabilirsiniz:

```
# Windows Task Scheduler kullanarak otomatik güncelleme ayarlamak için:
.\setup_scheduler.ps1

# Manuel olarak tüm güncellemeleri çalıştırmak için:
python manage.py schedule_football_updates
```

## Teknolojiler

- Django 4.2+
- API-FOOTBALL ve TheSportsDB API entegrasyonları
- Python Requests
- Bootstrap 5
- Django APScheduler
- PowerShell Scheduling (Windows)

## API Anahtarları

- **TheSportsDB**: Ücretsiz API anahtarı "1" olarak belirlenmiştir. Daha gelişmiş özellikler için TheSportsDB'nin premium planlarına başvurabilirsiniz.
- **API-FOOTBALL**: Ücretsiz API anahtarı günlük 100 istek sınırına sahiptir. Daha fazla istek için [api-football.com](https://www.api-football.com/) adresinden premium hesap alabilirsiniz.

## Test

API-FOOTBALL entegrasyonunun testleri:

```
python manage.py test scores.tests.test_api_football
```

## Lisans

This project is licensed under the MIT License. See the LICENSE file for details.