import customtkinter as ctk
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox
import webbrowser
import requests

from utils import async_helper, image_cache


class PhotoGallery(ctk.CTkFrame):
    """Универсальная кликабельная галерея фотографий"""

    def __init__(self, parent, width=300, height=210, **kwargs):
        super().__init__(parent, width=width, height=height, **kwargs)
        self.configure(fg_color="#1e1e1e", corner_radius=8)
        self.pack_propagate(False)

        self._width = width
        self._height = height - 35
        self._urls: list = []
        self._current_index: int = 0
        self._loaded_images: dict = {}
        self._tk_images: dict = {}
        self._destroyed = False

        self._build_ui()

    def _build_ui(self):
        self.photo_container = ctk.CTkFrame(
            self, fg_color="#1a1a1a",
            corner_radius=6, cursor="hand2"
        )
        self.photo_container.pack(fill="both", expand=True)

        self.photo_label = ctk.CTkLabel(
            self.photo_container,
            text="📷", font=ctk.CTkFont(size=28),
            text_color="#444444", cursor="hand2"
        )
        self.photo_label.pack(expand=True, fill="both")

        self.hint_label = ctk.CTkLabel(
            self.photo_container,
            text="", font=ctk.CTkFont(size=10),
            text_color="#4fc3f7", fg_color="transparent",
            cursor="hand2"
        )
        self.hint_label.place(relx=0.5, rely=0.88, anchor="center")

        for w in [self.photo_container, self.photo_label, self.hint_label]:
            w.bind("<Button-1>", self._open_viewer)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        nav = ctk.CTkFrame(self, fg_color="#161616", height=32)
        nav.pack(fill="x", side="bottom")
        nav.pack_propagate(False)

        ctk.CTkButton(
            nav, text="◀", width=38, height=26,
            command=self._prev, fg_color="#2a2a2a",
            hover_color="#3a3a3a", corner_radius=6
        ).pack(side="left", padx=4, pady=3)

        self.counter_label = ctk.CTkLabel(
            nav, text="Нет фото",
            font=ctk.CTkFont(size=11), text_color="#666666"
        )
        self.counter_label.pack(side="left", expand=True)

        ctk.CTkButton(
            nav, text="▶", width=38, height=26,
            command=self._next, fg_color="#2a2a2a",
            hover_color="#3a3a3a", corner_radius=6
        ).pack(side="right", padx=4, pady=3)

    def _on_enter(self, e=None):
        if self._urls:
            self.photo_container.configure(fg_color="#252525")
            self.hint_label.configure(text="🔍 Нажмите для просмотра")

    def _on_leave(self, e=None):
        self.photo_container.configure(fg_color="#1a1a1a")
        self.hint_label.configure(text="")

    def _open_viewer(self, e=None):
        if not self._urls:
            return
        from utils.image_viewer import ImageViewer
        ImageViewer(self.winfo_toplevel(), self._urls, self._current_index)

    def load_photos(self, urls: list):
        if not urls:
            self.photo_label.configure(text="📷", image=None)
            self.counter_label.configure(text="Нет фото")
            return
        self._urls = urls
        self._current_index = 0
        self._loaded_images.clear()
        self._tk_images.clear()
        self.counter_label.configure(text=f"1/{len(urls)}", text_color="#aaaaaa")
        self.photo_label.configure(image=None, text="⏳",
                                   font=ctk.CTkFont(size=24), text_color="#555555")
        self._load_async(urls[0])
        if len(urls) > 1:
            self.after(600, lambda: [self._load_async(u) for u in urls[1:5]])

    def _load_async(self, url):
        if self._destroyed:
            return
        async_helper.run_coroutine(
            image_cache.load_image_async(
                url=url, size=(self._width - 10, self._height - 10),
                callback=self._on_loaded, widget_ref=self
            )
        )

    def _on_loaded(self, img, url):
        if self._destroyed or img is None:
            return
        self._loaded_images[url] = img
        if self._urls and url == self._urls[self._current_index]:
            self._display(url)
        self._update_counter()

    def _display(self, url):
        if self._destroyed:
            return
        img = self._loaded_images.get(url)
        if not img:
            return
        tk_img = ImageTk.PhotoImage(img)
        self._tk_images[url] = tk_img
        self.photo_label.configure(image=tk_img, text="")
        self.photo_label.image = tk_img

    def _update_counter(self):
        if self._destroyed or not self._urls:
            return
        total = len(self._urls)
        loaded = sum(1 for u in self._urls if u in self._loaded_images)
        suffix = f" ✓{loaded}" if loaded < total else ""
        self.counter_label.configure(
            text=f"{self._current_index + 1}/{total}{suffix}",
            text_color="#aaaaaa"
        )

    def _show_index(self, index):
        if not self._urls:
            return
        self._current_index = index % len(self._urls)
        url = self._urls[self._current_index]
        if url in self._loaded_images:
            self._display(url)
        else:
            self.photo_label.configure(image=None, text="⏳",
                                       font=ctk.CTkFont(size=24), text_color="#555555")
            self._load_async(url)
        self._update_counter()

    def _prev(self): self._show_index(self._current_index - 1)
    def _next(self): self._show_index(self._current_index + 1)

    def destroy(self):
        self._destroyed = True
        super().destroy()


