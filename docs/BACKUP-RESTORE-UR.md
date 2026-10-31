# Backup and restore

- موجودہ `alingo.db` کو overwrite نہ کریں۔
- backup سے پہلے app/server روکیں یا SQLite online backup API استعمال کریں۔
- database backup کے ساتھ uploads، environment secret اور config manifest بھی محفوظ کریں۔
- restore پہلے الگ test directory میں کریں۔
- ہر backup کا SHA-256 manifest بنائیں اور restore test کا نتیجہ لکھیں۔
- secrets اور user/device data کو source ZIP یا public Git repository میں شامل نہ کریں۔
