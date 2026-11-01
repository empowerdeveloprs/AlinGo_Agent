# Zentrix Device Connect — انٹرفیس گائیڈ

## 1. موجودہ Dashboard

Dashboard کا HTML/CSS/JavaScript `modules/dashboard.py` میں inline موجود ہے۔
یہ ایک browser-based administrative interface ہے۔ الگ `templates/` directory
یا مکمل native Android UI اس repository میں موجود نہیں۔

## 2. Login

- راستہ: `/login`
- مقصد: Admin credentials کی تصدیق
- کامیابی: Admin session قائم ہوتا ہے
- ناکامی: Login error/flash message
- Logout: `/logout` session صاف کرتا ہے

## 3. Dashboard کے حصے

| کنٹرول | کام | اہم حد |
|---|---|---|
| Device UID input | منفرد device ID درج کرنا | لازمی؛ زیادہ سے زیادہ 160 characters |
| Device label input | قابلِ فہم نام درج کرنا | اختیاری؛ زیادہ سے زیادہ 160 characters |
| Register device | Device registration API بھیجنا | UID duplicate ہونے پر error آ سکتا ہے |
| Copy credential | ظاہر شدہ token copy کرنا | اصل token حساس credential ہے |
| Hide | token display چھپانا | یہ token rotation یا server-side revoke نہیں |
| Refresh | Dashboard data دوبارہ حاصل کرنا | نیٹ ورک/API error ممکن ہے |
| Devices table | UID، label، connection status اور last seen دکھانا | Online/offline server timestamp پر مبنی ہے |
| Disconnect/Reconnect | Device enabled حالت بدلنا | Disable کرنے پر token requests مسترد ہو سکتی ہیں |
| Feature controls | دستیاب feature کو enable/disable کرنا | Server-side flag بھی لاگو ہونا چاہیے |

## 4. موجودہ Dashboard کی حدود

Dashboard میں براہ راست survey creation، candidate link management،
audit request creation، manifest review یا حقیقی file transfer کے مکمل
administrative forms موجود ہونے کا دعویٰ نہیں کیا جا سکتا۔
ان میں سے کچھ کام backend APIs کے ذریعے دستیاب ہیں۔

## 5. API response اور error states

Browser JavaScript same-origin `fetch()` استعمال کرتا ہے۔ کامیابی یا ناکامی
کی اطلاع message area میں ظاہر کی جاتی ہے۔ Login پر redirect ہونے کی صورت میں
browser login page پر جا سکتا ہے۔

API-level errors میں unauthorized access، disabled feature، invalid input،
duplicate device، invalid/revoked link، consent gate، expired link اور
duplicate candidate submission شامل ہو سکتے ہیں۔ درست HTTP status ہر endpoint
کے اصل implementation سے دیکھا جائے۔

## 6. Accessibility اور اگلی UI ضروریات

- ہر input کے لیے واضح label اور validation message
- کامیابی اور ناکامی کے لیے قابلِ فہم status
- Token صرف ایک بار دکھانے کی وضاحت
- خطرناک کارروائی سے پہلے confirmation
- keyboard navigation اور مناسب contrast
- Urdu/English language direction کی درست handling
- ہر انتظامی API کے لیے مناسب UI یا واضح طور پر API-only نشان دہی

## 7. Android UI

اس repository میں مکمل Android application source/APK موجود نہیں۔
اس لیے Android screens، buttons، notification behavior یا permission prompts
کو implemented interface کے طور پر دستاویز نہیں کیا گیا۔
