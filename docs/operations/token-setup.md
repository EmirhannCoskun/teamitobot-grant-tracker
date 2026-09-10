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

Eski setup uygulamasının archive/delete işlemi, yeni canonical Render workflow'u production'da başarıyla doğrulandıktan sonra ve Software Captain onayıyla ayrı bir repository operasyonu olarak gerçekleştirilmelidir.

## 8. Production Render Operations

Production'daki canonical secret workflow, repository'deki Flask/file-based token setup workflow'undan bağımsız olarak Render environment/secret yönetimi üzerinden yürütülür.

### 8.1 Initial Secret Setup

Production Render service linked to this repository için:

1. Render Dashboard'da production service'i açın.
2. `Environment` bölümüne gidin.
3. Environment Variables altında `TELEGRAM_BOT_TOKEN` değişkenini ekleyin veya mevcut değeri güncelleyin.
4. Token değerini yalnızca Render'ın secret/environment alanına girin.
5. Değişiklik için `Save and deploy` seçeneğini kullanın. Secret değişikliğinin deploy edilmeden production runtime'a uygulanacağı varsayılmamalıdır.
6. Deploy tamamlandıktan sonra `Deploys` bölümünden ilgili deploy'un başarılı olduğunu doğrulayın.
7. Service logs içinde token değerinin görünmediğini kontrol edin.

Render'daki environment variable değişiklikleri için `Save and deploy` mevcut build'i yeni environment değerleriyle yeniden deploy eder. `Save only` seçilirse yeni değer bir sonraki deploy'a kadar service tarafından kullanılmaz.

### 8.2 Token Validation

Gerekirse token, controlled bir operator environment'ında non-persisting validator ile doğrulanabilir:

```bash
python -m tools.token_setup
```

Validator token'ı yalnızca `TELEGRAM_BOT_TOKEN` process environment'ından okur.

Token:

* command-line argument olarak verilmemelidir.
* shell history'ye yazılmamalıdır.
* source code'a veya repository dosyasına yazılmamalıdır.
* loglara veya deployment çıktısına yazılmamalıdır.

Production Render environment'ında token'ın kendisini loglamak veya ekrana çıkarmak yerine service'in başarılı şekilde deploy olup startup configuration validation'dan geçmesi doğrulanmalıdır.

### 8.3 Secret Rotation

Telegram bot token'ı rotate edilecekse:

1. Yeni token'ı Telegram tarafındaki yetkili bot yönetim workflow'u üzerinden oluşturun.
2. Render Dashboard'da production service'in `Environment` bölümünü açın.
3. `TELEGRAM_BOT_TOKEN` değerini yeni token ile değiştirin.
4. `Save and deploy` ile değişikliği production'a uygulayın.
5. Deploy'un başarılı olduğunu `Deploys` bölümünden doğrulayın.
6. Application logs içinde secret değerinin bulunmadığını kontrol edin.
7. Botun normal şekilde çalıştığını ve health/status kontrollerinin başarılı olduğunu doğrulayın.
8. Eski token'ın artık kullanılmadığından emin olun.

Yeni token production'da doğrulanmadan önce eski çalışan configuration kaldırılmamalıdır.

### 8.4 Rollback

Token değişikliği veya ilgili deployment production davranışını bozarsa:

* Öncelikle sorunun secret değerinden mi yoksa application deploy'undan mı kaynaklandığını ayırın.
* Yanlış veya kullanılamayan token söz konusuysa Render `Environment` bölümündeki `TELEGRAM_BOT_TOKEN` değerini son bilinen çalışan değerle değiştirin ve yeniden deploy edin.
* Kod değişikliği kaynaklı bir problem varsa Render `Deploys` bölümündeki son başarılı deploy'a rollback yapılabilir.
* Rollback sonrasında service'in tekrar çalıştığı ve health/status kontrollerinin başarılı olduğu doğrulanmalıdır.
* Sorun çözülmeden yeni production değişiklikleri uygulanmamalıdır.

Render Dashboard üzerinden önceki başarılı bir deploy'a rollback yapılabilir. Rollback yalnızca uygulama deploy'unu geri almak için kullanılmalı; secret rotation durumunda yanlış token'ın tekrar kullanılmasına neden olacak şekilde düşünülmemelidir.

### 8.5 Cutover from the Deprecated Workflow

Yeni canonical workflow production'da başarıyla doğrulanmadan eski Flask/file-based token setup workflow'u kaldırılmamalıdır.

Cutover sırası:

1. Render environment/secret configuration'ı tamamlayın.
2. Production service'i yeni canonical configuration ile deploy edin.
3. Startup configuration validation ve service health durumunu doğrulayın.
4. `TELEGRAM_BOT_TOKEN` değerinin yalnızca provider environment/secret yönetiminden geldiğini doğrulayın.
5. Production'ın Flask/token-file workflow'una bağımlı olmadığını doğrulayın.
6. Başarılı cutover sonrasında eski Flask/file-based setup workflow'unu production configuration kaynağı olarak tamamen devre dışı bırakın.
7. Eski setup repository'sinin archive veya delete edilmesi gerekiyorsa bu işlem Software Captain onayıyla ayrı bir repository operasyonu olarak gerçekleştirilmelidir.

Eski workflow, yeni canonical workflow başarıyla doğrulanmadan production'dan kaldırılmamalıdır.

### 8.6 Production Secret Checklist

Her secret kurulumu veya rotation işleminden sonra:

* [ ] `TELEGRAM_BOT_TOKEN` Render production service environment'ında tanımlı.
* [ ] Değişiklik `Save and deploy` ile production'a uygulandı.
* [ ] Deploy başarıyla tamamlandı.
* [ ] Service logs içinde token değeri bulunmuyor.
* [ ] Application startup configuration validation başarılı.
* [ ] Service health/status kontrolleri başarılı.
* [ ] Token command-line argument olarak kullanılmadı.
* [ ] Token repository veya plaintext dosyaya yazılmadı.
* [ ] Eski Flask/file-based workflow production configuration kaynağı olarak kullanılmıyor.
* [ ] Rotation işleminde eski tokenın kullanım durumu doğrulandı.


## 9. Production Setup Checklist

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

## 10. Local Validation

Local validation yapılacaksa validator process environment'ındaki `TELEGRAM_BOT_TOKEN` değerini kullanır.

Secret değerini command-line argümanı olarak vermeyin.

Örneğin aşağıdaki kullanım canonical değildir:

```bash
python -m tools.token_setup 123456789:secret
```

Validator bu kullanım şeklini desteklemez.

Token, process environment üzerinden sağlanmalıdır.

Windows, Linux veya CI/CD ortamında environment variable'ın nasıl tanımlanacağı kullanılan shell, IDE veya deployment provider'a göre değişebilir. Önemli olan token'ın process environment'a secret olarak aktarılması ve command-line/history, source code veya repository dosyalarına yazılmamasıdır.

## 11. Verification

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
