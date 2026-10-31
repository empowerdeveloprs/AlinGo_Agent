# AlinGo Device Connect — Modular Source Package

یہ پیکج ماڈیولر بنیاد فراہم کرتا ہے۔ اس میں سرور، Android source layout، دستاویزات اور ٹیسٹ الگ رکھے گئے ہیں۔

## اہم حقیقت
یہ ZIP ایک **قابلِ جائزہ modular starter** ہے، مکمل production-certified نظام نہیں۔ Android APK شامل نہیں، کیونکہ اسے Android SDK/Gradle ماحول میں build اور test کرنا باقی ہے۔ ڈیوائس اسٹوریج کی رسائی Android کی اجازتوں اور OS حدود کے تابع ہے۔

## اجزاء
- `server/`: Flask server، الگ routes/services/models اور SQLite schema۔
- `android/`: موجودہ Android source کی architecture guide اور ماڈیولز کی جگہیں۔
- `docs/`: architecture، permissions، audit workflow، backup، build notes۔
- `tests/`: سرور کے بنیادی health/schema tests۔

## سرور چلانا
Python 3.11+ تجویز کردہ ہے:
```bash
cd server
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```
پہلی مرتبہ ایڈمن اکاؤنٹ خود بنائیں:
```bash
python create_admin.py
```
پھر `http://127.0.0.1:5000` کھولیں۔

## حفاظتی اصول
- `.env`، ڈیٹابیس، session secret یا اصل device tokens کو ZIP/Git میں شامل نہ کریں۔
- ہر ڈیوائس کا الگ token رکھیں اور اسے revoke کرنے کی صلاحیت رکھیں۔
- صرف پہلے سے منظور شدہ دائرے میں آڈٹ کریں۔
- فائل کا مواد منتقل کرنے اور صرف metadata/hash پڑھنے کو الگ کارروائیاں سمجھیں۔
- نوٹیفکیشن اطلاع ہے؛ یہ Android permissions کا متبادل نہیں۔
