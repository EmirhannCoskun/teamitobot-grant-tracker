# 🤖 İtobot - FIRST Robotics Grant Tracker

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12.x-blue)

![Status](https://img.shields.io/badge/Status-Active-brightgreen)

**FIRST Robotics hibe fırsatlarını otomatik olarak takip eden Telegram botu**

[Hızlı Başlangıç](#-hızlı-başlangıç) • [Özellikler](#-özellikler) • [Çalışma Mantığı](#-çalışma-mantığı) • [Kurulum](#-kurulum) • [Bot Komutları](#-bot-komutları)

</div>

---

## 📋 Nedir?

**İtobot Grant Tracker**, FIRST Inspires web sitesinde yayınlanan **FRC hibe fırsatlarını otomatik olarak takip eden** ve yeni fırsatlar yayınlandığında Telegram üzerinden **bildirim gönderen** bir bot uygulamasıdır.

Bot, FIRST'in hibe fırsatları sayfasını **15 dakikada bir** kontrol eder. Yeni bir FRC hibesi tespit edildiğinde hibenin:

* Başlığını
* Başlangıç tarihini
* Bitiş tarihini
* Doğrudan başvuru bağlantısını

PostgreSQL veritabanına kaydeder ve abone olan kullanıcılara bildirir.

Kullanıcıların herhangi bir kod değişikliği yapmasına gerek yoktur. Telegram'da botu açıp `/start` komutunu kullanmaları yeterlidir.

---

## ✨ Özellikler

* 🔍 **Otomatik Tarama** - FIRST hibe portalını 15 dakikada bir kontrol eder
* 🚨 **Otomatik Bildirim** - Yeni FRC hibeleri bulunduğunda abone kullanıcılara Telegram bildirimi gönderir
* 🔗 **Doğrudan Başvuru Linki** - Bildirimlerde ilgili hibenin başvuru bağlantısı bulunur
* 📅 **Hibe Tarihleri** - Başlangıç ve bitiş tarihleri bildirimlerde gösterilir
* 👥 **Çok Kullanıcı Desteği** - Birden fazla kullanıcı aynı botu kullanabilir
* 📊 **Kişisel İstatistikler** - Kullanıcılar aldıkları hibe bildirimlerini görüntüleyebilir
* 🟢 **Bot Durumu** - Aktif kullanıcı sayısı, abonelik durumu ve sistem durumu görüntülenebilir
* ⏱️ **Sonraki Tarama** - Bir sonraki otomatik taramaya kalan süre görüntülenebilir
* 📈 **Son Tarama ve Çalışma Süresi** - Botun son tarama zamanı ve mevcut çalışma süresi görüntülenebilir
* 🔔 **Abonelik Yönetimi** - Bildirimler istenildiğinde açılıp kapatılabilir
* 🛡️ **Tekrarlı Bildirim Önleme** - Aynı hibe aynı kullanıcıya tekrar tekrar gönderilmez
* ☁️ **Production Ready** - Render ve PostgreSQL üzerinde çalışacak şekilde yapılandırılmıştır
* ❤️ **Graceful Shutdown** - Bot kapatılırken devam eden görevler kontrollü şekilde sonlandırılır

---

## ⚙️ Çalışma Mantığı

İtobot sürekli olarak aşağıdaki akışla çalışır:

```text
                    FIRST Inspires
                          │
                          ▼
                   ┌───────────┐
                   │  Scraper  │
                   └─────┬─────┘
                         │
                  Hibe bilgileri
                         │
                         ▼
                ┌─────────────────┐
                │ Yeni hibe kontrol│
                └────────┬────────┘
                         │
                    Yeni hibe?
                   ┌─────┴─────┐
                   │           │
                 Hayır         Evet
                   │           │
                   │           ▼
                   │    PostgreSQL'e kaydet
                   │           │
                   │           ▼
                   │    Abone kullanıcıları bul
                   │           │
                   │           ▼
                   │    Pending bildirim oluştur
                   │           │
                   │           ▼
                   │     Telegram bildirimi
                   │           │
                   │           ▼
                   │     Gönderildi olarak işaretle
                   │
                   └──────────────►
                          │
                          ▼
                    15 dakika bekle
                          │
                          └──────► Tekrar tara
```

### Hibe tespit sistemi

Bir hibenin daha önce görülüp görülmediği kontrol edilirken hibenin:

* **Başlığı**
* **Başlangıç tarihi**
* **Bitiş tarihi**

birlikte değerlendirilir.

Bu sayede yalnızca başlığa bakılarak farklı tarih aralığına sahip hibelerin yanlış şekilde aynı hibe kabul edilmesi önlenir.

Ayrıca aynı kullanıcı için aynı hibe hakkında birden fazla bildirim oluşturulması veritabanı seviyesinde de engellenir.

---

## ⚡ Hızlı Başlangıç

### 30 saniyede başla

```text
1. Telegram'da arama kısmına @itobot_grant_tracker_bot yaz

2. /start komutunu gönder

3. "📨 Abone Ol" butonuna bas

4. Tamamlandı! ✅
```

Bundan sonra yeni FRC hibe fırsatları bulunduğunda Telegram üzerinden bildirim alırsınız.

---

## 🤖 Bot Komutları

Bot içerisindeki temel işlemler butonlar üzerinden yapılır.

| Buton                    | Açıklama                                                          |
| ------------------------ | ----------------------------------------------------------------- |
| 📨 **Abone Ol**          | Yeni hibe bildirimlerini almaya başla                             |
| ❌ **Abone Olmaktan Çık** | Hibe bildirimlerini durdur                                        |
| ⏱️ **Sonraki Tarama**    | Bir sonraki otomatik taramaya kalan süreyi göster                 |
| 📈 **İstatistik**        | Kişisel bildirim ve bot istatistiklerini göster                   |
| 🟢 **Durum**             | Aktif kullanıcı sayısı, abonelik durumu ve sistem durumunu göster |
| ❓ **Yardım**             | Botun kullanım bilgilerini göster                                 |

---

## 📊 İstatistikler

Bot iki farklı istatistik görünümü sunar.

### 📈 İstatistik

Kullanıcılar:

* 📨 Aldıkları hibe bildirimlerinin sayısını
* 🕐 Botun son başarılı tarama zamanını
* ⏱️ Botun mevcut çalışma süresini

görebilir.

### 🟢 Bot Durumu

Genel sistem durumu:

* 👥 Aktif kullanıcı sayısı
* 🔔 Kullanıcının abonelik durumu
* 🔍 Toplam başarılı tarama sayısı
* ⚙️ Sistem çalışma durumu

görüntülenebilir.

Başarısız scraper çalışmaları toplam başarılı tarama sayısına dahil edilmez.

---

## 📁 Proje Yapısı

```text
frc-grant-tracker/

│
├── 📄 bot.py                 ← Ana Telegram botu
├── 📄 database.py            ← PostgreSQL modelleri ve işlemleri
├── 📄 scraper.py             ← FIRST hibe scraper'ı
├── 📄 config.py              ← Konfigürasyon yönetimi
│
├── 📄 .env                   ← Environment değişkenleri
├── 📄 .gitignore             ← Git ignore kuralları
├── 📄 requirements.txt       ← Python bağımlılıkları
├── 📄 Procfile               ← Render deployment
│
├── 📚 Dokümantasyon
│   ├── README.md             ← Bu dosya
│   ├── QUICK_START.md        ← Hızlı başlangıç
│   ├── SETUP-GUIDE.md        ← Detaylı kurulum
│   └── SECURITY.md           ← Güvenlik bilgileri
```

Production ortamında tüm kalıcı veriler **PostgreSQL** üzerinde tutulur.

---

## 🔐 Güvenlik

* ✅ Telegram bot token'ı environment değişkeni üzerinden okunur
* ✅ Secret değerler GitHub repository'sine commit edilmez
* ✅ Environment değişkenleri production configuration için kullanılır
* ✅ SQLAlchemy ORM kullanılır
* ✅ PostgreSQL production veritabanı olarak kullanılır
* ✅ Veritabanı kimlik bilgileri kaynak kodundan ayrı tutulur

### ❌ Asla

Bot token'ını, database şifresini veya diğer secret bilgileri GitHub repository'sine commit etmeyin.

---

## 🛠️ Teknolojiler

* **Python 3.12.x** - Desteklenen çalışma zamanı
* **python-telegram-bot** - Telegram Bot API
* **BeautifulSoup4** - Web scraping
* **Requests** - HTTP istekleri
* **SQLAlchemy** - ORM
* **PostgreSQL** - Veritabanı
* **Render** - Hosting ve deployment
* **UptimeRobot** - Monitoring

---

## 🧪 Geliştirme ve Test

Desteklenen çalışma zamanı **Python 3.12.x**'tir (bkz. `.python-version`).

Temiz bir checkout'ta kurulum, compile, Ruff format, Ruff lint, production kritik
lint ve fast pytest kontrollerinin tamamını tek cross-platform komutla çalıştırın:

```bash
python scripts/quality.py
```

GitHub Actions da `main`'e açılan her pull request için aynı canonical quality
entrypoint'i çalıştırır. Merge engellemesi repository branch protection/ruleset
ayarındaki required `fast-checks` status check'ine bağlıdır.

### PostgreSQL Test Altyapısı

`tests/postgres/` altındaki testler gerçek, izole bir PostgreSQL'e ihtiyaç duyar
ve `TEST_DATABASE_URL` tanımlı değilse otomatik olarak atlanır — `scripts/quality.py`
akışını etkilemezler.

Lokalde çalıştırmak için:

```bash
docker compose -f docker-compose.test.yml up -d
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/itobot_test python -m pytest tests/postgres -q
```

CI aynı testleri `postgres:16` service container'ı ile çalıştırır. Bu sürüm,
production'daki gerçek PostgreSQL major sürümü GRANT-09 kapsamında kayıt altına
alınana kadar geçici bir varsayımdır; kayıt netleşince burada ve CI'da güncellenmelidir.

`TEST_DATABASE_URL` yalnızca `localhost`/`127.0.0.1` host'una ve adında `test`
geçen bir veritabanına işaret edebilir; aksi halde testler production'a
yanlışlıkla bağlanmayı önlemek için hemen hata verir.

---

## ☁️ Production

İtobot production ortamında Render üzerinde sürekli çalışacak şekilde yapılandırılmıştır.

```text
┌─────────────────────┐
│   FIRST Inspires    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Scraper       │
│       Render        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     PostgreSQL      │
│       Render        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Telegram Bot     │
│       Render        │
└──────────┬──────────┘
           │
           ▼
     Abone Kullanıcılar
```

Bot ayrıca Render health-check sistemi tarafından kontrol edilebilen bir HTTP health endpoint'i çalıştırır.

### Production davranışı

* 🔍 Hibe sayfası **15 dakikada bir** kontrol edilir
* 🟢 Başarılı taramalar istatistiklere eklenir
* ⚠️ Başarısız taramalar başarılı tarama sayısına eklenmez
* 🚨 Yeni hibeler abone kullanıcılara bildirilir
* 🔁 Başarısız Telegram gönderimleri daha sonra tekrar denenebilir
* 🛑 Render tarafından gönderilen SIGTERM sinyali kontrollü şekilde işlenir

---

## 📧 İletişim

Sorular, öneriler veya geliştirme fikirleri için:

**E-posta:**

[iletisimemirhancoskun@gmail.com](mailto:iletisimemirhancoskun@gmail.com)

---

## 🙏 Teşekkürler

* [python-telegram-bot](https://python-telegram-bot.readthedocs.io/) - Telegram Bot API
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - Web scraping
* [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
* [FIRST Inspires](https://www.firstinspires.org/) - Grant opportunities

---

<div align="center">

**Made with ❤️ by Team İTOBOT**

**⭐ Bu projeyi beğendiysen yıldız atabilirsin!**

</div>
```
