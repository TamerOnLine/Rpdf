from __future__ import annotations

import importlib
import shutil
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ModuleNotFoundError:
    arabic_reshaper = None
    get_display = None


def ar(text: str) -> str:
    if arabic_reshaper is None or get_display is None:
        return text
    return get_display(arabic_reshaper.reshape(text))


class PDFControlApp(tk.Tk):
    def __init__(self, language: str = "ar") -> None:
        super().__init__()
        if language not in {"ar", "en"}:
            raise ValueError("language must be 'ar' or 'en'.")
        self.language = language
        self._configure_ui_scaling()
        self.title(self.tr("لوحة التحكم بملفات بي دي إف", "PDF Control Panel"))
        self.geometry("1120x780")
        self.minsize(980, 680)
        self.state("normal")

        self._build_ui()
        self.after(120, self._place_and_focus_window)
        # A gentle second focus pass helps some WSLg setups without re-minimizing.
        self.after(900, self._force_show_window)

    def tr(self, arabic_text: str, english_text: str) -> str:
        if self.language == "ar":
            return ar(arabic_text)
        return english_text

    def _pdf_filetypes(self) -> list[tuple[str, str]]:
        return [
            (self.tr("ملفات PDF", "PDF files"), "*.pdf"),
            (self.tr("كل الملفات", "All files"), "*.*"),
        ]

    def _configure_ui_scaling(self) -> None:
        self.tk.call("tk", "scaling", 1.2)

        default_font = tkfont.nametofont("TkDefaultFont")
        text_font = tkfont.nametofont("TkTextFont")
        fixed_font = tkfont.nametofont("TkFixedFont")

        default_size = max(default_font.cget("size"), 11)
        text_size = max(text_font.cget("size"), 11)
        fixed_size = max(fixed_font.cget("size"), 11)

        default_font.configure(size=default_size + 2)
        text_font.configure(size=text_size + 2)
        fixed_font.configure(size=fixed_size + 2)

        style = ttk.Style(self)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("TkDefaultFont", default_size + 1, "bold"))
        style.configure("TButton", padding=(8, 4))
        style.configure("TEntry", padding=(4, 2))

    def _place_and_focus_window(self) -> None:
        try:
            self.update_idletasks()
            width = self.winfo_width() or 860
            height = self.winfo_height() or 620
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = max((screen_w - width) // 2, 0)
            y = max((screen_h - height) // 2, 0)
            self.geometry(f"{width}x{height}+{x}+{y}")
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(350, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            pass

    def _force_show_window(self) -> None:
        try:
            self.state("normal")
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(400, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            pass

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        title_bar = tk.Frame(container, bg="#1f2937", bd=0, highlightthickness=0)
        title_bar.pack(fill="x", pady=(0, 12))

        title_text = tk.Label(
            title_bar,
            text=self.tr("لوحة التحكم بملفات PDF", "PDF Control Panel"),
            bg="#1f2937",
            fg="#f8fafc",
            font=("TkDefaultFont", 16, "bold"),
            padx=12,
            pady=8,
            anchor="w",
        )
        title_text.pack(fill="x")

        subtitle_text = tk.Label(
            title_bar,
            text=self.tr(
                "إدارة PDF: دمج، استخراج، تدوير، تعديل وإضافة نص",
                "Manage PDFs: merge, extract, rotate, edit, and add text",
            ),
            bg="#1f2937",
            fg="#cbd5e1",
            font=("TkDefaultFont", 12),
            padx=12,
            pady=0,
            anchor="w",
        )
        subtitle_text.pack(fill="x", pady=(0, 8))

        self.shared_input_pdf = tk.StringVar()
        shared_frame = ttk.Frame(container)
        shared_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(shared_frame, text=self.tr("ملف PDF موحّد لكل التبويبات", "Shared PDF file for all tabs")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Entry(shared_frame, textvariable=self.shared_input_pdf, width=72).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(shared_frame, text=self.tr("استعراض", "Browse"), command=self._pick_shared_input).grid(
            row=1, column=1, padx=8
        )
        ttk.Button(
            shared_frame,
            text=self.tr("تطبيق على التبويبات", "Apply to tabs"),
            command=self._apply_shared_input_from_field,
        ).grid(row=1, column=2, sticky="w")
        shared_frame.grid_columnconfigure(0, weight=1)

        self.quick_pdf_path = tk.StringVar()

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        self.xournal_tab = ttk.Frame(notebook, padding=12)
        self.info_tab = ttk.Frame(notebook, padding=12)
        self.merge_tab = ttk.Frame(notebook, padding=12)
        self.extract_tab = ttk.Frame(notebook, padding=12)
        self.insert_tab = ttk.Frame(notebook, padding=12)
        self.split_tab = ttk.Frame(notebook, padding=12)
        self.rotate_tab = ttk.Frame(notebook, padding=12)
        self.edit_tab = ttk.Frame(notebook, padding=12)
        self.add_text_tab = ttk.Frame(notebook, padding=12)

        notebook.add(self.xournal_tab, text="Xournal++")
        notebook.add(self.info_tab, text=self.tr("معلومات", "Info"))
        notebook.add(self.merge_tab, text=self.tr("دمج", "Merge"))
        notebook.add(self.extract_tab, text=self.tr("استخراج", "Extract"))
        notebook.add(self.insert_tab, text=self.tr("إدراج صفحات", "Insert pages"))
        notebook.add(self.split_tab, text=self.tr("تقسيم", "Split"))
        notebook.add(self.rotate_tab, text=self.tr("تدوير", "Rotate"))
        notebook.add(self.edit_tab, text=self.tr("تعديل النص", "Edit text"))
        notebook.add(self.add_text_tab, text=self.tr("إضافة نص", "Add text"))

        self._build_xournal_tab()
        self._build_info_tab()
        self._build_merge_tab()
        self._build_extract_tab()
        self._build_insert_tab()
        self._build_split_tab()
        self._build_rotate_tab()
        self._build_edit_tab()
        self._build_add_text_tab()

    def _apply_shared_input_to_tabs(self, path: str) -> None:
        clean_path = path.strip()
        if not clean_path:
            return
        self.shared_input_pdf.set(clean_path)
        self.quick_pdf_path.set(clean_path)
        self.info_input.set(clean_path)
        self.extract_input.set(clean_path)
        self.insert_base_input.set(clean_path)
        self.split_input.set(clean_path)
        self.rotate_input.set(clean_path)
        self.edit_input.set(clean_path)
        self.add_text_input.set(clean_path)

    def _apply_shared_input_from_field(self) -> None:
        raw = self.shared_input_pdf.get().strip()
        if not raw:
            messagebox.showerror(
                self.tr("خطأ", "Error"),
                self.tr("أدخل مسار ملف PDF أولًا.", "Enter a PDF file path first."),
            )
            return
        self._apply_shared_input_to_tabs(raw)

    def _pick_shared_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _build_xournal_tab(self) -> None:
        ttk.Label(
            self.xournal_tab,
            text=self.tr("فتح ملف للمعاينة/التعديل في Xournal++", "Open a PDF in Xournal++"),
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(self.xournal_tab, textvariable=self.quick_pdf_path, width=75).grid(
            row=1, column=0, padx=(0, 8), sticky="we"
        )
        ttk.Button(self.xournal_tab, text=self.tr("استعراض", "Browse"), command=self._pick_quick_pdf).grid(
            row=1, column=1, sticky="w"
        )
        ttk.Button(
            self.xournal_tab,
            text=self.tr("فتح في Xournal++", "Open in Xournal++"),
            command=self._open_in_xournal,
        ).grid(row=2, column=0, pady=10, sticky="w")
        self.xournal_tab.grid_columnconfigure(0, weight=1)

    def _build_info_tab(self) -> None:
        self.info_input = tk.StringVar()
        ttk.Label(self.info_tab, text=self.tr("ملف PDF المدخل", "Input PDF file")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.info_tab, textvariable=self.info_input, width=75).grid(
            row=1, column=0, padx=(0, 8), sticky="we"
        )
        ttk.Button(self.info_tab, text=self.tr("استعراض", "Browse"), command=self._pick_info_input).grid(
            row=1, column=1, sticky="w"
        )
        ttk.Button(self.info_tab, text=self.tr("عرض المعلومات", "Show info"), command=self._run_info).grid(
            row=2, column=0, pady=10, sticky="w"
        )

        self.info_text = tk.Text(self.info_tab, height=22, wrap="word")
        self.info_text.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.info_tab.grid_columnconfigure(0, weight=1)
        self.info_tab.grid_rowconfigure(3, weight=1)

    def _build_merge_tab(self) -> None:
        self.merge_inputs = tk.StringVar()
        self.merge_output = tk.StringVar()
        self.merge_file_paths: list[str] = []

        ttk.Label(
            self.merge_tab,
            text=self.tr(
                "ملفات PDF المدخلة (متعددة) - رتّبها قبل الدمج",
                "Input PDF files (multiple) - arrange before merging",
            ),
        ).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.merge_tab, textvariable=self.merge_inputs, width=75).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(self.merge_tab, text=self.tr("استعراض", "Browse"), command=self._pick_merge_inputs).grid(
            row=1, column=1, padx=8
        )

        list_wrap = ttk.Frame(self.merge_tab)
        list_wrap.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

        self.merge_listbox = tk.Listbox(list_wrap, height=7, exportselection=False)
        self.merge_listbox.grid(row=0, column=0, rowspan=4, sticky="nsew")

        scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.merge_listbox.yview)
        scroll.grid(row=0, column=1, rowspan=4, sticky="ns")
        self.merge_listbox.configure(yscrollcommand=scroll.set)

        ttk.Button(list_wrap, text=self.tr("إضافة ملفات", "Add files"), command=self._pick_merge_inputs).grid(
            row=0, column=2, padx=(8, 0), sticky="ew"
        )
        ttk.Button(
            list_wrap,
            text=self.tr("إزالة المحدد", "Remove selected"),
            command=self._remove_selected_merge_input,
        ).grid(row=1, column=2, padx=(8, 0), pady=(6, 0), sticky="ew")
        ttk.Button(
            list_wrap,
            text=self.tr("أعلى", "Up"),
            command=lambda: self._move_selected_merge_input(-1),
        ).grid(row=2, column=2, padx=(8, 0), pady=(6, 0), sticky="ew")
        ttk.Button(
            list_wrap,
            text=self.tr("أسفل", "Down"),
            command=lambda: self._move_selected_merge_input(1),
        ).grid(row=3, column=2, padx=(8, 0), pady=(6, 0), sticky="ew")

        list_wrap.grid_columnconfigure(0, weight=1)
        list_wrap.grid_rowconfigure(3, weight=1)

        ttk.Label(self.merge_tab, text=self.tr("ملف PDF الناتج", "Output PDF file")).grid(
            row=3, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.merge_tab, textvariable=self.merge_output, width=75).grid(
            row=4, column=0, sticky="we"
        )
        ttk.Button(self.merge_tab, text=self.tr("حفظ باسم", "Save as"), command=self._pick_merge_output).grid(
            row=4, column=1, padx=8
        )

        ttk.Button(self.merge_tab, text=self.tr("دمج", "Merge"), command=self._run_merge).grid(
            row=5, column=0, pady=12, sticky="w"
        )
        self.merge_tab.grid_columnconfigure(0, weight=1)
        self.merge_tab.grid_rowconfigure(2, weight=1)

    def _build_extract_tab(self) -> None:
        self.extract_input = tk.StringVar()
        self.extract_output = tk.StringVar()
        self.extract_pages_var = tk.StringVar()

        ttk.Label(self.extract_tab, text=self.tr("ملف PDF المدخل", "Input PDF file")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.extract_tab, textvariable=self.extract_input, width=75).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(self.extract_tab, text=self.tr("استعراض", "Browse"), command=self._pick_extract_input).grid(
            row=1, column=1, padx=8
        )

        ttk.Label(self.extract_tab, text=self.tr("ملف PDF الناتج", "Output PDF file")).grid(
            row=2, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.extract_tab, textvariable=self.extract_output, width=75).grid(
            row=3, column=0, sticky="we"
        )
        ttk.Button(self.extract_tab, text=self.tr("حفظ باسم", "Save as"), command=self._pick_extract_output).grid(
            row=3, column=1, padx=8
        )

        ttk.Label(self.extract_tab, text=self.tr('الصفحات (مثال: "1,3,5-7")', 'Pages (example: "1,3,5-7")')).grid(
            row=4, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.extract_tab, textvariable=self.extract_pages_var, width=30).grid(
            row=5, column=0, sticky="w"
        )

        ttk.Button(self.extract_tab, text=self.tr("استخراج", "Extract"), command=self._run_extract).grid(
            row=6, column=0, pady=12, sticky="w"
        )
        self.extract_tab.grid_columnconfigure(0, weight=1)

    def _build_insert_tab(self) -> None:
        self.insert_base_input = tk.StringVar()
        self.insert_pdf_input = tk.StringVar()
        self.insert_output = tk.StringVar()
        self.insert_after_page = tk.IntVar(value=1)

        ttk.Label(self.insert_tab, text=self.tr("ملف PDF الأساسي", "Base PDF file")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.insert_tab, textvariable=self.insert_base_input, width=75).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(self.insert_tab, text=self.tr("استعراض", "Browse"), command=self._pick_insert_base_input).grid(
            row=1, column=1, padx=8
        )

        ttk.Label(self.insert_tab, text=self.tr("ملف PDF المراد إدراجه (صفحة أو أكثر)", "PDF to insert (one or more pages)")).grid(
            row=2, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.insert_tab, textvariable=self.insert_pdf_input, width=75).grid(
            row=3, column=0, sticky="we"
        )
        ttk.Button(self.insert_tab, text=self.tr("استعراض", "Browse"), command=self._pick_insert_pdf_input).grid(
            row=3, column=1, padx=8
        )

        ttk.Label(self.insert_tab, text=self.tr("أدرج بعد الصفحة رقم (0 = بداية الملف)", "Insert after page number (0 = beginning)")).grid(
            row=4, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.insert_tab, textvariable=self.insert_after_page, width=12).grid(
            row=5, column=0, sticky="w"
        )

        ttk.Label(self.insert_tab, text=self.tr("ملف PDF الناتج", "Output PDF file")).grid(
            row=6, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.insert_tab, textvariable=self.insert_output, width=75).grid(
            row=7, column=0, sticky="we"
        )
        ttk.Button(self.insert_tab, text=self.tr("حفظ باسم", "Save as"), command=self._pick_insert_output).grid(
            row=7, column=1, padx=8
        )

        ttk.Button(self.insert_tab, text=self.tr("إدراج", "Insert"), command=self._run_insert).grid(
            row=8, column=0, pady=12, sticky="w"
        )
        self.insert_tab.grid_columnconfigure(0, weight=1)

    def _build_split_tab(self) -> None:
        self.split_input = tk.StringVar()
        self.split_output_dir = tk.StringVar()

        ttk.Label(self.split_tab, text=self.tr("ملف PDF المدخل", "Input PDF file")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.split_tab, textvariable=self.split_input, width=75).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(self.split_tab, text=self.tr("استعراض", "Browse"), command=self._pick_split_input).grid(
            row=1, column=1, padx=8
        )

        ttk.Label(self.split_tab, text=self.tr("مجلد الإخراج", "Output directory")).grid(
            row=2, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.split_tab, textvariable=self.split_output_dir, width=75).grid(
            row=3, column=0, sticky="we"
        )
        ttk.Button(self.split_tab, text=self.tr("اختيار", "Choose"), command=self._pick_split_output_dir).grid(
            row=3, column=1, padx=8
        )

        ttk.Button(self.split_tab, text=self.tr("تقسيم", "Split"), command=self._run_split).grid(
            row=4, column=0, pady=12, sticky="w"
        )
        self.split_tab.grid_columnconfigure(0, weight=1)

    def _build_rotate_tab(self) -> None:
        self.rotate_input = tk.StringVar()
        self.rotate_output = tk.StringVar()
        self.rotate_pages_var = tk.StringVar()
        self.rotate_angle = tk.IntVar(value=90)

        ttk.Label(self.rotate_tab, text=self.tr("ملف PDF المدخل", "Input PDF file")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.rotate_tab, textvariable=self.rotate_input, width=75).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(self.rotate_tab, text=self.tr("استعراض", "Browse"), command=self._pick_rotate_input).grid(
            row=1, column=1, padx=8
        )

        ttk.Label(self.rotate_tab, text=self.tr("ملف PDF الناتج", "Output PDF file")).grid(
            row=2, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.rotate_tab, textvariable=self.rotate_output, width=75).grid(
            row=3, column=0, sticky="we"
        )
        ttk.Button(self.rotate_tab, text=self.tr("حفظ باسم", "Save as"), command=self._pick_rotate_output).grid(
            row=3, column=1, padx=8
        )

        ttk.Label(self.rotate_tab, text=self.tr('الصفحات (مثال: "1-3,5")', 'Pages (example: "1-3,5")')).grid(
            row=4, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.rotate_tab, textvariable=self.rotate_pages_var, width=30).grid(
            row=5, column=0, sticky="w"
        )

        ttk.Label(self.rotate_tab, text=self.tr("زاوية التدوير", "Rotation angle")).grid(
            row=6, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Combobox(
            self.rotate_tab,
            textvariable=self.rotate_angle,
            values=["90", "180", "270"],
            width=8,
            state="readonly",
        ).grid(row=7, column=0, sticky="w")

        ttk.Button(self.rotate_tab, text=self.tr("تدوير", "Rotate"), command=self._run_rotate).grid(
            row=8, column=0, pady=12, sticky="w"
        )
        self.rotate_tab.grid_columnconfigure(0, weight=1)

    def _build_edit_tab(self) -> None:
        self.edit_input = tk.StringVar()
        self.edit_output = tk.StringVar()
        self.edit_find = tk.StringVar()
        self.edit_replace = tk.StringVar()
        self.edit_pages = tk.StringVar()

        ttk.Label(self.edit_tab, text=self.tr("ملف PDF المدخل", "Input PDF file")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.edit_tab, textvariable=self.edit_input, width=75).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(self.edit_tab, text=self.tr("استعراض", "Browse"), command=self._pick_edit_input).grid(
            row=1, column=1, padx=8
        )

        ttk.Label(self.edit_tab, text=self.tr("ملف PDF الناتج", "Output PDF file")).grid(
            row=2, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.edit_tab, textvariable=self.edit_output, width=75).grid(
            row=3, column=0, sticky="we"
        )
        ttk.Button(self.edit_tab, text=self.tr("حفظ باسم", "Save as"), command=self._pick_edit_output).grid(
            row=3, column=1, padx=8
        )

        ttk.Label(self.edit_tab, text=self.tr("النص المطلوب استبداله", "Text to find")).grid(
            row=4, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.edit_tab, textvariable=self.edit_find, width=40).grid(
            row=5, column=0, sticky="w"
        )

        ttk.Label(self.edit_tab, text=self.tr("النص البديل", "Replacement text")).grid(
            row=6, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.edit_tab, textvariable=self.edit_replace, width=40).grid(
            row=7, column=0, sticky="w"
        )

        ttk.Label(self.edit_tab, text=self.tr('الصفحات (اختياري، مثال: "1,3,5-7")', 'Pages (optional, example: "1,3,5-7")')).grid(
            row=8, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.edit_tab, textvariable=self.edit_pages, width=40).grid(
            row=9, column=0, sticky="w"
        )

        ttk.Button(self.edit_tab, text=self.tr("تعديل النص", "Edit text"), command=self._run_edit).grid(
            row=10, column=0, pady=12, sticky="w"
        )
        self.edit_tab.grid_columnconfigure(0, weight=1)

    def _build_add_text_tab(self) -> None:
        self.add_text_input = tk.StringVar()
        self.add_text_output = tk.StringVar()
        self.add_text_value = tk.StringVar()
        self.add_text_page = tk.IntVar(value=1)
        self.add_text_x = tk.DoubleVar(value=100.0)
        self.add_text_y = tk.DoubleVar(value=100.0)
        self.add_text_size = tk.IntVar(value=14)
        self.add_text_font_path = tk.StringVar()

        ttk.Label(self.add_text_tab, text=self.tr("ملف PDF المدخل", "Input PDF file")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_input, width=75).grid(
            row=1, column=0, sticky="we"
        )
        ttk.Button(self.add_text_tab, text=self.tr("استعراض", "Browse"), command=self._pick_add_text_input).grid(
            row=1, column=1, padx=8
        )

        ttk.Label(self.add_text_tab, text=self.tr("ملف PDF الناتج", "Output PDF file")).grid(
            row=2, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_output, width=75).grid(
            row=3, column=0, sticky="we"
        )
        ttk.Button(self.add_text_tab, text=self.tr("حفظ باسم", "Save as"), command=self._pick_add_text_output).grid(
            row=3, column=1, padx=8
        )

        ttk.Label(self.add_text_tab, text=self.tr("النص المراد إضافته", "Text to add")).grid(
            row=4, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_value, width=60).grid(
            row=5, column=0, sticky="w"
        )

        controls = ttk.Frame(self.add_text_tab)
        controls.grid(row=6, column=0, pady=(10, 0), sticky="w")
        ttk.Label(controls, text=self.tr("الصفحة", "Page")).grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_page, width=8).grid(
            row=1, column=0, padx=(0, 12), sticky="w"
        )
        ttk.Label(controls, text="X").grid(row=0, column=1, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_x, width=10).grid(
            row=1, column=1, padx=(0, 12), sticky="w"
        )
        ttk.Label(controls, text="Y").grid(row=0, column=2, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_y, width=10).grid(
            row=1, column=2, padx=(0, 12), sticky="w"
        )
        ttk.Label(controls, text=self.tr("الحجم", "Size")).grid(row=0, column=3, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_size, width=8).grid(
            row=1, column=3, sticky="w"
        )

        ttk.Label(self.add_text_tab, text=self.tr("خط TTF (اختياري لدعم العربية)", "TTF font (optional)")).grid(
            row=7, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_font_path, width=75).grid(
            row=8, column=0, sticky="we"
        )
        ttk.Button(self.add_text_tab, text=self.tr("اختيار خط", "Choose font"), command=self._pick_add_text_font).grid(
            row=8, column=1, padx=8
        )

        ttk.Button(self.add_text_tab, text=self.tr("إضافة النص", "Add text"), command=self._run_add_text).grid(
            row=9, column=0, pady=12, sticky="w"
        )
        ttk.Label(
            self.add_text_tab,
            text=self.tr(
                "ملاحظة: الإحداثيات تبدأ من أسفل يسار الصفحة.",
                "Note: coordinates start from the bottom-left of the page.",
            ),
        ).grid(row=10, column=0, sticky="w")
        self.add_text_tab.grid_columnconfigure(0, weight=1)

    def _pick_info_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_quick_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_merge_inputs(self) -> None:
        files = filedialog.askopenfilenames(filetypes=self._pdf_filetypes())
        if files:
            self._hydrate_merge_paths_from_entry()
            for file_path in files:
                if file_path not in self.merge_file_paths:
                    self.merge_file_paths.append(file_path)
            self._refresh_merge_list_ui()

    def _hydrate_merge_paths_from_entry(self) -> None:
        if self.merge_file_paths:
            return
        manual_values = [x.strip() for x in self.merge_inputs.get().split(";") if x.strip()]
        if manual_values:
            seen: set[str] = set()
            for value in manual_values:
                if value not in seen:
                    seen.add(value)
                    self.merge_file_paths.append(value)

    def _refresh_merge_list_ui(self, keep_selected: int | None = None) -> None:
        self.merge_inputs.set(";".join(self.merge_file_paths))
        self.merge_listbox.delete(0, tk.END)
        for file_path in self.merge_file_paths:
            self.merge_listbox.insert(tk.END, file_path)

        if keep_selected is not None and self.merge_file_paths:
            idx = max(0, min(keep_selected, len(self.merge_file_paths) - 1))
            self.merge_listbox.selection_set(idx)
            self.merge_listbox.activate(idx)

    def _remove_selected_merge_input(self) -> None:
        self._hydrate_merge_paths_from_entry()
        selected = self.merge_listbox.curselection()
        if not selected:
            return
        idx = selected[0]
        del self.merge_file_paths[idx]
        self._refresh_merge_list_ui(keep_selected=idx)

    def _move_selected_merge_input(self, delta: int) -> None:
        self._hydrate_merge_paths_from_entry()
        selected = self.merge_listbox.curselection()
        if not selected:
            return

        idx = selected[0]
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self.merge_file_paths):
            return

        self.merge_file_paths[idx], self.merge_file_paths[new_idx] = (
            self.merge_file_paths[new_idx],
            self.merge_file_paths[idx],
        )
        self._refresh_merge_list_ui(keep_selected=new_idx)

    def _pick_merge_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[(self.tr("ملفات PDF", "PDF files"), "*.pdf")]
        )
        if path:
            self.merge_output.set(path)

    def _pick_extract_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_extract_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[(self.tr("ملفات PDF", "PDF files"), "*.pdf")]
        )
        if path:
            self.extract_output.set(path)

    def _pick_insert_base_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_insert_pdf_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self.insert_pdf_input.set(path)

    def _pick_insert_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[(self.tr("ملفات PDF", "PDF files"), "*.pdf")]
        )
        if path:
            self.insert_output.set(path)

    def _pick_split_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_split_output_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.split_output_dir.set(path)

    def _pick_rotate_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_rotate_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[(self.tr("ملفات PDF", "PDF files"), "*.pdf")]
        )
        if path:
            self.rotate_output.set(path)

    def _pick_edit_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_edit_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[(self.tr("ملفات PDF", "PDF files"), "*.pdf")]
        )
        if path:
            self.edit_output.set(path)

    def _pick_add_text_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._pdf_filetypes())
        if path:
            self._apply_shared_input_to_tabs(path)

    def _pick_add_text_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[(self.tr("ملفات PDF", "PDF files"), "*.pdf")]
        )
        if path:
            self.add_text_output.set(path)

    def _pick_add_text_font(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("TTF", "*.ttf"), (self.tr("كل الملفات", "All files"), "*.*")])
        if path:
            self.add_text_font_path.set(path)

    def _run_info(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            raw = self.info_input.get().strip()
            if not raw:
                raise ValueError(self.tr("ملف PDF المدخل مطلوب.", "Input PDF file is required."))
            input_pdf = Path(raw)
            info = pdf_utils.get_pdf_info(input_pdf)
            self.info_text.delete("1.0", tk.END)
            lines = [f"{key}: {value}" for key, value in info.items()]
            self.info_text.insert(tk.END, "\n".join(lines))
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _run_merge(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            self._hydrate_merge_paths_from_entry()
            input_paths = [Path(x) for x in self.merge_file_paths if x.strip()]
            if not input_paths:
                raise ValueError(self.tr("اختر ملف PDF واحدًا على الأقل.", "Choose at least one PDF file."))
            output_raw = self.merge_output.get().strip()
            if not output_raw:
                raise ValueError(self.tr("ملف PDF الناتج مطلوب.", "Output PDF file is required."))
            output_pdf = Path(output_raw)
            pdf_utils.merge_pdfs(input_paths, output_pdf)
            messagebox.showinfo(
                self.tr("نجاح", "Success"),
                self.tr(
                    f"تم دمج {len(input_paths)} ملف(ات).",
                    f"Merged {len(input_paths)} file(s).",
                ),
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _run_extract(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_raw = self.extract_input.get().strip()
            output_raw = self.extract_output.get().strip()
            if not input_raw:
                raise ValueError(self.tr("ملف PDF المدخل مطلوب.", "Input PDF file is required."))
            if not output_raw:
                raise ValueError(self.tr("ملف PDF الناتج مطلوب.", "Output PDF file is required."))
            input_pdf = Path(input_raw)
            output_pdf = Path(output_raw)
            pages = self.extract_pages_var.get().strip()
            if not pages:
                raise ValueError(self.tr("صيغة الصفحات مطلوبة.", "Page range is required."))
            pdf_utils.extract_pages(input_pdf, output_pdf, pages)
            messagebox.showinfo(
                self.tr("نجاح", "Success"),
                self.tr("تم استخراج الصفحات بنجاح.", "Pages extracted successfully."),
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _run_insert(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            base_raw = self.insert_base_input.get().strip()
            insert_raw = self.insert_pdf_input.get().strip()
            output_raw = self.insert_output.get().strip()
            after_page = int(self.insert_after_page.get())

            if not base_raw:
                raise ValueError(self.tr("ملف PDF الأساسي مطلوب.", "Base PDF file is required."))
            if not insert_raw:
                raise ValueError(self.tr("ملف PDF المراد إدراجه مطلوب.", "PDF to insert is required."))
            if not output_raw:
                raise ValueError(self.tr("ملف PDF الناتج مطلوب.", "Output PDF file is required."))

            pdf_utils.insert_pdf_after_page(
                input_pdf=Path(base_raw),
                insert_pdf=Path(insert_raw),
                output_pdf=Path(output_raw),
                after_page=after_page,
            )
            messagebox.showinfo(
                self.tr("نجاح", "Success"),
                self.tr("تم إدراج الصفحات بنجاح.", "Pages inserted successfully."),
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _run_split(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_raw = self.split_input.get().strip()
            output_raw = self.split_output_dir.get().strip()
            if not input_raw:
                raise ValueError(self.tr("ملف PDF المدخل مطلوب.", "Input PDF file is required."))
            if not output_raw:
                raise ValueError(self.tr("مجلد الإخراج مطلوب.", "Output directory is required."))
            input_pdf = Path(input_raw)
            output_dir = Path(output_raw)
            pdf_utils.split_pdf(input_pdf, output_dir)
            messagebox.showinfo(
                self.tr("نجاح", "Success"),
                self.tr("تم تقسيم ملف PDF بنجاح.", "PDF split successfully."),
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _run_rotate(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_raw = self.rotate_input.get().strip()
            output_raw = self.rotate_output.get().strip()
            if not input_raw:
                raise ValueError(self.tr("ملف PDF المدخل مطلوب.", "Input PDF file is required."))
            if not output_raw:
                raise ValueError(self.tr("ملف PDF الناتج مطلوب.", "Output PDF file is required."))
            input_pdf = Path(input_raw)
            output_pdf = Path(output_raw)
            pages = self.rotate_pages_var.get().strip()
            if not pages:
                raise ValueError(self.tr("صيغة الصفحات مطلوبة.", "Page range is required."))
            angle = int(self.rotate_angle.get())
            pdf_utils.rotate_pages(input_pdf, output_pdf, pages, angle)
            messagebox.showinfo(
                self.tr("نجاح", "Success"),
                self.tr("تم تدوير الصفحات بنجاح.", "Pages rotated successfully."),
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _run_edit(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_raw = self.edit_input.get().strip()
            output_raw = self.edit_output.get().strip()
            find_text = self.edit_find.get()
            replace_text = self.edit_replace.get()
            pages = self.edit_pages.get().strip()

            if not input_raw:
                raise ValueError(self.tr("ملف PDF المدخل مطلوب.", "Input PDF file is required."))
            if not output_raw:
                raise ValueError(self.tr("ملف PDF الناتج مطلوب.", "Output PDF file is required."))
            if not find_text:
                raise ValueError(self.tr("النص المطلوب استبداله مطلوب.", "Text to find is required."))

            input_pdf = Path(input_raw)
            output_pdf = Path(output_raw)

            replaced_count = pdf_utils.replace_text_in_pdf(
                input_pdf=input_pdf,
                output_pdf=output_pdf,
                find_text=find_text,
                replace_text=replace_text,
                pages=pages if pages else None,
            )
            messagebox.showinfo(
                self.tr("نجاح", "Success"),
                self.tr(
                    f"تم استبدال {replaced_count} حالة بنجاح.",
                    f"Replaced {replaced_count} occurrence(s) successfully.",
                ),
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _run_add_text(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return

            input_raw = self.add_text_input.get().strip()
            output_raw = self.add_text_output.get().strip()
            text_value = self.add_text_value.get()
            page_num = int(self.add_text_page.get())
            x_pos = float(self.add_text_x.get())
            y_pos = float(self.add_text_y.get())
            font_size = int(self.add_text_size.get())
            font_path = self.add_text_font_path.get().strip() or None

            if not input_raw:
                raise ValueError(self.tr("ملف PDF المدخل مطلوب.", "Input PDF file is required."))
            if not output_raw:
                raise ValueError(self.tr("ملف PDF الناتج مطلوب.", "Output PDF file is required."))
            if not text_value:
                raise ValueError(self.tr("النص المراد إضافته مطلوب.", "Text to add is required."))

            pdf_utils.add_text_overlay(
                input_pdf=Path(input_raw),
                output_pdf=Path(output_raw),
                page_number=page_num,
                text=text_value,
                x=x_pos,
                y=y_pos,
                font_size=font_size,
                font_path=font_path,
            )
            messagebox.showinfo(
                self.tr("نجاح", "Success"),
                self.tr("تمت إضافة النص بنجاح.", "Text added successfully."),
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _open_in_xournal(self) -> None:
        try:
            xournal_bin = shutil.which("xournalpp")
            if xournal_bin is None:
                raise ValueError(
                    self.tr(
                        "برنامج Xournal++ غير مثبت. ثبّت الحزمة xournalpp أولًا.",
                        "Xournal++ is not installed. Install the xournalpp package first.",
                    )
                )

            raw_path = self.quick_pdf_path.get().strip()
            if not raw_path:
                raise ValueError(self.tr("اختر ملفًا أولًا.", "Choose a file first."))

            src = Path(raw_path)
            if not src.exists():
                raise ValueError(self.tr("الملف غير موجود.", "File does not exist."))

            open_path = src
            if src.suffix.lower() != ".pdf":
                open_path = src.with_suffix(".pdf")
                shutil.copyfile(src, open_path)

            # Xournal++ can emit noisy ALSA/JACK warnings on systems without audio devices.
            # Keep the GUI experience clean by detaching it from this terminal output.
            subprocess.Popen(
                [xournal_bin, str(open_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as exc:
            messagebox.showerror(self.tr("خطأ", "Error"), str(exc))

    def _load_pdf_utils(self):
        try:
            return importlib.import_module(".pdf_utils", __package__)
        except ModuleNotFoundError as exc:
            messagebox.showerror(
                self.tr("متطلب مفقود", "Missing dependency"),
                self.tr(
                    f"{exc}\n\nثبّت المتطلبات أولًا:\npip install -r requirements.txt",
                    f"{exc}\n\nInstall dependencies first:\npip install -r requirements.txt",
                ),
            )
            return None


def run_gui(language: str = "ar") -> None:
    app = PDFControlApp(language=language)
    app.mainloop()
