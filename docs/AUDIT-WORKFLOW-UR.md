# آڈٹ ورک فلو

1. منتظم ڈیش بورڈ/API سے ڈیوائس، آڈٹ کی قسم اور محدود scope منتخب کرے۔
2. سرور درخواست کو `queued` حالت میں محفوظ کرے۔
3. Android کلائنٹ authenticated channel سے درخواست حاصل کرے۔
4. ایپ درخواست کی شناخت، scope اور فعال feature کی جانچ کرے۔
5. مالک کو Android notification دکھایا جائے۔
6. metadata audit میں صرف قابلِ رسائی فائلوں کا metadata/hash جمع ہو۔
7. content audit صرف واضح طور پر منظور شدہ مخصوص فائلوں کے لیے ہو۔
8. نتیجہ request ID کے ساتھ سرور کو بھیجا جائے اور audit event محفوظ ہو۔

اس starter میں سرور کی request queue اور result endpoint موجود ہیں؛ Android polling/notification/scan ابھی implement اور test کرنا باقی ہے۔ سرور کے queued ہونے سے خودبخود فون پر notification پہنچنے کی ضمانت نہیں ہوتی۔
