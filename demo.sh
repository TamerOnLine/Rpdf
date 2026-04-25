#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/Rpdf/pdf-control"
INPUT_PDF="${1:-input.pdf}"
WORKDIR="${2:-demo_output}"

cd "$PROJECT_DIR"
source .venv/bin/activate

if [[ ! -f "$INPUT_PDF" ]]; then
  echo "Input PDF not found: $INPUT_PDF"
  echo "Usage: $0 /path/to/input.pdf [workdir]"
  exit 1
fi

mkdir -p "$WORKDIR"

echo "==> 1) التحقق من الواجهة"
python3 -m src.main --help > /dev/null
echo "OK"

echo "==> 2) عرض معلومات الملف"
python3 -m src.main info "$INPUT_PDF" | tee "$WORKDIR/info.txt"

echo "==> 3) استخراج صفحات 1 و 3 و 5-7"
python3 -m src.main extract "$INPUT_PDF" "$WORKDIR/out_extract.pdf" --pages "1,3,5-7"

echo "==> 4) تقسيم كل صفحة إلى ملف مستقل"
python3 -m src.main split "$INPUT_PDF" --output-dir "$WORKDIR/out_pages"

echo "==> 5) تدوير الصفحات 1-3 و 5"
python3 -m src.main rotate "$INPUT_PDF" "$WORKDIR/out_rotated.pdf" --pages "1-3,5" --angle 90

echo "==> 6) استبدال نص عربي"
python3 -m src.main edit "$INPUT_PDF" "$WORKDIR/out_edit_ar.pdf" --find "قديم" --replace "جديد" || true

echo "==> 7) استبدال نص إنجليزي في صفحات محددة"
python3 -m src.main edit "$INPUT_PDF" "$WORKDIR/out_edit_en.pdf" --find "Hello" --replace "Hi" --pages "1,3-5" || true

echo "==> 8) إضافة نص مرئي"
python3 -m src.main addtext "$INPUT_PDF" "$WORKDIR/out_text.pdf" \
  --page 1 --text "تمت المراجعة" --x 120 --y 680 --size 16

echo "==> 9) إنشاء ملف مدمج تجريبي"
python3 -m src.main merge "$WORKDIR/merged.pdf" "$INPUT_PDF" "$WORKDIR/out_extract.pdf" "$WORKDIR/out_rotated.pdf"

echo "==> 10) انتهى التنفيذ"
echo "الملفات الناتجة داخل: $WORKDIR"
find "$WORKDIR" -maxdepth 2 -type f | sort
