# Token Setup and Validation

Bu doküman, İTOBOT Grant Tracker için Telegram bot token'ının canonical yapılandırma ve doğrulama akışını tanımlar.

## 1. Canonical Secret Flow

Telegram bot token'ı uygulamanın configuration kaynağıdır ve runtime environment üzerinden sağlanır.

Canonical akış:

```text
Telegram / BotFather
        │
        │ Bot token
        ▼
Deployment Provider / Secret Store
        │
        │ TELEGRAM_BOT_TOKEN
        ▼
Process Environment
        │
        ▼
Application Bootstrap
        │
        ▼
Typed Settings
```

Production ortamında `TELEGRAM_BOT_TOKEN` provider'ın environment/secret mekanizması üzerinden tanımlanmalıdır.

Token:

* source code içine yazılmamalıdır.
* Git repository'sine commit edilmemelidir.
* README, issue, log veya test çıktısına yazılmamalıdır.
* command-line argümanı olarak verilmemelidir.
* kalıcı bir token dosyasına yazılmamalıdır.

`TELEGRAM_BOT_TOKEN` uygulama tarafından startup sırasında environment'tan okunur ve typed settings yapısına aktarılır.

Production ortamlarında `.env` dosyası configuration kaynağı değildir. Secret değerleri deployment provider'ın secret/environment yönetiminden sağlanmalıdır.

Development ortamında `.env` kullanılabilir; bu dosya yalnızca local development configuration akışının bir parçasıdır ve repository'ye commit edilmemelidir.

## 2. Required Environment Variable

| Variable             | Required | Description                           |
| -------------------- | -------- | ------------------------------------- |
| `TELEGRAM_BOT_TOKEN` | Yes      | Telegram Bot API authentication token |

Eksik veya geçersiz configuration uygulamanın startup sırasında non-zero exit ile durmasına neden olur.

Configuration hataları secret değerini göstermez. Yalnızca ilgili environment variable'ın adı raporlanabilir.

## 3. Optional Token Validator

Repository, token'ın Telegram Bot API tarafından kabul edilip edilmediğini kontrol etmek için non-persisting bir validator CLI içerir.

Çalıştırma:

```bash
python -m tools.token_setup
```

CLI yalnızca mevcut process environment'ındaki:

```text
TELEGRAM_BOT_TOKEN
```

değerini okur.

Validator:

1. Environment variable'ın mevcut olup olmadığını kontrol eder.
2. Token'ın yerel olarak tanınabilir Telegram token formatına uyup uymadığını kontrol eder.
3. Telegram Bot API `getMe` endpoint'ine istek gönderir.
4. Sonucu güvenli bir durum olarak sınıflandırır.
5. Token'ı hiçbir zaman stdout/stderr çıktısına yazmaz.
6. Token'ı dosyaya kaydetmez.
7. Token'ı validation sonucunda saklamaz.
8. Token'ı exception mesajına dahil etmez.

CLI, token kurulumunun zorunlu bir parçası değildir. Deployment provider'ın secret/environment yönetimi canonical configuration kaynağı olmaya devam eder.

## 4. Validation Results

Validator üç güvenli sonuç üretir.

### Valid

Telegram Bot API başarılı bir `getMe` yanıtı verdiğinde:

```text
Telegram bot token is valid.
```

process exit code:

```text
0
```

Bu sonuç, Telegram'ın verilen token'ı kabul ettiğini gösterir.

### Invalid

Telegram açıkça `401 Unauthorized` döndürürse token:

```text
invalid
```

olarak sınıflandırılır.

Aynı sınıflandırma yerel token formatı geçersiz olduğunda veya token hiç sağlanmadığında da kullanılır.

Process exit code:

```text
1
```

### Unavailable

Aşağıdaki durumlarda token'ın kendisinin geçersiz olduğu sonucuna varılmaz:

* network bağlantı hatası
* timeout
* Telegram server hatası
* rate limiting
* beklenmeyen HTTP yanıtı
* malformed API response

Bu durumda:

```text
Telegram Bot API could not be reached or returned an unexpected response.
```

mesajı verilir.

Process exit code:

```text
2
```

Bu ayrım önemlidir:

```text
401 Unauthorized
    → token geçersiz

Network / timeout / server / unexpected response
    → token'ın geçersiz olduğu kanıtlanmadı
```

