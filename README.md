# 🤖 İtobot - FIRST Robotics Grant Tracker

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

**FIRST Robotics hibe fırsatlarını otomatik takip eden Telegram botu**

[Hızlı Başlangıç](#-hızlı-başlangıç) • [Kurulum](#-kurulum) • [Komutlar](#-bot-komutları)

</div>

---

## 📋 Nedir?

İtobot Grant Tracker, FIRST Inspires web sitesinde yayınlanan tüm hibe ve fırsat duyurularını **otomatik olarak takip** etmek ve Telegram üzerinden **anında bildirim** göndermek için 7/24 çalışan profesyonel bir bot uygulamasıdır.

Hiçbir kullanıcının kod içinde **hiçbir şey değiştirmesine gerek yok!** Telegram'da bot adını aratıp `/start` komutunu çalıştırın ve hemen abone olmaya başlayın, hepsi bu kadar.

### ✨ Özellikler

- 🔍 **Otomatik Tarama** - 15 dakikada bir FIRST portalını tarar
- 🚨 **Anında Bildirim** - Yeni hibe duyurularını hemen bildir
- 👥 **Çok Kullanıcı Desteği** - Birden fazla kullanıcı kullanabilir
- 📊 **Kişisel İstatistikler** - Aldığınız bildirim sayısını görün
- 🟢 **7/24 Aktif** - Render + UptimeRobot ile kesintisiz çalışma
- 🔒 **Güvenli** - Tüm credentials `.env`'de saklanır
- ⚡ **Basit** - Kullanıcılar sadece `/start` yazarlar, başlangıç biter

---

## ⚡ Hızlı Başlangıç

### 30 saniye'de başla:

```bash
1. Telegram'da arama kısmına gir ve şunu yaz: @itobot_grant_tracker_bot
2. /start yazıp gönder
3. "📨 Abone Ol" butonuna tıkla
4. Tamamlandı. Artık hibeler açıklandığında anında bildirim alacağınız bir botunuz var! ✅
```

## 🤖 Bot Komutları

Telegram'da butonlar var, hepsi otomatik:

| Buton | Açıklama |
|-------|----------|
| 📨 **Abone Ol** | Yeni hibe bildirimlerini almaya başla |
| ❌ **Abone Olmaktan Çık** | Bildirimler almayı durdur |
| ⏱️ **Sonraki Tarama** | Bir sonraki site kontrolüne kalan süreyi görmeni sağlar |
| 📈 **İstatistik** | Senin aldığın bildirim sayısı |
| 🟢 **Durum** | Bot durumu ve toplam istatistikler |
| ❓ **Yardım** | Komut listesi |

---

## 📁 Proje Yapısı

```
frc-grant-tracker/
│
├── 📄 bot.py                 ← ANA BOT DOSYASI
├── 📄 database.py            ← Veritabanı işlemleri
├── 📄 scraper.py             ← FIRST site scraper
├── 📄 config.py              ← Konfigürasyon
│
├── 📄 .env                   ← Environment şablonu
├── 📄 .gitignore             ← Git ignore
├── 📄 requirements.txt       ← Python paketleri
├── 📄 Procfile               ← Render deployment
│
├── 📚 Dokümantasyon
│   ├── README.md             ← Bu dosya
│   ├── QUICK_START.md        ← 30 dakikalık başlangıç
│   ├── SETUP-GUIDE.md        ← Detaylı kurulum
│   └── SECURITY.md           ← Güvenlik bilgileri
│
└── 📦 grant_tracker.db       ← Veritabanı (local)
```

**Toplam: 11 dosya, ~1000 satır production-ready kod**

---

## 🔐 Güvenlik

- ✅ Token `.env`'de saklanır (GitHub'a gitmez)
- ✅ Tüm user verisi şifreli veritabanında
- ✅ SQL Injection prevention (SQLAlchemy ORM)
- ✅ Input validation tüm komutlarda

**❌ Asla:** Token'ı GitHub'a commit etme!

---

## 📊 İstatistikler

Bot otomatik olarak takip eder:
- ✅ Toplam tarama sayısı
- 🚨 Gönderilen bildirim sayısı
- 👥 Aktif kullanıcı sayısı

Telegram'da `/durum` yazınca göreceksin.

---

## 🛠️ Teknolojiler

- **Python 3.9+** - Dil
- **python-telegram-bot** - Telegram API
- **BeautifulSoup4** - Web scraping
- **SQLAlchemy** - ORM
- **SQLite/PostgreSQL** - Veritabanı
- **Render** - Hosting
- **UptimeRobot** - Monitoring

---

## 📧 Destek

- **GitHub Issues:** [Issues](https://github.com/EmirhannCoskun/frc-grant-tracker/issues)

---

## 🙏 Teşekkürler

- [python-telegram-bot](https://python-telegram-bot.readthedocs.io/) - Telegram API
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - Web scraping
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [FIRST Inspires](https://www.firstinspires.org/) - Grant opportunities

---

<div align="center">

Made with by Team İTOBOT

**⭐ Bu projeyi beğendiysen yıldız atabilirsin!**

</div>