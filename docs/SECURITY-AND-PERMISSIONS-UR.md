# Zentrix Device Connect — سیکیورٹی اور اجازتوں کی دستاویز

## 1. مقصد اور دائرۂ کار

یہ دستاویز موجودہ Flask سرور میں authentication، authorization، device tokens، consent، audit logging اور ڈیٹا کے تحفظ کا جائزہ دیتی ہے۔

یہ implementation documentation ہے، مکمل security certification نہیں۔ جہاں کوئی حفاظتی سہولت موجودہ code سے ثابت نہیں، وہاں اسے implemented نہیں سمجھا جائے گا۔

## 2. بنیادی سیکیورٹی ماڈل

نظام میں دو بنیادی قسم کی درخواستیں ہیں:

- Admin Browser: منتظم کی session کے ذریعے محفوظ routes استعمال کرتا ہے۔
- Device API Client: device token کے ذریعے مجاز API routes استعمال کرتا ہے۔

SQLite ڈیٹا محفوظ کرنے کے لیے استعمال ہوتا ہے۔ مکمل Android application اس repository میں موجود نہیں؛ اس لیے Android-side permissions اور device security کو مکمل طور پر verify نہیں کیا جا سکتا۔

## 3. Admin Authentication

موجودہ implementation کے مطابق:

1. منتظم `/login` پر username اور password جمع کرتا ہے۔
2. سرور credentials کی تصدیق کرتا ہے۔
3. password hash کی تصدیق Werkzeug کے ذریعے ہوتی ہے۔
4. کامیابی پر session میں `admin_username` محفوظ ہوتا ہے۔
5. محفوظ admin routes session کی موجودگی چیک کرتے ہیں۔
6. `/logout` session صاف کرتا ہے۔

### ضروری حفاظتی اقدامات

- مضبوط اور منفرد admin password استعمال کریں۔
- `FLASK_SECRET_KEY` کے لیے طویل، بے ترتیب اور خفیہ value مقرر کریں۔
- development secret کو production میں استعمال نہ کریں۔
- login rate limiting اور ناکام کوششوں کی نگرانی شامل کریں۔
- session cookie کے لیے `Secure`، `HttpOnly` اور مناسب `SameSite` settings کا جائزہ لیں۔
- تمام حساس تبدیلیوں پر CSRF protection نافذ ہونے کی تصدیق کریں۔

ان میں سے کسی سہولت کو صرف سفارش کی بنیاد پر implemented نہ سمجھیں؛ متعلقہ code اور deployment settings الگ verify کرنا ضروری ہے۔

## 4. Device Token Security

موجودہ device authentication میں:

- device token کو سرور پر SHA-256 hash کی صورت میں محفوظ کیا جاتا ہے۔
- API درخواست میں `Authorization: Bearer <token>` استعمال ہوتا ہے۔
- token کی تصدیق کے لیے constant-time comparison استعمال ہوتی ہے۔
- token خفیہ اور بے ترتیب انداز میں بنایا جاتا ہے۔
- device disabled ہونے پر اس کی token-authenticated درخواستیں مسترد ہونی چاہییں۔
- کامیاب device request پر `last_seen` اپ ڈیٹ ہوتا ہے۔

### حفاظتی اصول

- raw device token کو logs، screenshots، Git یا عام reports میں محفوظ نہ کریں۔
- token صرف محفوظ اور مجاز منتظم کو دکھائیں۔
- token کے افشا ہونے کی صورت میں revocation یا rotation کا طریقہ درکار ہے۔
- production میں HTTPS استعمال کریں۔
- `last_seen` کو حقیقی وقت میں device کے آن لائن ہونے کا قطعی ثبوت نہ سمجھیں۔

## 5. Authorization اور Feature Flags

موجودہ نظام میں admin session اور device token الگ مقاصد کے لیے استعمال ہوتے ہیں۔

Feature flags میں یہ نام شامل ہیں:

- `storage_audit`
- `content_audit`
- `file_transfer`

سرور بعض کارروائیوں سے پہلے متعلقہ feature flag چیک کرتا ہے۔

Feature flag فعال ہونے کا مطلب یہ نہیں کہ اس نام سے متعلق مکمل فعالیت تیار ہے۔ خصوصاً file transfer کے لیے حقیقی file-content transfer pipeline مکمل ہونے کی تصدیق نہیں۔

## 6. Candidate Consent اور Permissions

Candidate link workflow میں:

1. منتظم candidate link بنا سکتا ہے۔
2. candidate ہدایات پڑھتا اور consent جمع کرتا ہے۔
3. browser permission status کی رپورٹ بھیج سکتا ہے۔
4. سرور consent اور link کی validity کے متعلق checks کرتا ہے۔
5. submission کو database میں محفوظ کیا جا سکتا ہے۔

### اہم حدود

- Browser کی بھیجی ہوئی permission report client-supplied data ہے۔
- یہ cryptographic proof نہیں کہ کسی permission کی حالت آزادانہ طور پر verify کی گئی ہے۔
- browser permissions پورے فون کے contacts، storage یا دیگر apps تک مکمل رسائی کا ثبوت نہیں۔
- حساس فائلوں کے لیے واضح، مخصوص اور باخبر رضامندی درکار ہے۔
- candidate link کی مدت، رسائی، revocation اور ممکنہ افشا ہونے کے خطرات کا جائزہ ضروری ہے۔