Bir API outage veya network problemi yalnızca token problemi olarak raporlanmamalıdır.

## 5. Non-Disclosure Rules

Validator'ın temel güvenlik sözleşmesi token değerinin disclosure edilmemesidir.

Token:

* stdout'a yazılmaz.
* stderr'a yazılmaz.
* exception mesajına yazılmaz.
* validation result içinde tutulmaz.
* dosyaya yazılmaz.
* CLI argümanı olarak alınmaz.
* log mesajlarına dahil edilmez.

HTTP isteği oluşturulurken token geçici olarak Telegram API URL'sinin bir parçası olabilir; ancak bu URL hiçbir şekilde kullanıcıya gösterilmez veya kalıcı olarak saklanmaz.

Test suite bu davranışları özellikle doğrular.

## 6. File Creation Contract

Validator herhangi bir token dosyası oluşturmaz.

Özellikle aşağıdaki tipte bir workflow canonical değildir:

```text
token
  ↓
token.json
  ↓
Flask setup application
  ↓
bot
```

Token'ın plaintext dosyada saklanması bu repository'nin configuration mimarisiyle uyumlu değildir.

Validator'ın amacı token'ı **saklamak değil, doğrulamaktır**.

## 7. Deprecated Flask Token Setup

Eski Flask tabanlı token setup workflow'u canonical configuration kaynağı değildir.

Eski workflow'un temel problemi token'ın local plaintext dosyasına yazılması ve bunun runtime configuration mimarisiyle ayrışmasıdır.

Yeni canonical workflow:

```text
Provider Secret Store / Process Environment
                    │
                    ▼
              Application
```

Opsiyonel validation:

```text
Process Environment
        │
        ▼
Token Validator
        │
        ▼
Telegram getMe
```

Eski Flask/token-file workflow'u yeni deployment'larda kullanılmamalıdır.

Eski setup uygulamasının archive/delete işlemi ayrı bir repository/workflow kararıdır ve bu dokümanın kapsamında değildir.

## 8. Production Setup Checklist

Production deployment öncesinde:

* [ ] `TELEGRAM_BOT_TOKEN` provider secret/environment alanında tanımlandı.
* [ ] Token source code'a yazılmadı.
* [ ] Token repository'ye commit edilmedi.
* [ ] Token herhangi bir plaintext dosyaya yazılmadı.
* [ ] `DATABASE_URL` provider secret/environment alanında tanımlandı.
* [ ] Application startup configuration validation'dan geçiyor.
* [ ] Gerekirse `python -m tools.token_setup` ile token doğrulandı.
* [ ] Validator çıktısında token değeri bulunmadığı kontrol edildi.
* [ ] Eski Flask/token-file setup workflow'u production configuration kaynağı olarak kullanılmıyor.

## 9. Local Validation

Local validation yapılacaksa validator process environment'ındaki `TELEGRAM_BOT_TOKEN` değerini kullanır.

Secret değerini command-line argümanı olarak vermeyin.

Örneğin aşağıdaki kullanım canonical değildir:

```bash
python -m tools.token_setup 123456789:secret
```

Validator bu kullanım şeklini desteklemez.

Token, process environment üzerinden sağlanmalıdır.

Windows, Linux veya CI/CD ortamında environment variable'ın nasıl tanımlanacağı kullanılan shell, IDE veya deployment provider'a göre değişebilir. Önemli olan token'ın process environment'a secret olarak aktarılması ve command-line/history, source code veya repository dosyalarına yazılmamasıdır.

## 10. Verification

Token setup değişikliklerinden sonra repository quality gate çalıştırılmalıdır:

```bash
ruff check tools/token_setup tests/unit/test_token_setup.py
ruff format --check tools/token_setup tests/unit/test_token_setup.py
pytest -v
```

Beklenen sonuç:

* Ruff lint başarılı.
* Ruff format kontrolü başarılı.
* Token setup testleri başarılı.
* Full test suite başarısız olmamalı.

Token validator'ın davranışı özellikle aşağıdaki sözleşmelerle korunur:

* valid token → `VALID`
* explicit HTTP 401 → `INVALID`
* network/provider failure → `UNAVAILABLE`
* token disclosure → yasak
* token persistence → yasak
* token file creation → yasak