class ExpandableText(ctk.CTkFrame):
    """
    Разворачиваемое описание с возможностью копирования.
    Копирование через кнопку или Ctrl+A в развёрнутом режиме.
    """

    COLLAPSED_CHARS = 200

    def __init__(self, parent, text: str, accent_color="#4fc3f7", **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color="#1e1e1e", corner_radius=8)

        self._full_text = text
        self._accent = accent_color
        self._expanded = False
        self._has_more = len(text) > self.COLLAPSED_CHARS

        self._build_ui()

    def _build_ui(self):
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="#252525", corner_radius=6)
        header.pack(fill="x")

        ctk.CTkLabel(
            header, text="📝 Описание:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#aaaaaa"
        ).pack(side="left", padx=10, pady=5)

        # Кнопка копировать
        self.copy_btn = ctk.CTkButton(
            header,
            text="📋 Копировать",
            width=115, height=26,
            command=self._copy_text,
            fg_color="#2a3a2a",
            hover_color="#3a4a3a",
            text_color="#81c784",
            font=ctk.CTkFont(size=11),
            corner_radius=6
        )
        self.copy_btn.pack(side="right", padx=5, pady=4)

        # Кнопка развернуть (если текст длинный)
        if self._has_more:
            self.toggle_btn = ctk.CTkButton(
                header,
                text="▼ Развернуть",
                width=115, height=26,
                command=self._toggle,
                fg_color="#2a2a2a",
                hover_color="#3a3a3a",
                text_color=self._accent,
                font=ctk.CTkFont(size=11),
                corner_radius=6
            )
            self.toggle_btn.pack(side="right", padx=(5, 0), pady=4)

        # Свёрнутый вид — обычный label
        self.short_label = ctk.CTkLabel(
            self,
            text=self._short_text(),
            font=ctk.CTkFont(size=11),
            text_color="#cccccc",
            wraplength=450,
            justify="left",
            anchor="nw"
        )
        self.short_label.pack(padx=10, pady=(5, 8), fill="x", anchor="w")

        if self._has_more:
            self.short_label.configure(cursor="hand2")
            self.short_label.bind("<Button-1>", lambda e: self._toggle())

        # Развёрнутый вид — текстбокс с возможностью выделения
        self.full_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(size=11),
            fg_color="#141414",
            text_color="#cccccc",
            corner_radius=6,
            wrap="word",
            height=150,
            state="normal"
        )
        # Вставляем текст
        self.full_textbox.insert("1.0", self._full_text)
        # Делаем только для чтения, но с возможностью выделения
        self.full_textbox.configure(state="disabled")
        # НЕ паkуем — покажем только при разворачивании

        # Биндим Ctrl+C на textbox
        self.full_textbox.bind("<Control-c>", self._on_ctrl_c)
        self.full_textbox.bind("<Control-a>", self._select_all)

    def _short_text(self) -> str:
        if len(self._full_text) <= self.COLLAPSED_CHARS:
            return self._full_text
        return self._full_text[:self.COLLAPSED_CHARS] + "..."

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self.short_label.pack_forget()
            self.full_textbox.pack(
                fill="x", padx=8, pady=(4, 8)
            )
            if self._has_more:
                self.toggle_btn.configure(text="▲ Свернуть")
        else:
            self.full_textbox.pack_forget()
            self.short_label.pack(
                padx=10, pady=(5, 8), fill="x", anchor="w"
            )
            if self._has_more:
                self.toggle_btn.configure(text="▼ Развернуть")

    def _copy_text(self):
        """Копирование полного текста в буфер обмена"""
        try:
            self.clipboard_clear()
            self.clipboard_append(self._full_text)
            self.update()

            # Визуальный фидбек
            self.copy_btn.configure(
                text="✅ Скопировано!",
                fg_color="#1a4a1a",
                text_color="#81c784"
            )
            self.after(2000, lambda: self.copy_btn.configure(
                text="📋 Копировать",
                fg_color="#2a3a2a",
                text_color="#81c784"
            ))
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    def _on_ctrl_c(self, event):
        """Ctrl+C в текстбоксе"""
        try:
            selected = self.full_textbox.get("sel.first", "sel.last")
            if selected:
                self.clipboard_clear()
                self.clipboard_append(selected)
        except tk.TclError:
            pass

    def _select_all(self, event):
        """Ctrl+A — выделить весь текст"""
        self.full_textbox.configure(state="normal")
        self.full_textbox.tag_add("sel", "1.0", "end")
        self.full_textbox.configure(state="disabled")
        return "break"

    def update_text(self, text: str):
        self._full_text = text
        self._has_more = len(text) > self.COLLAPSED_CHARS
        self._expanded = False
        self.short_label.configure(text=self._short_text())
        self.full_textbox.configure(state="normal")
        self.full_textbox.delete("1.0", "end")
        self.full_textbox.insert("1.0", text)
        self.full_textbox.configure(state="disabled")