## 7. Audit Logging

`modules/audit_log.py` میں audit events درج کرنے کا طریقہ موجود ہے۔

Audit events انتظامی اور متعلقہ نظامی کارروائیوں کی traceability کے لیے استعمال ہوتے ہیں۔

### حدود اور احتیاطیں

- Audit log میں passwords، raw tokens یا غیر ضروری حساس file contents شامل نہ کریں۔
- صرف event کا ریکارڈ ہونا tamper-proof logging کی ضمانت نہیں۔
- SQLite میں موجود audit records کو database تک رسائی رکھنے والا شخص تبدیل کر سکتا ہے، جب تک الگ حفاظتی کنٹرول موجود نہ ہوں۔
- حساس واقعات، ناکام authentication اور غیر مجاز کوششوں کی logging کا الگ جائزہ ضروری ہے۔
- production میں log retention، backup اور access control کی پالیسی مقرر کریں۔

## 8. Database اور Secrets

موجودہ database path کی default value `instance/zentrix_modular.db` ہے، اور اسے `DATABASE_PATH` کے ذریعے تبدیل کیا جا سکتا ہے۔

درج ذیل معلومات Git repository میں شامل نہیں ہونی چاہییں:

- اصل `.env` فائل
- admin passwords یا ان کے قابلِ استعمال credentials
- raw device tokens
- حقیقی صارفین کی حساس معلومات
- نجی audit records اور غیر مجاز طور پر حاصل کردہ فائلیں
- production database اور اس کے backups

`.env.example` میں صرف placeholder values رکھیں۔ database backups کو محدود رسائی اور مناسب encryption کے ساتھ محفوظ کریں۔

## 9. Network اور API Security

Production deployment سے پہلے:

- HTTPS اور certificate validation یقینی بنائیں۔
- حساس endpoints کے لیے authentication اور authorization کی تصدیق کریں۔
- JSON payloads، item counts، string lengths اور request sizes کی حدود برقرار رکھیں۔
- غلط input پر محفوظ اور واضح error responses دیں۔
- secrets اور tokens کو URL query parameters میں نہ رکھیں۔
- debug mode بند رکھیں۔
- dependency updates اور security advisories کا جائزہ لیں۔
- server کو غیر ضروری طور پر public internet پر expose نہ کریں۔

## 10. File Metadata اور حقیقی File Transfer میں فرق

موجودہ manifest endpoint file metadata وصول کرتا ہے، مثلاً relative path، size اور دستیاب hash information۔

یہ endpoint بذاتِ خود اصل file bytes وصول نہیں کرتا۔

Transfer request database میں pending record بنا سکتی ہے، لیکن اس سے حقیقی transfer مکمل ہونے کا ثبوت نہیں ملتا۔

مکمل file transfer کے لیے الگ سے device-side consent، مجاز file selection، secure upload، size اور hash verification، error handling اور completion status درکار ہیں۔

## 11. موجودہ حدود اور Production Readiness

موجودہ repository کی دستاویزات اور implementation کے مطابق:

- مکمل Android APK یا Android source یہاں شامل نہیں۔
- مکمل Android permission enforcement کی تصدیق نہیں کی جا سکتی۔
- push notification delivery کو مکمل implemented نہیں سمجھنا چاہیے۔
- حقیقی file-content transfer pipeline مکمل نہیں۔
- browser permission report آزادانہ verification کا متبادل نہیں۔
- CSRF protection، rate limiting، session-cookie settings اور production deployment controls کا الگ جائزہ ضروری ہے۔
- کامیاب automated tests مکمل security audit یا production readiness کی ضمانت نہیں۔

## 12. حفاظتی جانچ کی چیک لسٹ

Production سے پہلے ہر نکتے کو code، configuration اور حقیقی ماحول میں verify کریں۔

- [ ] مضبوط `FLASK_SECRET_KEY` مقرر ہے۔
- [ ] `.env`، database اور secrets Git سے خارج ہیں۔
- [ ] Admin password hashing اور login failure handling آزمائی گئی ہے۔
- [ ] Login rate limiting نافذ اور آزمائی گئی ہے۔
- [ ] CSRF protection کی جانچ مکمل ہے۔
- [ ] Session cookie کی settings verify کی گئی ہیں۔
- [ ] HTTPS اور محفوظ reverse-proxy configuration درست ہے۔
- [ ] Device token authentication اور disabled-device behavior آزمائے گئے ہیں۔
- [ ] Tokens کے افشا ہونے کی صورت میں revocation کا طریقہ موجود ہے۔
- [ ] Admin اور device permissions کے negative tests مکمل ہیں۔
- [ ] Audit logs میں secrets یا غیر ضروری حساس معلومات نہیں۔
- [ ] Database backup، access control اور recovery آزمائے گئے ہیں۔
- [ ] File metadata کو حقیقی file-content transfer سے الگ رکھا گیا ہے۔
- [ ] Android client کی حقیقی device testing مکمل ہے۔
- [ ] Production security review مکمل ہے۔

## 13. حتمی نتیجہ

یہ دستاویز موجودہ سرور کے حفاظتی طریقوں اور ان کی حدود کو واضح کرتی ہے۔ کسی feature کو production-ready قرار دینے سے پہلے اس کی implementation، configuration، tests اور حقیقی deployment کی الگ تصدیق ضروری ہے۔
