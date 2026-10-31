# Security policy

- ہر ڈیوائس کا الگ random token؛ token plaintext صرف ایک بار دکھائیں۔
- production میں HTTPS لازم؛ HTTP پر tokens نہ بھیجیں۔
- token hash server DB میں محفوظ کریں اور revoke/rotate فیچر مکمل کریں۔
- admin endpoints پر CSRF، rate limiting، secure cookies، login throttling اور permission checks شامل کرنے سے پہلے production deployment نہ کریں۔
- audit scope allowlist سے validate ہو؛ arbitrary path قبول نہ کریں۔
- audit event میں actor، request ID، scope، timestamps، status اور outcome شامل ہوں۔
- notification واضح ہو؛ file content transfer اور metadata audit الگ ہوں۔
- Android کی اجازتیں مالک خود OS dialogs میں دے؛ app خود ان پابندیوں کو bypass نہ کرے۔
