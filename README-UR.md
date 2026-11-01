# Zentrix Device Connect — Modular Source Package

یہ پیکیج Zentrix Device Connect کے Flask سرور، SQLite ڈیٹابیس، ٹیسٹ اور نظام کی دستاویزات پر مشتمل ہے۔

## اہم حقیقت

یہ قابلِ جائزہ modular starter ہے، مکمل production-certified نظام نہیں۔ اس ریپوزٹری میں Android APK یا مکمل Android ایپ سورس شامل نہیں۔ حقیقی ڈیوائس فائلوں کی مکمل منتقلی اور end-to-end hash verification ابھی مکمل نہیں ہیں۔

## موجودہ پروجیکٹ ساخت

- `app.py`: Flask ایپ اور routes۔
- `run.py`: سرور چلانے کا entry point۔
- `modules/`: authentication، devices، surveys، audit requests اور file-audit ماڈیولز۔
- `instance/`: مقامی SQLite ڈیٹابیس کی جگہ؛ اصل ڈیٹابیس کو Git میں شامل نہ کریں۔
- `uploads/`: اپ لوڈز سے متعلق مقامی جگہ۔
- `tests/`: خودکار ٹیسٹ۔
- `docs/`: نظام کی رہنما دستاویزات۔

## سسٹم چلانا

Python 3.11 یا اس سے جدید ورژن تجویز کردہ ہے۔ تمام کمانڈز پروجیکٹ کی جڑ سے چلائیں:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

اپنی مقامی ".env" فائل بنانے کے لیے ".env.example" دیکھیں اور محفوظ secret استعمال کریں۔ پھر ایڈمن اکاؤنٹ بنائیں اور سرور چلائیں:

python create_admin.py
python run.py

براؤزر میں "http://127.0.0.1:5000" کھولیں۔

سسٹم دستاویزات

- "Architecture" (docs/ARCHITECTURE.md)
- "اردو System Functional Guide" (docs/SYSTEM-FUNCTIONAL-GUIDE-UR.md)
- "اردو Interface Guide" (docs/INTERFACE-GUIDE-UR.md)
- "اردو Data Flow" (docs/DATA-FLOW-UR.md)
- "اردو Security and Permissions" (docs/SECURITY-AND-PERMISSIONS-UR.md)
- "Functional Map CSV" (docs/FUNCTIONAL-MAP-UR.csv)
- "System Architecture Diagram" (docs/diagrams/ZENTRIX-SYSTEM-ARCHITECTURE.svg)
- "API Reference" (docs/API-REFERENCE.md)
- "Audit Workflow" (docs/AUDIT-WORKFLOW-UR.md)
- "Backup and Restore" (docs/BACKUP-RESTORE-UR.md)

حفاظتی اصول

- ".env"، ڈیٹابیس، session secret اور اصل device tokens کو ZIP یا Git میں شامل نہ کریں۔
- ہر ڈیوائس کا الگ token رکھیں اور ضرورت پر اسے revoke کریں۔
- آڈٹ صرف مجاز دائرۂ کار میں کریں۔
- metadata یا hash کی فہرست وصول ہونا اصل فائل کی منتقلی کا ثبوت نہیں۔
- نوٹیفکیشن، Android permissions کا متبادل نہیں۔
- audit log موجود ہونا بذاتِ خود tamper-proof ہونے کی ضمانت نہیں۔

---

## Git اور GitHub کا مکمل طریقۂ کار

اس پروجیکٹ کے سورس کوڈ کو محفوظ رکھنے، تبدیلیوں کی تاریخ برقرار رکھنے، مختلف ڈیوائسز پر کام جاری رکھنے اور GitHub کے ساتھ ہم آہنگی کے لیے Git استعمال کیا جاتا ہے۔

### مکمل اردو گائیڈ
[Git اور GitHub Workflow — تفصیلی وضاحت اور سات تصویری خاکے](docs/GIT-WORKFLOW-UR.md)

### موضوعات
- Working Directory اور Staging Area
- Local Repository اور Remote Repository
- `git add`، `git commit`، `git push` اور `git pull`
- نئے کمپیوٹر یا موبائل پر `git clone`
- متعدد Developers اور Collaborators
- Private GitHub Repository کے ساتھ کام
- Secrets، Database اور مقامی ڈیٹا کا تحفظ

### تصویری رہنمائی
تمام سات Git Workflow تصاویر یہاں موجود ہیں:

`docs/images/git-workflow/`
