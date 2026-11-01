# Zentrix Device Connect — نظامی و فنکشنل گائیڈ

## 1. مقصد اور موجودہ حدود

یہ منصوبہ Flask اور SQLite پر مبنی ایک modular server prototype ہے۔
اس میں انتظامی لاگ اِن، ڈیوائس رجسٹریشن، survey APIs، candidate consent
links، audit-request queue، metadata manifests اور feature flags شامل ہیں۔

یہ مکمل production-certified نظام نہیں ہے۔ Android APK اس repository میں
شامل نہیں، اور server endpoints کی موجودگی Android client کی تکمیل کا ثبوت
نہیں ہے۔

## 2. نظام کے بنیادی اجزاء

| جزو | اصل مقام | ذمہ داری |
|---|---|---|
| App Factory | `app.py` | Flask configuration، DB initialization اور blueprint registration |
| Authentication | `modules/auth.py` | Admin login/logout اور session |
| Device Registry | `modules/devices.py` | ڈیوائس کی رجسٹریشن اور فہرست |
| Security | `modules/security.py` | Admin session اور device bearer-token checks |
| Surveys | `modules/surveys.py` | Survey listing، response submission اور basic administration APIs |
| Audit Requests | `modules/audit_requests.py` | Request queue، heartbeat اور result receipt |
| Dashboard | `modules/dashboard.py` | انتظامی browser dashboard |
| Admin Controls | `modules/admin.py` | Device connection toggle اور feature flags |
| Candidate Links | `modules/candidate_links.py` | Candidate links، consent، browser permission report اور submission |
| Device Manifest | `modules/device_file_audit.py` | فائلوں کے metadata manifest کا اندراج |
| File Audit | `modules/file_audit.py` | Manifest status/listing اور transfer-request record |
| Audit Log | `modules/audit_log.py` | Audit events درج کرنا |
| Database | `modules/db.py` | SQLite schema، indexes اور ابتدائی feature flags |

## 3. انتظامی لاگ اِن

`/login` پر GET/POST کے ذریعے login page اور credential verification دستیاب ہیں۔
کامیاب login کے بعد session میں `admin_username` رکھا جاتا ہے۔
Logout پر session صاف کیا جاتا ہے۔

Production استعمال سے پہلے CSRF protection، rate limiting، session settings
اور secret configuration کا جائزہ ضروری ہے۔

## 4. ڈیوائس رجسٹریشن اور شناخت

Admin device UID اور اختیاری label دے کر ڈیوائس رجسٹر کرتا ہے۔
Server ایک نیا token بناتا ہے اور database میں اس کا hash رکھتا ہے۔
اصل token صرف رجسٹریشن کے جواب میں دکھایا جاتا ہے؛ اسے محفوظ انداز میں
متعلقہ مجاز device client تک پہنچانا ضروری ہے۔

مجاز device requests میں bearer token validate کیا جاتا ہے اور
`last_seen` اپ ڈیٹ ہوتا ہے۔ Dashboard میں online/offline حالت
`DEVICE_OFFLINE_AFTER_SECONDS` کے مطابق نکالی جاتی ہے، جس کی default
قدر 90 سیکنڈ ہے۔ یہ server-side heuristic ہے، حقیقی connectivity کی ضمانت نہیں۔

## 5. Surveys

Admin APIs بنیادی survey records بنا اور فہرست کر سکتی ہیں۔
Device APIs enabled surveys حاصل کر سکتی ہیں اور survey response جمع کر سکتی ہیں۔
موجودہ schema validation بنیادی ہے؛ مکمل form builder یا وسیع field validation
فرض نہیں کی جانی چاہیے۔

## 6. Candidate links اور consent

Candidate link کے ذریعے SOP دکھایا جاتا ہے۔ Candidate سے consent اور browser
permission report طلب کی جا سکتی ہے، پھر ایک survey statement جمع ہو سکتی ہے۔
غلط، منسوخ یا expire شدہ link رد کیا جاتا ہے، اور پہلی submission کے بعد
دوبارہ submission روکنے کی guard موجود ہے۔

Browser کا permission report client کی طرف سے آتا ہے؛ اسے cryptographic proof
یا فون کی مکمل اجازتوں کا آزاد ثبوت نہ سمجھیں۔ Browser خود بخود تمام فائلوں،
contacts یا پورے فون تک رسائی نہیں دیتا۔

## 7. Audit request workflow

Admin مخصوص device کے لیے metadata یا content audit request بنا سکتا ہے،
اگر متعلقہ feature enabled ہو۔ Request queue میں آتی ہے۔ Device-side client
کو pending requests پڑھ کر اپنی پالیسی، consent اور platform permissions کے
مطابق فیصلہ کرنا ہوگا۔

Server میں queue اور result endpoint موجود ہونا اس بات کا ثبوت نہیں کہ
Android notification، scanner یا background processing مکمل ہے۔

## 8. File manifests اور transfer requests

Manifest endpoint منتخب فائلوں کا metadata وصول کرتا ہے، مثلاً relative path،
size، MIME type اور اختیاری SHA-256۔ Endpoint واضح طور پر content upload
نہیں کرتا؛ response میں `content_received: false` آتا ہے۔

Transfer request endpoint ایک pending record بنا سکتا ہے۔ حقیقی file bytes
کی upload، chunking، device-side approval، hash verification اور مکمل transfer
اس endpoint سے خودبخود مکمل نہیں ہوتے۔

## 9. Feature flags

Database میں ابتدائی flags `surveys`، `storage_audit`، `content_audit`
اور `file_transfer` موجود ہوتے ہیں۔ Admin ان کے enable/disable ہونے کو
کنٹرول کر سکتا ہے۔ ہر route پر enforcement کی تفصیل متعلقہ ماڈیول سے دیکھی جائے۔

## 10. Database

`modules/db.py` میں بنیادی tables یہ ہیں:

- `admins`
- `devices`
- `surveys`
- `survey_responses`
- `audit_requests`
- `audit_events`
- `candidate_links`
- `file_audit_manifests`
- `file_audit_items`
- `file_transfers`
- `feature_flags`

یہ schema مستقبل کے transfer statuses بھی رکھتا ہے؛ صرف status column کی
موجودگی کو اس feature کی تکمیل نہ سمجھیں۔

## 11. Implementation status

- Implemented: Flask app factory، admin login، device registry، بنیادی survey APIs،
  audit queue/result endpoints، feature flag APIs، candidate link flow،
  metadata manifest ingestion اور transfer request record۔
- Partial / Needs review: survey schema validation، production security hardening،
  token rotation/revocation workflow، candidate permission evidence اور UI coverage۔
- Planned / Not implemented in this repository: Android APK، Android scanner،
  push notification delivery، حقیقی file content transfer pipeline اور
  end-to-end device-side workflow۔

## 12. تصدیق

موجودہ ٹیسٹ suite میں 43 tests کامیاب ہوئے تھے۔ یہ نتیجہ ان tests کی حدود تک ہے؛
یہ production security audit یا Android device integration test نہیں ہے۔
