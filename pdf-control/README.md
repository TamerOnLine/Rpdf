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
- إدراج صفحة/ملف PDF داخل ملف PDF في موضع محدد
- تشغيل كسيرفر HTTP (FastAPI)
- واجهة ويب باستخدام Streamlit

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
./run.sh web
./run.sh serve --host 127.0.0.1 --port 8000
./run.sh info input.pdf
```

## الاختبارات
بعد تثبيت المتطلبات وإنشاء البيئة الافتراضية، شغّل:
```bash
./.venv/bin/python -m unittest discover -s tests -v
```

التغطية الحالية تشمل:
- اختبارات دوال `insert` في `pdf_utils` (الإدراج في البداية/المنتصف والتحقق من القيم غير الصالحة).
- اختبارات endpoint `insert` في API (حالة نجاح وحالة فشل).

## تشغيل الواجهة الرسومية (GUI)
```bash
python3 -m src.main gui
```

لتشغيل الواجهة باللغة الإنجليزية:
```bash
python3 -m src.main gui --lang en
```

أو عبر الأمر المختصر:
```bash
python3 -m src.main gui-en
```

## تشغيل واجهة Streamlit
بعد تثبيت المتطلبات:
```bash
cd pdf-control
./run.sh web
```

لتشغيل الواجهة على منفذ متاح تلقائيًا وفتح المتصفح:
```bash
cd pdf-control
./open-web.sh
```

الحد الافتراضي للرفع في سكربتات المشروع هو `1024 MB` لكل ملف. لتغييره مؤقتًا:
```bash
STREAMLIT_MAX_UPLOAD_SIZE_MB=2048 ./open-web.sh
```

أو مباشرة:
```bash
streamlit run src/streamlit_app.py
```

تحتوي واجهة Streamlit على مكتبة ملفات مشتركة: أضف ملفات PDF مرة واحدة ثم استخدمها من كل التبويبات. تدعم الواجهة فتح PDF في Xournal++، عرض المعلومات، الدمج، الاستخراج، التقسيم، التدوير، استبدال النص، إضافة نص مرئي، وإدراج ملف PDF داخل ملف آخر.

## تشغيل كسيرفر API
```bash
python3 -m src.main serve --host 127.0.0.1 --port 8000
```

بعد التشغيل:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health: `http://127.0.0.1:8000/health`

### حدود API الحالية
- يتحقق السيرفر من أن الملفات المرفوعة تبدأ بترويسة PDF صحيحة (`%PDF-`).
- الحد الافتراضي لحجم كل ملف مرفوع هو `25 MB`.
- يستخدم السيرفر أسماء تخزين مؤقت داخلية، وينظف أسماء ملفات الإخراج لمنع استخدام مسارات خارج مجلد العمل المؤقت.
- لا توجد طبقة مصادقة أو صلاحيات حتى الآن؛ لذلك شغّل السيرفر محليًا أو خلف حماية مناسبة فقط.

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
هذه الميزة تحاول استبدال النص الموجود داخل محتوى PDF نفسه. نجاحها يعتمد على طريقة بناء الملف:
- تعمل غالبًا مع ملفات PDF البسيطة التي تحتوي على نص مباشر.
- لا تعمل مع الملفات الممسوحة ضوئيًا كصور إلا بعد OCR خارج المشروع.
- قد لا تعمل مع ملفات تستخدم خطوطًا مشفرة، أو تقسم الكلمة الواحدة إلى أجزاء داخلية، أو ترسم النص بطريقة معقدة.
- إذا لم يجد المشروع النص داخل البنية الداخلية للصفحات المحددة فسيُرجع خطأ بدل إنشاء ملف بلا تغيير.

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

### 8) إدراج صفحة بعد صفحة معينة
يدعم المشروع أمرًا مباشرًا باسم `insert`.

مثال: إدراج `newpage.pdf` بعد الصفحة `5` من `input.pdf`:

```bash
python3 -m src.main insert input.pdf newpage.pdf output.pdf --after-page 5
```

للإدراج في بداية الملف:
```bash
python3 -m src.main insert input.pdf newpage.pdf output.pdf --after-page 0
```

## ملاحظات
- ترقيم الصفحات في الأوامر يبدأ من 1.
- الزوايا المدعومة للتدوير: `90`, `180`, `270`.
- ميزة تعديل النص ليست محرر PDF كامل؛ هي استبدال مباشر داخل أوامر النص التي يستطيع `pypdf` قراءتها.
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
