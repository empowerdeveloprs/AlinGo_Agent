# Zentrix Device Connect — ڈیٹا فلو اور ورک فلو

## 1. مقصد

یہ دستاویز Flask سرور میں درخواستوں، تصدیق، ڈیٹا بیس اور response کے بہاؤ کی وضاحت کرتی ہے۔ یہ موجودہ سرور implementation کی دستاویز ہے؛ مکمل Android client workflow کا دعویٰ نہیں۔

## 2. عمومی System Architecture

```text
                    +----------------------+
                    |    Admin Browser     |
                    | Login / Dashboard     |
                    +----------+-----------+
                               |
                               | HTTP Request
                               v
                    +----------------------+
                    | Flask App (app.py)   |
                    +----------+-----------+
                               |
                  +------------+-------------+
                  |                          |
                  v                          v
       +---------------------+    +----------------------+
       | Admin Blueprints    |    | Device API Routes    |
       | Session validation  |    | Bearer token checks  |
       +----------+----------+    +-----------+----------+
                  |                           |
                  +-------------+-------------+
                                |
                                v
                    +----------------------+
                    | SQLite Database      |
                    | modules/db.py        |
                    +----------+-----------+
                               |
                    +----------+-----------+
                    |                      |
                    v                      v
           +----------------+     +------------------+
           | Business Data  |     | Audit Events     |
           +----------------+     +------------------+

       Device Client / Android App
       اس repository میں مکمل Android APK شامل نہیں۔

```

## 3. Admin Login Flow

1. Browser "/login" پر login page کھولتا ہے۔
2. Admin username اور password جمع کرتا ہے۔
3. "modules/auth.py" محفوظ شدہ credentials کی تصدیق کرتا ہے۔
4. کامیابی پر session میں "admin_username" محفوظ کیا جاتا ہے۔
5. Admin-protected routes session کی تصدیق کرتے ہیں۔
6. "/logout" session صاف کرتا ہے۔

حد: Production deployment سے پہلے CSRF protection، login rate limiting اور session-cookie settings کا جائزہ ضروری ہے۔

## 4. Device Authentication Flow

1. Device API request میں "Authorization: Bearer <token>" بھیجتا ہے۔
2. "modules/security.py" token کی تصدیق کرتا ہے۔
3. غلط token یا disabled device کی درخواست مسترد ہو سکتی ہے۔
4. درست device request پر "last_seen" اپ ڈیٹ کیا جاتا ہے۔
5. متعلقہ endpoint payload validation اور feature checks کے بعد کارروائی کرتا ہے۔
6. نتیجہ API response میں واپس بھیجا جاتا ہے۔

"last_seen" ایک server-side timestamp ہے۔ اسے مسلسل connectivity یا device کے حقیقی وقت میں آن لائن ہونے کا قطعی ثبوت نہ سمجھیں۔

## 5. Survey Flow

1. مجاز device enabled surveys حاصل کرنے کی درخواست کرتا ہے۔
2. Server enabled survey records واپس کرتا ہے۔
3. Device survey response متعلقہ API endpoint کو بھیج سکتا ہے۔
4. Server بنیادی validation کرتا ہے۔
5. درست response database میں محفوظ کیا جاتا ہے۔
6. Admin API کے ذریعے survey responses دیکھ سکتا ہے۔

موجودہ implementation مکمل visual form builder یا ہر قسم کے سوال کے لیے جامع validation فراہم نہیں کرتی۔

## 6. Audit Request Flow

1. Admin کسی device کے لیے audit request بناتا ہے۔
2. Server admin permission، device status اور متعلقہ feature flag چیک کرتا ہے۔
3. Request queue میں محفوظ ہوتی ہے۔
4. متعلقہ audit event بھی درج کیا جا سکتا ہے۔
5. Device client pending requests endpoint سے request حاصل کر سکتا ہے۔
6. Device client نتیجہ بھیجے تو server اسے متعلقہ request کے ساتھ محفوظ کرتا ہے۔

اہم فرق: Server پر queue موجود ہونے کا مطلب یہ نہیں کہ Android notification پہنچ گئی، device نے request وصول کی یا کارروائی مکمل کر لی۔

## 7. Candidate Link اور Consent Flow

1. Admin candidate link بناتا ہے۔
2. Candidate link کھول کر SOP پڑھتا ہے۔
3. Candidate consent جمع کرتا ہے۔
4. Browser permission status کی رپورٹ بھیج سکتا ہے۔
5. Candidate submission endpoint پر جواب جمع کرتا ہے۔
6. Server link کی validity، consent اور submission rules چیک کرتا ہے۔
7. پہلی submission محفوظ ہوتی ہے؛ duplicate submission مسترد ہو سکتی ہے۔

Browser سے موصول ہونے والی permission report client-supplied data ہے۔ اسے آزاد cryptographic proof یا پورے فون کی permissions کا ثبوت نہیں سمجھنا چاہیے۔

## 8. File Metadata Manifest Flow

1. مجاز device client metadata manifest بھیجتا ہے۔
2. Server device token، feature flag، consent-related fields، payload size اور item count چیک کرتا ہے۔
3. Relative paths اور metadata کی validation ہوتی ہے۔
4. Manifest اور اس کے metadata items SQLite میں محفوظ ہوتے ہیں۔
5. Server response میں "content_received: false" واپس کرتا ہے۔

یہ عمل metadata وصول کرتا ہے؛ یہ بذاتِ خود فائلوں کا اصل content upload نہیں کرتا۔

## 9. Transfer Request Flow

1. Admin کسی manifest item کے لیے transfer request بنا سکتا ہے۔
2. Server item، device اور متعلقہ feature status چیک کرتا ہے۔
3. Database میں pending transfer record بنایا جا سکتا ہے۔
4. یہ record ایک درخواست کی نمائندگی کرتا ہے، مکمل transfer کی نہیں۔

حقیقی file bytes upload، chunking، device-side approval، hash verification اور transfer completion کے لیے اضافی implementation درکار ہے۔

## 10. Database اور Audit Events

"modules/db.py" SQLite schema، tables، indexes اور ابتدائی feature flags تیار کرتا ہے۔

اہم tables:

- "admins"
- "devices"
- "surveys"
- "survey_responses"
- "audit_requests"
- "audit_events"
- "candidate_links"
- "file_audit_manifests"
- "file_audit_items"
- "file_transfers"
- "feature_flags"

Audit events متعلقہ انتظامی اور نظامی کارروائیوں کا ریکارڈ رکھنے کے لیے استعمال ہوتے ہیں۔

Local database، passwords، tokens اور دیگر حساس credentials کو Git repository میں شامل نہ کریں۔

## 11. موجودہ Implementation کی حدود

- مکمل Android APK یا Android source اس repository میں شامل نہیں۔
- Push notification delivery مکمل ہونے کی تصدیق نہیں۔
- Device-side scanner اور background processing مکمل نہیں۔
- حقیقی file-content transfer pipeline مکمل نہیں۔
- Metadata manifest کو file-content transfer نہ سمجھیں۔
- End-to-end Android integration کے لیے الگ client اور حقیقی device testing درکار ہے۔

## 12. Tests کی حیثیت

اس منصوبے کے سابقہ test run میں 43 tests کامیاب ہوئے تھے۔ یہ نتیجہ صرف ان tests کی حدود تک ہے؛ اسے production security audit، Android integration test یا مکمل file-transfer verification نہ سمجھا جائے۔
