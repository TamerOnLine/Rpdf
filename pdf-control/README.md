# مشروع التحكم بملفات PDF

مشروع بسيط للتحكم بملفات PDF من سطر الأوامر باستخدام Python.
يتضمن أيضًا واجهة رسومية بسيطة.

## الميزات
- عرض معلومات ملف PDF
- دمج عدة ملفات PDF
- استخراج صفحات محددة
- تقسيم ملف PDF إلى ملفات منفصلة (لكل صفحة)
- تدوير صفحات محددة
- تعديل النص داخل صفحات PDF (استبدال نص)
- إضافة نص مرئي داخل الصفحة بإحداثيات محددة
- تشغيل كسيرفر HTTP (FastAPI)

## المتطلبات
- Python 3.10+
- `tkinter` (اختياري لتشغيل الواجهة الرسومية)

## التثبيت
```bash
cd pdf-control
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## الاستخدام
```bash
python3 -m src.main --help
```

## سكربت تشغيل سريع
لتفادي مشاكل المسار (`No module named 'src'`) شغّل المشروع عبر:
```bash
cd pdf-control
./run.sh
```

- بدون معاملات: يشغّل `gui`
- مع معاملات: يمرّرها مباشرة إلى CLI

أمثلة:
```bash
./run.sh --help
./run.sh serve --host 127.0.0.1 --port 8000
./run.sh info input.pdf
```

## تشغيل الواجهة الرسومية (GUI)
```bash
python3 -m src.main gui
```

## تشغيل كسيرفر API
```bash
python3 -m src.main serve --host 127.0.0.1 --port 8000
```

بعد التشغيل:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health: `http://127.0.0.1:8000/health`

### تشغيل API على ويندوز (PowerShell)
```powershell
cd C:\path\to\pdf-control
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -m src.main serve --host 127.0.0.1 --port 8000
```

### 1) معلومات الملف
```bash
python3 -m src.main info input.pdf
```

### 2) دمج ملفات
```bash
python3 -m src.main merge output.pdf a.pdf b.pdf c.pdf
```

### 3) استخراج صفحات
يدعم:
- رقم صفحة مفرد: `3`
- نطاق: `2-5`
- عدة عناصر: `1,3,7-9`

```bash
python3 -m src.main extract input.pdf output.pdf --pages "1,3,5-7"
```

### 4) تقسيم إلى صفحات منفصلة
```bash
python3 -m src.main split input.pdf --output-dir out_pages
```

### 5) تدوير صفحات
```bash
python3 -m src.main rotate input.pdf output.pdf --pages "1-3,5" --angle 90
```

### 6) تعديل النص داخل PDF
استبدال نص في كل الصفحات:
```bash
python3 -m src.main edit input.pdf output.pdf --find "قديم" --replace "جديد"
```

استبدال نص في صفحات محددة فقط:
```bash
python3 -m src.main edit input.pdf output.pdf --find "Hello" --replace "Hi" --pages "1,3-5"
```

### 7) إضافة نص مرئي داخل الصفحة
```bash
python3 -m src.main addtext input.pdf output.pdf --page 1 --text "مراجعة" --x 120 --y 680 --size 16
```

للعربية بشكل أفضل، مرّر خط TTF يدعم العربية:
```bash
python3 -m src.main addtext input.pdf output.pdf --page 1 --text "تمت المراجعة" --x 120 --y 680 --size 16 --font-path "/path/to/arabic-font.ttf"
```

## ملاحظات
- ترقيم الصفحات في الأوامر يبدأ من 1.
- الزوايا المدعومة للتدوير: `90`, `180`, `270`.
- ميزة تعديل النص تعتمد على بنية الملف؛ بعض ملفات PDF المعقدة/الممسوحة ضوئيًا قد لا تدعم الاستبدال المباشر.
- ميزة `addtext` تضيف نصًا فوق الصفحة (مثل أداة الكتابة في بعض برامج عرض PDF).
- من الواجهة الرسومية يوجد زر سريع لفتح الملف في `Xournal++` للمعاينة والتعديل اليدوي.
- إذا ظهر خطأ `No module named 'tkinter'`:
  - Ubuntu/Debian: ثبّت الحزمة `python3-tk`
  - Fedora: ثبّت الحزمة `python3-tkinter`
- إذا لم يكن `Xournal++` مثبتًا:
  - Ubuntu/Debian: `sudo apt install -y xournalpp`
- إذا كانت عملية `gui` تعمل لكن النافذة لا تظهر (خصوصًا في WSL/VS Code):
  - شغّل التطبيق من Terminal خارجي ثم جرّب `Alt+Tab`.
  - أعد تشغيل WSLg عبر PowerShell: `wsl --shutdown` ثم أعد المحاولة.


source /home/Rpdf/pdf-control/.venv/bin/activate
pkill -f "src.main gui" || true
cd /home/Rpdf/pdf-control
./run.sh
