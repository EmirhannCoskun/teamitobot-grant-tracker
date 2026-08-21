# 🤖 İtobot - FIRST Robotics Grant Tracker

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

**FIRST Robotics hibe fırsatlarını otomatik takip eden Telegram botu**

[Hızlı Başlangıç](#-hızlı-başlangıç) • [Kurulum](#-kurulum) • [Bot Komutları](#-bot-komutları) • [Özellikler](#-özellikler)

</div>

---

## 📋 Nedir?

İtobot Grant Tracker, FIRST Inspires web sitesinde yayınlanan **FRC hibe fırsatlarını otomatik olarak takip** eden ve yeni fırsatlar yayınlandığında Telegram üzerinden **bildirim gönderen** bir bot uygulamasıdır.

Bot, FIRST'in hibe fırsatları sayfasını **15 dakikada bir** kontrol eder. Yeni bir FRC hibesi tespit edildiğinde hibenin:

* Başlığını
* Başlangıç tarihini
* Bitiş tarihini
* Doğrudan başvuru bağlantısını

veritabanına kaydeder ve abone olan kullanıcılara bildirir.

Kullanıcıların kod üzerinde herhangi bir değişiklik yapmasına gerek yoktur. Telegram'da botu açıp `/start` komutunu kullanmaları yeterlidir.

### ✨ Özellikler

* 🔍 **Otomatik Tarama** - FIRST hibe portalını 15 dakikada bir kontrol eder
* 🚨 **Otomatik Bildirim** - Yeni FRC hibeleri bulunduğunda abone kullanıcılara Telegram bildirimi gönderir
* 🔗 **Doğrudan Başvuru Linki** - Bildirimlerde ilgili hibenin doğrudan başvuru bağlantısı bulunur
* 📅 **Hibe Tarihleri** - Başlangıç ve bitiş tarihleri bildirimlerde gösterilir
* 👥 **Çok Kullanıcı Desteği** - Birden fazla kullanıcı aynı botu kullanabilir
* 📊 **Kişisel İstatistikler** - Her kullanıcı kendi tarama ve aldığı bildirim sayılarını görebilir
* 🟢 **Bot Durumu** - Aktif kullanıcı sayısı, abonelik durumu ve sistem durumu görüntülenebilir
* ⏱️ **Sonraki Tarama** - Bir sonraki otomatik taramaya kalan süre görüntülenebilir
* 📈 **Son Tarama ve Çalışma Süresi** - Botun son tarama zamanı ve mevcut çalışma süresi görüntülenebilir
* 🔔 **Abonelik Yönetimi** - Bildirimler istenildiğinde açılıp kapatılabilir
* 🛡️ **Tekrarlı Bildirim Önleme** - Aynı hibe aynı kullanıcıya tekrar tekrar gönderilmez
* ☁️ **Production Ready** - Render ve PostgreSQL üzerinde çalışacak şekilde yapılandırılmıştır

---

## ⚡ Hızlı Başlangıç

### 30 saniyede başla:

```text
1. Telegram'da arama kısmına @itobot_grant_tracker_bot yaz
2. /start komutunu gönder
3. "📨 Abone Ol" butonuna bas
4. Tamamlandı! ✅
```

Bundan sonra yeni FRC hibe fırsatları bulunduğunda bildirim alırsınız.

---

## 🤖 Bot Komutları

Bot içerisinde tüm temel işlemler butonlar üzerinden yapılır.

| Buton                    | Açıklama                                                          |
| ------------------------ | ----------------------------------------------------------------- |
| 📨 **Abone Ol**          | Yeni hibe bildirimlerini almaya başla                             |
| ❌ **Abone Olmaktan Çık** | Hibe bildirimlerini durdur                                        |
| ⏱️ **Sonraki Tarama**    | Bir sonraki otomatik taramaya kalan süreyi göster                 |
| 📈 **İstatistik**        | Kişisel tarama ve bildirim istatistiklerini göster                |
| 🟢 **Durum**             | Aktif kullanıcı sayısı, abonelik durumu ve sistem durumunu göster |
| ❓ **Yardım**             | Botun kullanım bilgilerini göster                                 |

---

## 📊 İstatistikler

Bot iki farklı istatistik görünümü sunar.

### 📈 Kişisel İstatistikler

Her kullanıcı yalnızca **kendi verilerini** görür:

* 🔍 Kendisi için gerçekleştirilen tarama sayısı
* 📨 Aldığı hibe bildirimlerinin sayısı
* 🕐 Botun son tarama zamanı
* ⏱️ Botun mevcut çalışma süresi

### 🟢 Bot Durumu

Genel sistem durumu:

* 👥 Aktif kullanıcı sayısı
* 🔔 Kullanıcının abonelik durumu
* ⚙️ Sistem çalışma durumu

---

## 📁 Proje Yapısı

```text
frc-grant-tracker/
│
├── 📄 bot.py                 ← Ana Telegram botu
├── 📄 database.py            ← Veritabanı modelleri ve işlemleri
├── 📄 scraper.py             ← FIRST hibe scraper'ı
├── 📄 config.py              ← Konfigürasyon yönetimi
│
├── 📄 .env                   ← Environment değişkenleri (local)
├── 📄 .gitignore             ← Git ignore kuralları
├── 📄 requirements.txt       ← Python bağımlılıkları
├── 📄 Procfile               ← Render deployment
│
├── 📚 Dokümantasyon
│   ├── README.md             ← Bu dosya
│   ├── QUICK_START.md        ← Hızlı başlangıç
│   ├── SETUP-GUIDE.md        ← Detaylı kurulum
│   └── SECURITY.md           ← Güvenlik bilgileri
│
└── 📦 grant_tracker.db       ← Local development database
```

> `grant_tracker.db` yalnızca local development için kullanılır. Production ortamında PostgreSQL kullanılır.

---

## 🔐 Güvenlik

* ✅ Telegram bot token'ı `.env` üzerinden okunur
* ✅ Secret değerler GitHub repository'sine commit edilmez
* ✅ Local database dosyaları `.gitignore` ile hariç tutulur
* ✅ SQLAlchemy ORM kullanılır
* ✅ PostgreSQL production ortamında kullanılır
* ✅ Environment değişkenleri üzerinden production configuration yönetilir

### ❌ Asla

Bot token'ını, database şifresini veya diğer secret bilgileri GitHub'a commit etmeyin.

---

## 🛠️ Teknolojiler

* **Python 3.12+** - Programlama dili
* **python-telegram-bot** - Telegram Bot API
* **BeautifulSoup4** - Web scraping
* **Requests** - HTTP istekleri
* **SQLAlchemy** - ORM
* **SQLite** - Local development database
* **PostgreSQL** - Production database
* **Render** - Hosting ve deployment
* **UptimeRobot** - Monitoring

---

## ☁️ Production

İtobot production ortamında:

```text
FIRST Inspires
      ↓
   Scraper
      ↓
 PostgreSQL
      ↓
 Telegram Bot
      ↓
 Abone Kullanıcılar
```

mimarisiyle çalışır.

Bot, Render üzerinde sürekli çalışacak şekilde yapılandırılmıştır ve health-check endpoint'i üzerinden izlenebilir.

---

## 📧 Destek

Sorunlar, öneriler veya geliştirme fikirleri için:

**GitHub Issues:**
https://github.com/EmirhannCoskun/frc-grant-tracker/issues

---

## 🙏 Teşekkürler

* [python-telegram-bot](https://python-telegram-bot.readthedocs.io/) - Telegram Bot API
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - Web scraping
* [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
* [FIRST Inspires](https://www.firstinspires.org/) - Grant opportunities

---

<div align="center">

Made with by Team İTOBOT

**⭐ Bu projeyi beğendiysen yıldız atabilirsin!**

</div>