class PhoneWidget(ctk.CTkFrame):
    """
    Виджет отображения телефонов.
    Показывает все номера, каждый можно скопировать.
    """

    def __init__(self, parent, apartment: dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color="#252525", corner_radius=6)
        self._apt = apartment
        self._build()

    def _build(self):
        phones = self._apt.get("phones_list", [])

        # Если нет списка — берём строку
        if not phones:
            phone_str = self._apt.get("phone", "Не указан")
            if phone_str and phone_str != "Не указан":
                phones = [p.strip() for p in phone_str.split("/")]
            else:
                phones = []

        # Имя контакта
        contact = self._apt.get("contact_name", "")

        if not phones:
            ctk.CTkLabel(
                self, text="📞 Телефон не указан",
                font=ctk.CTkFont(size=12), text_color="#888888"
            ).pack(padx=10, pady=5)
            return

        # Заголовок
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(5, 2))

        ctk.CTkLabel(
            header, text="📞 Контакты:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#aaaaaa"
        ).pack(side="left")

        if contact:
            ctk.CTkLabel(
                header, text=f"  👤 {contact}",
                font=ctk.CTkFont(size=11),
                text_color="#4fc3f7"
            ).pack(side="left")

        # Каждый номер на отдельной строке с кнопкой копирования
        for phone in phones:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)

            ctk.CTkLabel(
                row,
                text=phone,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ffffff"
            ).pack(side="left")

            ctk.CTkButton(
                row,
                text="📋",
                width=30, height=24,
                command=lambda p=phone: self._copy_phone(p),
                fg_color="#2a2a2a",
                hover_color="#3a3a3a",
                font=ctk.CTkFont(size=12),
                corner_radius=4
            ).pack(side="left", padx=(6, 0))

        # Отступ снизу
        ctk.CTkFrame(self, fg_color="transparent", height=3).pack()

    def _copy_phone(self, phone: str):
        """Копировать номер в буфер"""
        # Оставляем только цифры для удобства набора
        digits_only = re.sub(r'\D', '', phone)
        try:
            self.clipboard_clear()
            self.clipboard_append(digits_only)
            self.update()
        except Exception:
            pass


