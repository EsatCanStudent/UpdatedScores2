# UpdatedScores - Futbol Skorları Takip Uygulaması

API-FOOTBALL entegrasyonu ile canlı futbol skorları, maç istatistikleri ve bildirimler sunan Django web uygulaması.

## 🌟 Özellikler

- 📱 Canlı maç skorları ve istatistikleri
- 👤 Kullanıcı profili ve favori takip sistemi
- 🔔 Özelleştirilebilir bildirim sistemi
- 🌍 Çoklu dil desteği (Türkçe/İngilizce)
- 📊 Detaylı maç analizleri ve istatistikler
- 📅 Fixture ve skor takvimi

## 🚀 Kurulum

1. Repository'i klonlayın:
```bash
git clone https://github.com/EsatCanStudent/UpdatedScores2.git
cd UpdatedScores2
```

2. Virtual environment oluşturun:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Gereksinimleri yükleyin:
```bash
pip install -r requirements.txt
```

4. `.env` dosyasını oluşturun:
```
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

API_FOOTBALL_KEY=your-api-key
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
UPDATE_INTERVAL=3600

SECURE_SSL_REDIRECT=False
```

5. Veritabanını oluşturun:
```bash
python manage.py migrate
```

6. Sunucuyu başlatın:
```bash
python manage.py runserver
```

## 📝 Kullanım

- Ana sayfa: http://localhost:8000/
- Admin paneli: http://localhost:8000/admin/
- Profil sayfası: http://localhost:8000/profile/
