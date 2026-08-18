# خطة تحويل PDF Control إلى واجهة متصفح دون Streamlit

> حالة التنفيذ: نُفذت الخطة الأساسية في الإصدار `1.1.0`. أصبحت FastAPI وواجهة
> HTML/CSS/JavaScript هي واجهة التشغيل الافتراضية، وأزيل اعتماد Streamlit.

## 1. الهدف

الهدف هو استبدال واجهة Streamlit بواجهة ويب عربية عادية تعمل داخل المتصفح، مع
الاحتفاظ بمحرك معالجة PDF الحالي المكتوب بلغة Python.

لا تعني عبارة "يعمل في المتصفح" أن جميع عمليات PDF ستنفذ بواسطة JavaScript داخل
المتصفح. ستبقى عمليات المعالجة وOCR في خادم Python محلي، بينما يتعامل المستخدم مع
واجهة HTML وCSS وJavaScript فقط.

```text
المتصفح                           خادم Python المحلي
HTML + CSS + JavaScript  <---->  FastAPI  <---->  محرك PDF الحالي
```

النتيجة المستهدفة:

- عدم استخدام Streamlit أو ظهور أي عنصر تابع له.
- تشغيل التطبيق بأمر واحد.
- فتح الواجهة على عنوان محلي مثل `http://127.0.0.1:8000`.
- المحافظة على وظائف PDF الحالية واختباراتها قدر الإمكان.
- إمكانية نشر التطبيق على خادم في مرحلة لاحقة دون إعادة بناء الواجهة.

## 2. ما سيبقى وما سيتغير

### المكونات التي ستبقى

- `core.py`: الواجهة العامة لمحرك المعالجة.
- `merge.py`: الدمج والاستخراج والتقسيم والتدوير والإدراج.
- `editing.py`: إضافة النص واستبداله.
- `ocr.py`: العرض وOCR.
- وظائف إنشاء ملفات PDF القابلة للتعبئة المتاحة عبر `core.py`.
- `_engine.py` و`_pdf.py`: تفاصيل التنفيذ الداخلية.
- `config.py` و`limits.py`: الإعدادات وحدود الموارد.

### المكونات التي ستستبدل

- `web.py` و`ui.py` ووحدات `features/` المعتمدة على Streamlit.
- حالة جلسة Streamlit ومكتبة الملفات المرتبطة بها.
- أزرار التنزيل والمعاينة الخاصة بـStreamlit.

سيكون البديل واجهة ثابتة في `static/` ومسارات API في FastAPI.

## 3. البنية المقترحة

```text
src/pdf_control/
├── api.py
├── cli.py
├── config.py
├── core.py
├── limits.py
├── merge.py
├── editing.py
├── ocr.py
├── api_routes/
│   ├── __init__.py
│   ├── files.py
│   ├── compose.py
│   ├── edit.py
│   └── forms.py
└── static/
    ├── index.html
    ├── app.css
    └── app.js
```

يفضل تقسيم مسارات API حسب المسؤولية وعدم وضع جميع العمليات في `api.py`.

## 4. التبعيات الجديدة

تضاف الحزم التالية إلى `pyproject.toml`:

```toml
"fastapi>=0.115.0,<1.0.0",
"uvicorn[standard]>=0.30.0,<1.0.0",
"python-multipart>=0.0.9,<1.0.0",
```

وظائف الحزم:

- FastAPI: تعريف واجهة HTTP واستقبال الطلبات.
- Uvicorn: تشغيل خادم الويب المحلي.
- python-multipart: استقبال الملفات المرفوعة من النماذج.

بعد تعديل الاعتماديات:

```bash
.venv/bin/pip install -e .
```

لا تحذف Streamlit في بداية الترحيل. يحذف بعد تحويل جميع الوظائف واجتياز الاختبارات،
حتى تظل النسخة الحالية قابلة للتشغيل أثناء العمل.

## 5. تصميم واجهة API

المسارات المقترحة:

| الطريقة | المسار | الوظيفة | النتيجة |
|---|---|---|---|
| `GET` | `/api/health` | فحص جاهزية التطبيق | JSON |
| `POST` | `/api/info` | معلومات ملف PDF | JSON |
| `POST` | `/api/preview` | صور معاينة الصفحات | صور أو JSON |
| `POST` | `/api/merge` | دمج ملفات | PDF |
| `POST` | `/api/extract` | استخراج صفحات | PDF |
| `POST` | `/api/split` | تقسيم ملف | ZIP |
| `POST` | `/api/rotate` | تدوير صفحات | PDF |
| `POST` | `/api/insert` | إدراج ملف في آخر | PDF |
| `POST` | `/api/add-text` | إضافة نص | PDF |
| `POST` | `/api/replace-text` | استبدال نص | PDF |
| `POST` | `/api/editable` | إنشاء نسخة قابلة للتعبئة | PDF |
| `POST` | `/api/exact-editable` | إنشاء نسخة مطابقة قابلة للتعبئة | PDF |

مثال طلب التدوير:

```text
Content-Type: multipart/form-data

file: document.pdf
pages: 1,3,5-7
angle: 90
```

يجب أن تستخدم المسارات دوال `pdf_control.core` العامة بدل استيراد تفاصيل المحرك
الداخلية مباشرة.

## 6. نموذج أولي لخادم FastAPI

المثال التالي يوضح المبدأ فقط. عند التنفيذ الفعلي يجب نقل المنطق المشترك، مثل حفظ
الملفات والتحقق منها وتنظيفها، إلى وظائف مساعدة مستقلة.

```python
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pdf_control import limits
from pdf_control.core import merge_pdfs

app = FastAPI(title="PDF Control")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/merge")
async def merge(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="اختر ملفين على الأقل.")

    temp_dir = Path(tempfile.mkdtemp(prefix="pdf-control-"))
    input_paths: list[Path] = []

    try:
        session_bytes = 0
        for number, uploaded in enumerate(files):
            data = await uploaded.read()
            limits.validate_upload(data, session_bytes)
            session_bytes += len(data)

            if not data.startswith(b"%PDF-"):
                raise HTTPException(status_code=400, detail="أحد الملفات ليس PDF صالحًا.")

            input_path = temp_dir / f"input-{number}.pdf"
            input_path.write_bytes(data)
            input_paths.append(input_path)

        output_path = temp_dir / "merged.pdf"
        merge_pdfs(input_paths, output_path)
        background_tasks.add_task(shutil.rmtree, temp_dir, ignore_errors=True)

        return FileResponse(
            output_path,
            filename="merged.pdf",
            media_type="application/pdf",
            background=background_tasks,
        )
    except HTTPException:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except ValueError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="تعذّرت معالجة الملفات.") from exc


static_dir = Path(__file__).with_name("static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

ملاحظة مهمة: يجب تسجيل تفاصيل الخطأ داخليًا، لكن لا ينبغي إرسال أثر الاستدعاء أو
معلومات مسارات الخادم إلى المتصفح.

## 7. نموذج واجهة المتصفح

### `index.html`

```html
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PDF Control</title>
  <link rel="stylesheet" href="/app.css">
</head>
<body>
  <main>
    <h1>PDF Control</h1>
    <p>معالجة ملفات PDF من المتصفح</p>

    <section>
      <h2>دمج ملفات PDF</h2>
      <input id="merge-files" type="file" accept="application/pdf" multiple>
      <button id="merge-button" type="button">دمج الملفات</button>
      <p id="merge-status" role="status"></p>
    </section>
  </main>

  <script src="/app.js"></script>
</body>
</html>
```

### `app.js`

```javascript
const filesInput = document.querySelector("#merge-files");
const mergeButton = document.querySelector("#merge-button");
const statusElement = document.querySelector("#merge-status");