import re  # Нужен для PhoneWidget


class ApartmentInfoBar(ctk.CTkFrame):
    """Панель мета-информации о квартире"""

    def __init__(self, parent, apartment: dict,
                 show_map: bool = True, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color="transparent")
        self._apt = apartment
        self._build(show_map)

    def _build(self, show_map: bool):
        # Комнаты + площадь + этаж
        row1 = ctk.CTkFrame(self, fg_color="#252525", corner_radius=6)
        row1.pack(fill="x", pady=(0, 4))

        rooms_text = self._apt.get("rooms", "Не указано")
        area = self._apt.get("area", "")
        floor = self._apt.get("floor", "")

        meta_parts = [f"🏠 {rooms_text}"]
        if area:
            meta_parts.append(f"📐 {area}")
        if floor:
            meta_parts.append(f"🏢 {floor}")

        ctk.CTkLabel(
            row1,
            text="   ".join(meta_parts),
            font=ctk.CTkFont(size=12),
            text_color="#e0e0e0"
        ).pack(side="left", padx=10, pady=6)

        ctk.CTkLabel(
            row1,
            text=f"📅 {self._apt.get('date', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        ).pack(side="right", padx=10, pady=6)

        # Телефоны (кликабельные)
        PhoneWidget(self, self._apt).pack(fill="x", pady=(0, 4))

        # Адрес + карта
        address = self._apt.get("address", "Не указан")
        addr_row = ctk.CTkFrame(self, fg_color="#252525", corner_radius=6)
        addr_row.pack(fill="x", pady=(0, 4))

        addr_color = "#e0e0e0" if address != "Не указан" else "#666666"
        ctk.CTkLabel(
            addr_row,
            text=f"📍 {address}",
            font=ctk.CTkFont(size=12),
            text_color=addr_color,
            wraplength=300,
            justify="left"
        ).pack(side="left", padx=10, pady=5)

        if show_map:
            ctk.CTkButton(
                addr_row,
                text="🗺️ Карта",
                width=85, height=28,
                command=self._open_map,
                fg_color="#1565c0", hover_color="#1976d2",
                font=ctk.CTkFont(size=11), corner_radius=6
            ).pack(side="right", padx=5, pady=3)

        # Группа + ссылка ВК
        group_row = ctk.CTkFrame(self, fg_color="#252525", corner_radius=6)
        group_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            group_row,
            text=f"👥 {self._apt.get('group', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa"
        ).pack(side="left", padx=10, pady=4)

        ctk.CTkButton(
            group_row,
            text="🔗 ВКонтакте",
            width=110, height=26,
            command=lambda: webbrowser.open(self._apt.get("url", "")),
            fg_color="#4a4a8a", hover_color="#5a5a9a",
            font=ctk.CTkFont(size=11), corner_radius=6
        ).pack(side="right", padx=5, pady=3)

    def _open_map(self):
        address = self._apt.get("address", "")
        if address and address != "Не указан":
            encoded = requests.utils.quote(address)
            webbrowser.open(f"https://yandex.ru/maps/?text={encoded}")
        else:
            messagebox.showwarning(
                "Адрес не найден",
                "Адрес не определён автоматически.\n"
                "Попробуйте открыть оригинальный пост в ВК."
            )