# Release Notes

## v0.2.0 — Operational Grant Notifications

Status: release-ready; tag, Git push ve production deploy yapılmadı.

Bu operasyonel ara sürüm, mevcut grant scraper ve Telegram davranışını koruyarak
yeni grant'ler için opsiyonel text e-posta bildirimi ekler.

### Eklenenler

- Runtime environment üzerinden `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
  `SMTP_PASSWORD`, `SMTP_FROM` ve `SMTP_TO` konfigürasyonu.
- Güvenli varsayılan STARTTLS ve provider gereksinimleri için implicit SSL desteği.
- Açık, pozitif ve varsayılan 10 saniyelik SMTP network timeout'u.
- Grant başlığı, deadline varsa bitiş tarihi, URL ve mevcutsa kısa açıklama içeren
  text e-posta.
- Timeout, authentication ve diğer SMTP hatalarında credential içermeyen hata logu.
- Gerçek SMTP servisine bağlanmayan deterministic test kapsamı.

### Failure semantics ve bilinen sınırlamalar

- E-posta gönderimi best-effort'tur; SMTP hatası bot process'ini veya mevcut Telegram
  bildirim yolunu durdurmaz.
- Notification fan-out henüz durable/atomic değildir.
- Durable outbox çözümü architecture roadmap'indeki Transactional Outbox görevlerinde
  kalır.

Bu sürüm database schema veya migration içermez.
