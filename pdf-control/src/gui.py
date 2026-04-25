from __future__ import annotations

import importlib
import shutil
import subprocess
import tkinter as tk
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
    def __init__(self) -> None:
        super().__init__()
        self.title(ar("لوحة التحكم بملفات PDF"))
        self.geometry("860x620")
        self.minsize(760, 540)
        self.state("normal")

        self._build_ui()
        self.after(120, self._place_and_focus_window)
        # A gentle second focus pass helps some WSLg setups without re-minimizing.
        self.after(900, self._force_show_window)

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
            text=ar("لوحة التحكم بملفات PDF"),
            bg="#1f2937",
            fg="#f8fafc",
            font=("TkDefaultFont", 13, "bold"),
            padx=12,
            pady=8,
            anchor="w",
        )
        title_text.pack(fill="x")

        subtitle_text = tk.Label(
            title_bar,
            text=ar("إدارة PDF: دمج، استخراج، تدوير، تعديل وإضافة نص"),
            bg="#1f2937",
            fg="#cbd5e1",
            font=("TkDefaultFont", 10),
            padx=12,
            pady=(0, 8),
            anchor="w",
        )
        subtitle_text.pack(fill="x")

        self.quick_pdf_path = tk.StringVar()
        quick_frame = ttk.Frame(container)
        quick_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(quick_frame, text=ar("فتح للمعاينة/التعديل في Xournal++")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Entry(quick_frame, textvariable=self.quick_pdf_path, width=72).grid(row=1, column=0, sticky="we")
        ttk.Button(quick_frame, text=ar("استعراض"), command=self._pick_quick_pdf).grid(row=1, column=1, padx=8)
        ttk.Button(quick_frame, text=ar("فتح في Xournal++"), command=self._open_in_xournal).grid(row=1, column=2, sticky="w")
        quick_frame.grid_columnconfigure(0, weight=1)

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        self.info_tab = ttk.Frame(notebook, padding=12)
        self.merge_tab = ttk.Frame(notebook, padding=12)
        self.extract_tab = ttk.Frame(notebook, padding=12)
        self.split_tab = ttk.Frame(notebook, padding=12)
        self.rotate_tab = ttk.Frame(notebook, padding=12)
        self.edit_tab = ttk.Frame(notebook, padding=12)
        self.add_text_tab = ttk.Frame(notebook, padding=12)

        notebook.add(self.info_tab, text=ar("معلومات"))
        notebook.add(self.merge_tab, text=ar("دمج"))
        notebook.add(self.extract_tab, text=ar("استخراج"))
        notebook.add(self.split_tab, text=ar("تقسيم"))
        notebook.add(self.rotate_tab, text=ar("تدوير"))
        notebook.add(self.edit_tab, text=ar("تعديل النص"))
        notebook.add(self.add_text_tab, text=ar("إضافة نص"))

        self._build_info_tab()
        self._build_merge_tab()
        self._build_extract_tab()
        self._build_split_tab()
        self._build_rotate_tab()
        self._build_edit_tab()
        self._build_add_text_tab()

    def _build_info_tab(self) -> None:
        self.info_input = tk.StringVar()
        ttk.Label(self.info_tab, text=ar("ملف PDF المدخل")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.info_tab, textvariable=self.info_input, width=75).grid(
            row=1, column=0, padx=(0, 8), sticky="we"
        )
        ttk.Button(self.info_tab, text=ar("استعراض"), command=self._pick_info_input).grid(row=1, column=1, sticky="w")
        ttk.Button(self.info_tab, text=ar("عرض المعلومات"), command=self._run_info).grid(row=2, column=0, pady=10, sticky="w")

        self.info_text = tk.Text(self.info_tab, height=22, wrap="word")
        self.info_text.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.info_tab.grid_columnconfigure(0, weight=1)
        self.info_tab.grid_rowconfigure(3, weight=1)

    def _build_merge_tab(self) -> None:
        self.merge_inputs = tk.StringVar()
        self.merge_output = tk.StringVar()

        ttk.Label(self.merge_tab, text=ar("ملفات PDF المدخلة (متعددة)")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.merge_tab, textvariable=self.merge_inputs, width=75).grid(row=1, column=0, sticky="we")
        ttk.Button(self.merge_tab, text=ar("استعراض"), command=self._pick_merge_inputs).grid(row=1, column=1, padx=8)

        ttk.Label(self.merge_tab, text=ar("ملف PDF الناتج")).grid(row=2, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.merge_tab, textvariable=self.merge_output, width=75).grid(row=3, column=0, sticky="we")
        ttk.Button(self.merge_tab, text=ar("حفظ باسم"), command=self._pick_merge_output).grid(row=3, column=1, padx=8)

        ttk.Button(self.merge_tab, text=ar("دمج"), command=self._run_merge).grid(row=4, column=0, pady=12, sticky="w")
        self.merge_tab.grid_columnconfigure(0, weight=1)

    def _build_extract_tab(self) -> None:
        self.extract_input = tk.StringVar()
        self.extract_output = tk.StringVar()
        self.extract_pages_var = tk.StringVar()

        ttk.Label(self.extract_tab, text=ar("ملف PDF المدخل")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.extract_tab, textvariable=self.extract_input, width=75).grid(row=1, column=0, sticky="we")
        ttk.Button(self.extract_tab, text=ar("استعراض"), command=self._pick_extract_input).grid(row=1, column=1, padx=8)

        ttk.Label(self.extract_tab, text=ar("ملف PDF الناتج")).grid(row=2, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.extract_tab, textvariable=self.extract_output, width=75).grid(row=3, column=0, sticky="we")
        ttk.Button(self.extract_tab, text=ar("حفظ باسم"), command=self._pick_extract_output).grid(row=3, column=1, padx=8)

        ttk.Label(self.extract_tab, text=ar('الصفحات (مثال: "1,3,5-7")')).grid(row=4, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.extract_tab, textvariable=self.extract_pages_var, width=30).grid(row=5, column=0, sticky="w")

        ttk.Button(self.extract_tab, text=ar("استخراج"), command=self._run_extract).grid(row=6, column=0, pady=12, sticky="w")
        self.extract_tab.grid_columnconfigure(0, weight=1)

    def _build_split_tab(self) -> None:
        self.split_input = tk.StringVar()
        self.split_output_dir = tk.StringVar()

        ttk.Label(self.split_tab, text=ar("ملف PDF المدخل")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.split_tab, textvariable=self.split_input, width=75).grid(row=1, column=0, sticky="we")
        ttk.Button(self.split_tab, text=ar("استعراض"), command=self._pick_split_input).grid(row=1, column=1, padx=8)

        ttk.Label(self.split_tab, text=ar("مجلد الإخراج")).grid(row=2, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.split_tab, textvariable=self.split_output_dir, width=75).grid(row=3, column=0, sticky="we")
        ttk.Button(self.split_tab, text=ar("اختيار"), command=self._pick_split_output_dir).grid(row=3, column=1, padx=8)

        ttk.Button(self.split_tab, text=ar("تقسيم"), command=self._run_split).grid(row=4, column=0, pady=12, sticky="w")
        self.split_tab.grid_columnconfigure(0, weight=1)

    def _build_rotate_tab(self) -> None:
        self.rotate_input = tk.StringVar()
        self.rotate_output = tk.StringVar()
        self.rotate_pages_var = tk.StringVar()
        self.rotate_angle = tk.IntVar(value=90)

        ttk.Label(self.rotate_tab, text=ar("ملف PDF المدخل")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.rotate_tab, textvariable=self.rotate_input, width=75).grid(row=1, column=0, sticky="we")
        ttk.Button(self.rotate_tab, text=ar("استعراض"), command=self._pick_rotate_input).grid(row=1, column=1, padx=8)

        ttk.Label(self.rotate_tab, text=ar("ملف PDF الناتج")).grid(row=2, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.rotate_tab, textvariable=self.rotate_output, width=75).grid(row=3, column=0, sticky="we")
        ttk.Button(self.rotate_tab, text=ar("حفظ باسم"), command=self._pick_rotate_output).grid(row=3, column=1, padx=8)

        ttk.Label(self.rotate_tab, text=ar('الصفحات (مثال: "1-3,5")')).grid(row=4, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.rotate_tab, textvariable=self.rotate_pages_var, width=30).grid(row=5, column=0, sticky="w")

        ttk.Label(self.rotate_tab, text=ar("زاوية التدوير")).grid(row=6, column=0, pady=(10, 0), sticky="w")
        ttk.Combobox(self.rotate_tab, textvariable=self.rotate_angle, values=[90, 180, 270], width=8, state="readonly").grid(
            row=7, column=0, sticky="w"
        )

        ttk.Button(self.rotate_tab, text=ar("تدوير"), command=self._run_rotate).grid(row=8, column=0, pady=12, sticky="w")
        self.rotate_tab.grid_columnconfigure(0, weight=1)

    def _build_edit_tab(self) -> None:
        self.edit_input = tk.StringVar()
        self.edit_output = tk.StringVar()
        self.edit_find = tk.StringVar()
        self.edit_replace = tk.StringVar()
        self.edit_pages = tk.StringVar()

        ttk.Label(self.edit_tab, text=ar("ملف PDF المدخل")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.edit_tab, textvariable=self.edit_input, width=75).grid(row=1, column=0, sticky="we")
        ttk.Button(self.edit_tab, text=ar("استعراض"), command=self._pick_edit_input).grid(row=1, column=1, padx=8)

        ttk.Label(self.edit_tab, text=ar("ملف PDF الناتج")).grid(row=2, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.edit_tab, textvariable=self.edit_output, width=75).grid(row=3, column=0, sticky="we")
        ttk.Button(self.edit_tab, text=ar("حفظ باسم"), command=self._pick_edit_output).grid(row=3, column=1, padx=8)

        ttk.Label(self.edit_tab, text=ar("النص المطلوب استبداله")).grid(row=4, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.edit_tab, textvariable=self.edit_find, width=40).grid(row=5, column=0, sticky="w")

        ttk.Label(self.edit_tab, text=ar("النص البديل")).grid(row=6, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.edit_tab, textvariable=self.edit_replace, width=40).grid(row=7, column=0, sticky="w")

        ttk.Label(self.edit_tab, text=ar('الصفحات (اختياري، مثال: "1,3,5-7")')).grid(row=8, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.edit_tab, textvariable=self.edit_pages, width=40).grid(row=9, column=0, sticky="w")

        ttk.Button(self.edit_tab, text=ar("تعديل النص"), command=self._run_edit).grid(row=10, column=0, pady=12, sticky="w")
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

        ttk.Label(self.add_text_tab, text=ar("ملف PDF المدخل")).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_input, width=75).grid(row=1, column=0, sticky="we")
        ttk.Button(self.add_text_tab, text=ar("استعراض"), command=self._pick_add_text_input).grid(row=1, column=1, padx=8)

        ttk.Label(self.add_text_tab, text=ar("ملف PDF الناتج")).grid(row=2, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_output, width=75).grid(row=3, column=0, sticky="we")
        ttk.Button(self.add_text_tab, text=ar("حفظ باسم"), command=self._pick_add_text_output).grid(row=3, column=1, padx=8)

        ttk.Label(self.add_text_tab, text=ar("النص المراد إضافته")).grid(row=4, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_value, width=60).grid(row=5, column=0, sticky="w")

        controls = ttk.Frame(self.add_text_tab)
        controls.grid(row=6, column=0, pady=(10, 0), sticky="w")
        ttk.Label(controls, text=ar("الصفحة")).grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_page, width=8).grid(row=1, column=0, padx=(0, 12), sticky="w")
        ttk.Label(controls, text="X").grid(row=0, column=1, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_x, width=10).grid(row=1, column=1, padx=(0, 12), sticky="w")
        ttk.Label(controls, text="Y").grid(row=0, column=2, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_y, width=10).grid(row=1, column=2, padx=(0, 12), sticky="w")
        ttk.Label(controls, text=ar("الحجم")).grid(row=0, column=3, sticky="w")
        ttk.Entry(controls, textvariable=self.add_text_size, width=8).grid(row=1, column=3, sticky="w")

        ttk.Label(self.add_text_tab, text=ar("خط TTF (اختياري لدعم العربية)")).grid(row=7, column=0, pady=(10, 0), sticky="w")
        ttk.Entry(self.add_text_tab, textvariable=self.add_text_font_path, width=75).grid(row=8, column=0, sticky="we")
        ttk.Button(self.add_text_tab, text=ar("اختيار خط"), command=self._pick_add_text_font).grid(row=8, column=1, padx=8)

        ttk.Button(self.add_text_tab, text=ar("إضافة النص"), command=self._run_add_text).grid(row=9, column=0, pady=12, sticky="w")
        ttk.Label(
            self.add_text_tab,
            text=ar("ملاحظة: الإحداثيات تبدأ من أسفل يسار الصفحة."),
        ).grid(row=10, column=0, sticky="w")
        self.add_text_tab.grid_columnconfigure(0, weight=1)

    def _pick_info_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.info_input.set(path)

    def _pick_quick_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.quick_pdf_path.set(path)

    def _pick_merge_inputs(self) -> None:
        files = filedialog.askopenfilenames(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if files:
            self.merge_inputs.set(";".join(files))

    def _pick_merge_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[(ar("ملفات PDF"), "*.pdf")])
        if path:
            self.merge_output.set(path)

    def _pick_extract_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.extract_input.set(path)

    def _pick_extract_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[(ar("ملفات PDF"), "*.pdf")])
        if path:
            self.extract_output.set(path)

    def _pick_split_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.split_input.set(path)

    def _pick_split_output_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.split_output_dir.set(path)

    def _pick_rotate_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.rotate_input.set(path)

    def _pick_rotate_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[(ar("ملفات PDF"), "*.pdf")])
        if path:
            self.rotate_output.set(path)

    def _pick_edit_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.edit_input.set(path)

    def _pick_edit_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[(ar("ملفات PDF"), "*.pdf")])
        if path:
            self.edit_output.set(path)

    def _pick_add_text_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[(ar("ملفات PDF"), "*.pdf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.add_text_input.set(path)

    def _pick_add_text_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[(ar("ملفات PDF"), "*.pdf")])
        if path:
            self.add_text_output.set(path)

    def _pick_add_text_font(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("TTF", "*.ttf"), (ar("كل الملفات"), "*.*")])
        if path:
            self.add_text_font_path.set(path)

    def _run_info(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            raw = self.info_input.get().strip()
            if not raw:
                raise ValueError(ar("ملف PDF المدخل مطلوب."))
            input_pdf = Path(raw)
            info = pdf_utils.get_pdf_info(input_pdf)
            self.info_text.delete("1.0", tk.END)
            lines = [f"{key}: {value}" for key, value in info.items()]
            self.info_text.insert(tk.END, "\n".join(lines))
        except Exception as exc:
            messagebox.showerror(ar("خطأ"), str(exc))

    def _run_merge(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_paths = [Path(x) for x in self.merge_inputs.get().split(";") if x.strip()]
            if not input_paths:
                raise ValueError(ar("اختر ملف PDF واحدًا على الأقل."))
            output_raw = self.merge_output.get().strip()
            if not output_raw:
                raise ValueError(ar("ملف PDF الناتج مطلوب."))
            output_pdf = Path(output_raw)
            pdf_utils.merge_pdfs(input_paths, output_pdf)
            messagebox.showinfo(ar("نجاح"), ar(f"تم دمج {len(input_paths)} ملف(ات)."))
        except Exception as exc:
            messagebox.showerror(ar("خطأ"), str(exc))

    def _run_extract(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_raw = self.extract_input.get().strip()
            output_raw = self.extract_output.get().strip()
            if not input_raw:
                raise ValueError(ar("ملف PDF المدخل مطلوب."))
            if not output_raw:
                raise ValueError(ar("ملف PDF الناتج مطلوب."))
            input_pdf = Path(input_raw)
            output_pdf = Path(output_raw)
            pages = self.extract_pages_var.get().strip()
            if not pages:
                raise ValueError(ar("صيغة الصفحات مطلوبة."))
            pdf_utils.extract_pages(input_pdf, output_pdf, pages)
            messagebox.showinfo(ar("نجاح"), ar("تم استخراج الصفحات بنجاح."))
        except Exception as exc:
            messagebox.showerror(ar("خطأ"), str(exc))

    def _run_split(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_raw = self.split_input.get().strip()
            output_raw = self.split_output_dir.get().strip()
            if not input_raw:
                raise ValueError(ar("ملف PDF المدخل مطلوب."))
            if not output_raw:
                raise ValueError(ar("مجلد الإخراج مطلوب."))
            input_pdf = Path(input_raw)
            output_dir = Path(output_raw)
            pdf_utils.split_pdf(input_pdf, output_dir)
            messagebox.showinfo(ar("نجاح"), ar("تم تقسيم ملف PDF بنجاح."))
        except Exception as exc:
            messagebox.showerror(ar("خطأ"), str(exc))

    def _run_rotate(self) -> None:
        try:
            pdf_utils = self._load_pdf_utils()
            if pdf_utils is None:
                return
            input_raw = self.rotate_input.get().strip()
            output_raw = self.rotate_output.get().strip()
            if not input_raw:
                raise ValueError(ar("ملف PDF المدخل مطلوب."))
            if not output_raw:
                raise ValueError(ar("ملف PDF الناتج مطلوب."))
            input_pdf = Path(input_raw)
            output_pdf = Path(output_raw)
            pages = self.rotate_pages_var.get().strip()
            if not pages:
                raise ValueError(ar("صيغة الصفحات مطلوبة."))
            angle = int(self.rotate_angle.get())
            pdf_utils.rotate_pages(input_pdf, output_pdf, pages, angle)
            messagebox.showinfo(ar("نجاح"), ar("تم تدوير الصفحات بنجاح."))
        except Exception as exc:
            messagebox.showerror(ar("خطأ"), str(exc))

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
                raise ValueError(ar("ملف PDF المدخل مطلوب."))
            if not output_raw:
                raise ValueError(ar("ملف PDF الناتج مطلوب."))
            if not find_text:
                raise ValueError(ar("النص المطلوب استبداله مطلوب."))

            input_pdf = Path(input_raw)
            output_pdf = Path(output_raw)

            replaced_count = pdf_utils.replace_text_in_pdf(
                input_pdf=input_pdf,
                output_pdf=output_pdf,
                find_text=find_text,
                replace_text=replace_text,
                pages=pages if pages else None,
            )
            messagebox.showinfo(ar("نجاح"), ar(f"تم استبدال {replaced_count} حالة بنجاح."))
        except Exception as exc:
            messagebox.showerror(ar("خطأ"), str(exc))

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
                raise ValueError(ar("ملف PDF المدخل مطلوب."))
            if not output_raw:
                raise ValueError(ar("ملف PDF الناتج مطلوب."))
            if not text_value:
                raise ValueError(ar("النص المراد إضافته مطلوب."))

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
            messagebox.showinfo(ar("نجاح"), ar("تمت إضافة النص بنجاح."))
        except Exception as exc:
            messagebox.showerror(ar("خطأ"), str(exc))

    def _open_in_xournal(self) -> None:
        try:
            xournal_bin = shutil.which("xournalpp")
            if xournal_bin is None:
                raise ValueError(ar("برنامج Xournal++ غير مثبت. ثبّت الحزمة xournalpp أولًا."))

            raw_path = self.quick_pdf_path.get().strip()
            if not raw_path:
                raise ValueError(ar("اختر ملفًا أولًا."))

            src = Path(raw_path)
            if not src.exists():
                raise ValueError(ar("الملف غير موجود."))

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
            messagebox.showerror(ar("خطأ"), str(exc))

    @staticmethod
    def _load_pdf_utils():
        try:
            return importlib.import_module(".pdf_utils", __package__)
        except ModuleNotFoundError as exc:
            messagebox.showerror(
                ar("متطلب مفقود"),
                ar(f"{exc}\n\nثبّت المتطلبات أولًا:\npip install -r requirements.txt"),
            )
            return None


def run_gui() -> None:
    app = PDFControlApp()
    app.mainloop()