mergeButton.addEventListener("click", async () => {
  if (filesInput.files.length < 2) {
    statusElement.textContent = "اختر ملفين على الأقل.";
    return;
  }

  const form = new FormData();
  for (const file of filesInput.files) {
    form.append("files", file);
  }

  mergeButton.disabled = true;
  statusElement.textContent = "جارٍ دمج الملفات...";

  try {
    const response = await fetch("/api/merge", {
      method: "POST",
      body: form,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذّر دمج الملفات.");
    }

    const result = await response.blob();
    const url = URL.createObjectURL(result);
    const link = document.createElement("a");
    link.href = url;
    link.download = "merged.pdf";
    link.click();
    URL.revokeObjectURL(url);
    statusElement.textContent = "تم دمج الملفات بنجاح.";
  } catch (error) {
    statusElement.textContent = error.message;
  } finally {
    mergeButton.disabled = false;
  }
});
```

## 8. إدارة الملفات والجلسات

كانت مكتبة الملفات محفوظة في `st.session_state`. بعد إزالة Streamlit توجد طريقتان:

### الخيار الأول: إرسال الملفات مع كل عملية

هذا هو الخيار الموصى به للنسخة الأولى:

- أبسط وأقل خطورة.
- لا يحتاج قاعدة بيانات أو معرف جلسة.
- تحذف الملفات المؤقتة بعد إرسال النتيجة.
- قد يعيد المستخدم رفع الملف نفسه عند تنفيذ عملية جديدة.

### الخيار الثاني: مكتبة ملفات مؤقتة على الخادم

تستخدم عند الحاجة إلى تجربة مماثلة للواجهة الحالية:

- ينشأ معرف جلسة عشوائي آمن.
- يحفظ كل مستخدم ملفاته في مجلد معزول.
- تطبق حصة حجم ومدة انتهاء لكل جلسة.
- يمنع استخدام اسم الملف المرسل كمسار مباشر.
- تنظف الجلسات المنتهية دوريًا.

لا ينصح بتنفيذ مكتبة الخادم قبل وضع سياسة واضحة للعزل والتنظيف.

## 9. المعاينة

يمكن تنفيذ المعاينة بطريقتين:

1. استخدام عارض PDF المدمج في المتصفح بواسطة رابط كائن `Blob`.
2. تحويل الصفحات إلى PNG بواسطة الوظيفة الحالية وعرض الصور المصغرة.

الأفضل استخدام عارض المتصفح للمعاينة الكاملة، وصور PNG فقط لاختيار الصفحات أو عند
عدم دعم العارض المدمج. يجب تطبيق `PDF_CONTROL_MAX_RENDER_PAGES` قبل تحويل الصفحات.

## 10. ميزة Xournal++

Xournal++ برنامج سطح مكتب ولا يعمل داخل صفحة الويب. في النسخة المحلية توجد الخيارات
التالية:

- إبقاء زر يطلب من خادم Python المحلي فتح Xournal++.
- إخفاء الميزة في النسخ المنشورة على خادم بعيد.
- استبدالها مستقبلًا بمحرر وتعليقات يعملان داخل المتصفح.

لا ينبغي أن يكون مسار البرنامج أو الملف قابلًا للتحكم المباشر من طلب المستخدم.

## 11. الأمان وحدود الموارد

كل مسار API يعالج ملفات يجب أن:

- يتحقق من الحجم باستخدام `limits.py` قبل المعالجة الثقيلة.
- يتحقق من توقيع PDF ومقدرته على الفتح، وليس من امتداد الاسم فقط.
- يستخدم أسماء داخلية مولدة بدل اسم الملف الأصلي كمسار.
- يرفض المستندات المشفرة عند عدم دعم كلمة المرور.
- يطبق حد عدد الصفحات وحد العرض وOCR.
- ينظف المجلد المؤقت عند النجاح والفشل.
- لا يعرض تفاصيل الاستثناءات الداخلية للمستخدم.
- يضيف مهلة أو عامل معالجة منفصل للعمليات الثقيلة عند النشر العام.

لا توجد حاجة إلى CORS عندما تخدم FastAPI الواجهة وAPI من الأصل نفسه. لا تفعّل CORS
العامة باستخدام `*` دون حاجة واضحة.

## 12. تعديل التشغيل

يعدل `cli.py` ليشغل Uvicorn بدل Streamlit:

```python
import uvicorn

uvicorn.run(
    "pdf_control.api:app",
    host="127.0.0.1",
    port=8000,
)
```

يمكن بعد بدء الخادم فتح الرابط بواسطة `webbrowser.open`. يجب أن يظل `--no-browser`
متاحًا للاختبارات والتشغيل على الخوادم.

التشغيل المستهدف:

```bash
pdf-control
```

ثم تفتح الواجهة على:

```text
http://127.0.0.1:8000
```

## 13. خطة التنفيذ المرحلية

### المرحلة الأولى: الأساس

- إضافة FastAPI وUvicorn وpython-multipart.
- إنشاء `api.py` وصفحة HTML أولية.
- إضافة `/api/health`.
- تعديل CLI بصورة تسمح بتجربة الخادم الجديد دون حذف Streamlit.

### المرحلة الثانية: عمليات التركيب

- الدمج.
- الاستخراج.
- التقسيم.
- التدوير.
- الإدراج.

### المرحلة الثالثة: المعاينة والتحرير

- معلومات PDF والمعاينة.
- إضافة النص واستبداله.
- اختيار الصفحات بصريًا.
- رسائل التقدم والأخطاء والتنزيل.

### المرحلة الرابعة: OCR والنماذج

- النسخة القابلة للتعبئة.
- النسخة المطابقة بصريًا.
- إعدادات DPI واللغة والثقة.
- مربعات الاختيار.

### المرحلة الخامسة: الانتقال النهائي

- إضافة اختبارات API والواجهة.
- اختبار الملفات الكبيرة والتالفة والمشفرة.
- مقارنة النتائج مع واجهة Streamlit الحالية.
- إزالة Streamlit ووحدات الواجهة القديمة.
- تحديث README وأوامر التثبيت والتشغيل.

## 14. الاختبارات المطلوبة

ينبغي إضافة اختبارات باستخدام عميل FastAPI تغطي:

- نجاح كل مسار وامتداد النتيجة ونوع المحتوى.
- غياب الملف والحقول المطلوبة.
- ملف غير PDF.
- ملف أكبر من الحد.
- عدد صفحات أكبر من الحد.
- نطاق صفحات أو زاوية غير صالحين.
- المستند المشفر والتالف.
- حذف الملفات المؤقتة بعد النجاح والفشل.
- عدم كشف أثر الاستدعاء أو مسار الخادم في رسالة الخطأ.

وتضاف اختبارات متصفح، مثل Playwright، لتغطية:

- اختيار الملفات.
- تشغيل العملية.
- ظهور الحالة والخطأ.
- تنزيل النتيجة.
- اتجاه RTL والعمل على شاشة صغيرة.

## 15. معايير اكتمال الترحيل

يعد التحويل مكتملًا عندما:

- تعمل جميع الوظائف الحالية دون Streamlit.
- يفتح `pdf-control` الواجهة في المتصفح.
- تمر اختبارات المحرك وAPI والواجهة.
- تحذف الملفات المؤقتة تلقائيًا.
- تطبق حدود الحجم والصفحات على جميع العمليات.
- لا تعتمد أي وحدة واجهة على `streamlit`.
- تزال Streamlit من اعتماديات المشروع.
- يحدث README ودليل التثبيت والتشغيل.

## 16. القرار الموصى به

يبدأ التنفيذ بخادم FastAPI محلي وصفحة HTML بسيطة، مع إرسال الملفات مع كل عملية.
يجب عدم بناء نظام جلسات أو قاعدة بيانات في المرحلة الأولى. بعد تحويل الوظائف الأساسية
والتحقق منها، يمكن إضافة مكتبة ملفات مؤقتة وواجهة أكثر تفاعلية دون تغيير محرك PDF.
