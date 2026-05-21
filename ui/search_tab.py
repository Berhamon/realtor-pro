import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
import requests

from utils import async_helper, image_cache, Debouncer
from ui.components import PhotoGallery, ExpandableText, ApartmentInfoBar


class ApartmentCard(ctk.CTkFrame):
    """Карточка квартиры для вкладки Поиск"""

    def __init__(self, parent, apartment: dict,
                 on_approve=None, on_reject=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.apartment = apartment
        self.on_approve = on_approve
        self.on_reject = on_reject

        self.configure(
            fg_color="#2b2b2b", corner_radius=12,
            border_width=1, border_color="#3a3a3a"
        )
        self._build_ui()

    def _build_ui(self):
        # ── Заголовок ──────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="#1d2a3a", corner_radius=8)
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text=f"📍 {self.apartment.get('address', 'Адрес не указан')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4fc3f7"
        ).pack(side="left", padx=10, pady=7)

        ctk.CTkLabel(
            header,
            text=f"💰 {self.apartment.get('price', 'Цена не указана')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#81c784"
        ).pack(side="right", padx=10, pady=7)

        # ── Основной контент ───────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=4)

        # Галерея (кликабельная)
        self.gallery = PhotoGallery(
            content, width=290, height=205,
            fg_color="#1e1e1e"
        )
        self.gallery.pack(side="left", padx=(0, 10))
        self.gallery.load_photos(self.apartment.get("photos", []))

        # Правая колонка
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        # Мета-информация
        ApartmentInfoBar(
            right,
            self.apartment,
            show_map=True
        ).pack(fill="x")

        # Разворачиваемое описание
        ExpandableText(
            right,
            text=self.apartment.get("text", "Описание отсутствует"),
            accent_color="#4fc3f7"
        ).pack(fill="x", pady=(4, 0))

        # ── Кнопки действий ────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        actions.pack(fill="x", padx=10, pady=(6, 10))

        ctk.CTkButton(
            actions,
            text="❌ Отклонить",
            width=130, height=34,
            command=self._reject,
            fg_color="#7a2020", hover_color="#8a3030",
            font=ctk.CTkFont(size=12), corner_radius=8
        ).pack(side="right", padx=8, pady=6)

        ctk.CTkButton(
            actions,
            text="✅ Одобрить",
            width=130, height=34,
            command=self._approve,
            fg_color="#1a5c2a", hover_color="#2a6c3a",
            font=ctk.CTkFont(size=12), corner_radius=8
        ).pack(side="right", padx=(0, 4), pady=6)

        ctk.CTkLabel(
            actions,
            text=f"📅 {self.apartment.get('date', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        ).pack(side="left", padx=10, pady=6)

    def _approve(self):
        if self.on_approve:
            self.on_approve(self.apartment)

    def _reject(self):
        if self.on_reject:
            self.on_reject(self.apartment)


class VirtualList(ctk.CTkScrollableFrame):
    """Виртуальный список с исправленной очисткой"""

    BATCH_SIZE = 5

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self._apartments: list = []
        self._rendered_cards: list = []
        self._render_index: int = 0
        self._load_more_btn = None
        self._empty_label = None

    def set_apartments(self, apartments: list):
        """Полная очистка и рендер нового списка"""
        # Уничтожаем всё содержимое
        for widget in self.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        self._rendered_cards.clear()
        self._load_more_btn = None
        self._empty_label = None
        self._apartments = apartments
        self._render_index = 0

        if not apartments:
            self._show_empty()
            return

        self.after(10, self._render_batch)

    def _show_empty(self):
        self._empty_label = ctk.CTkLabel(
            self,
            text=(
                "🔍 Объявлений не найдено.\n\n"
                "Нажмите '🔍 Парсить ВК' или измените фильтры."
            ),
            font=ctk.CTkFont(size=14),
            text_color="#555555",
            justify="center"
        )
        self._empty_label.pack(expand=True, pady=60)

    def _render_batch(self):
        start = self._render_index
        end = min(start + self.BATCH_SIZE, len(self._apartments))

        for apt in self._apartments[start:end]:
            try:
                card = ApartmentCard(
                    self, apt,
                    on_approve=self.app.search_tab._approve_apartment,
                    on_reject=self.app.search_tab._reject_apartment
                )
                card.pack(fill="x", pady=5, padx=5)
                self._rendered_cards.append(card)
            except Exception as e:
                print(f"Ошибка рендера: {e}")

        self._render_index = end

        if self._load_more_btn:
            try:
                self._load_more_btn.destroy()
            except Exception:
                pass
            self._load_more_btn = None

        if self._render_index < len(self._apartments):
            remaining = len(self._apartments) - self._render_index
            self._load_more_btn = ctk.CTkButton(
                self,
                text=f"⬇️ Загрузить ещё ({remaining} осталось)",
                height=42,
                command=self._render_batch,
                fg_color="#2a2a2a", hover_color="#3a3a3a",
                font=ctk.CTkFont(size=13), corner_radius=8
            )
            self._load_more_btn.pack(fill="x", padx=20, pady=10)


class SearchTab(ctk.CTkFrame):
    """Вкладка поиска"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self._all_apartments: list = []
        self._filtered: list = []
        self._search_debouncer = Debouncer(delay_ms=350)
        self._price_debouncer = Debouncer(delay_ms=500)
        self._build_ui()

    def _build_ui(self):
        self.configure(fg_color="#1a1a1a")

        # ── Панель управления ──────────────────────────
        controls = ctk.CTkFrame(self, fg_color="#222222", height=75)
        controls.pack(fill="x", padx=10, pady=(10, 5))
        controls.pack_propagate(False)

        self.parse_btn = ctk.CTkButton(
            controls,
            text="🔍 Парсить ВК",
            width=150, height=46,
            command=self._start_parsing,
            fg_color="#1565c0", hover_color="#1976d2",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10
        )
        self.parse_btn.pack(side="left", padx=12, pady=14)

        # Поиск
        search_frame = ctk.CTkFrame(controls, fg_color="transparent")
        search_frame.pack(side="left", fill="y", padx=5)

        ctk.CTkLabel(
            search_frame, text="Поиск:",
            font=ctk.CTkFont(size=11), text_color="#888888"
        ).pack(anchor="w", pady=(8, 0))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="🔎 Адрес, телефон, описание...",
            width=280, height=36,
            font=ctk.CTkFont(size=12), corner_radius=8
        ).pack(pady=(2, 8))

        # Фильтр цены
        price_frame = ctk.CTkFrame(controls, fg_color="transparent")
        price_frame.pack(side="left", fill="y", padx=5)

        ctk.CTkLabel(
            price_frame, text="Макс. цена (₽):",
            font=ctk.CTkFont(size=11), text_color="#888888"
        ).pack(anchor="w", pady=(8, 0))

        self.price_var = tk.StringVar()
        self.price_var.trace_add("write", self._on_price_changed)

        ctk.CTkEntry(
            price_frame,
            textvariable=self.price_var,
            placeholder_text="Без ограничений",
            width=160, height=36,
            font=ctk.CTkFont(size=12), corner_radius=8
        ).pack(pady=(2, 8))

        # Фильтр комнат
        rooms_frame = ctk.CTkFrame(controls, fg_color="transparent")
        rooms_frame.pack(side="left", fill="y", padx=5)

        ctk.CTkLabel(
            rooms_frame, text="Комнаты:",
            font=ctk.CTkFont(size=11), text_color="#888888"
        ).pack(anchor="w", pady=(8, 0))

        self.rooms_var = tk.StringVar(value="Все")
        ctk.CTkOptionMenu(
            rooms_frame,
            variable=self.rooms_var,
            values=["Все", "Студия", "1", "2", "3", "4+"],
            width=120, height=36,
            command=self._on_filter_changed,
            fg_color="#333333", button_color="#444444",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(2, 8))

        self.status_label = ctk.CTkLabel(
            controls, text="Готов",
            font=ctk.CTkFont(size=11), text_color="#888888"
        )
        self.status_label.pack(side="right", padx=15)

        # Прогресс
        self.progress = ctk.CTkProgressBar(
            self, height=3,
            fg_color="#2a2a2a", progress_color="#1565c0"
        )
        self.progress.pack(fill="x", padx=10)
        self.progress.set(0)

        # Статистика
        stats_bar = ctk.CTkFrame(self, fg_color="#1e1e1e", height=30)
        stats_bar.pack(fill="x", padx=10, pady=(3, 0))
        stats_bar.pack_propagate(False)

        self.count_label = ctk.CTkLabel(
            stats_bar, text="Найдено: 0 объявлений",
            font=ctk.CTkFont(size=12), text_color="#888888"
        )
        self.count_label.pack(side="left", padx=10)

        self.filter_info = ctk.CTkLabel(
            stats_bar, text="",
            font=ctk.CTkFont(size=11), text_color="#666666"
        )
        self.filter_info.pack(side="right", padx=10)

        # Виртуальный список
        self.virtual_list = VirtualList(
            self, app=self.app,
            fg_color="#1a1a1a", label_text=""
        )
        self.virtual_list.pack(fill="both", expand=True, padx=10, pady=(3, 10))

    def _on_search_changed(self, *args):
        self._search_debouncer.call(self._apply_filters)

    def _on_price_changed(self, *args):
        self._price_debouncer.call(self._apply_filters)

    def _on_filter_changed(self, *args):
        self._apply_filters()

    def _apply_filters(self):
        def do():
            query = self.search_var.get().lower().strip()
            price_str = self.price_var.get().strip()
            rooms_filter = self.rooms_var.get()

            result = self._all_apartments.copy()

            if query:
                result = [
                    a for a in result
                    if query in (
                        a.get("text", "") +
                        a.get("address", "") +
                        a.get("phone", "") +
                        a.get("group", "")
                    ).lower()
                ]

            if price_str.isdigit():
                max_p = int(price_str)
                result = [
                    a for a in result
                    if self._extract_price(a.get("price", "")) <= max_p
                ]

            if rooms_filter != "Все":
                filtered = []
                for a in result:
                    rooms = a.get("rooms", "").lower()
                    if rooms_filter == "Студия" and "студ" in rooms:
                        filtered.append(a)
                    elif rooms_filter in ["1", "2", "3"] and \
                            f"{rooms_filter} комн" in rooms:
                        filtered.append(a)
                    elif rooms_filter == "4+" and any(
                        f"{n} комн" in rooms for n in ["4", "5", "6"]
                    ):
                        filtered.append(a)
                result = filtered

            self._filtered = result
            self.after(0, self._update_ui)

        async_helper.run_in_executor(do)

    def _update_ui(self):
        total = len(self._filtered)
        self.count_label.configure(text=f"Найдено: {total} объявлений")

        parts = []
        if self.search_var.get().strip():
            parts.append(f"поиск: '{self.search_var.get().strip()}'")
        if self.price_var.get().strip().isdigit():
            parts.append(f"цена ≤ {self.price_var.get()}₽")
        if self.rooms_var.get() != "Все":
            parts.append(f"комнат: {self.rooms_var.get()}")

        self.filter_info.configure(
            text=("Фильтры: " + " | ".join(parts)) if parts else ""
        )
        self.virtual_list.set_apartments(self._filtered)

    def _extract_price(self, s: str) -> int:
        import re
        nums = re.findall(r"\d+", s.replace(" ", ""))
        return int("".join(nums[:2])) if nums else 999_999_999

    def _start_parsing(self):
        config = self.app.config
        if not config.get("vk_token"):
            messagebox.showerror("Ошибка", "VK токен не указан!\nПерейдите в ⚙️ Настройки.")
            return
        if not config.get("vk_groups"):
            messagebox.showerror("Ошибка", "Нет групп ВК!\nПерейдите в ⚙️ Настройки.")
            return

        self.parse_btn.configure(
            state="disabled", text="⏳ Парсинг...", fg_color="#555555"
        )
        self.progress.set(0)
        async_helper.run_in_executor(
            self._parse_worker,
            callback=self._on_parse_done
        )

    def _parse_worker(self):
        try:
            from vk_parser import VKParser
            config = self.app.config
            parser = VKParser(config["vk_token"])
            groups = config["vk_groups"]
            all_posts = []

            for i, url in enumerate(groups):
                progress = (i + 1) / len(groups)
                self.after(0, lambda p=progress, i=i: (
                    self.progress.set(p),
                    self.status_label.configure(
                        text=f"Парсинг {i+1}/{len(groups)}"
                    )
                ))
                all_posts.extend(parser.get_posts(url, count=50))

            existing = {a["id"] for a in self.app.data.get("apartments", [])}
            added = 0
            for post in all_posts:
                if post["id"] not in existing:
                    self.app.data["apartments"].append(post)
                    existing.add(post["id"])
                    added += 1
            return added
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(
                text=f"❌ {e}"
            ))
            return 0

    def _on_parse_done(self, added):
        self.progress.set(1)
        self.parse_btn.configure(
            state="normal", text="🔍 Парсить ВК", fg_color="#1565c0"
        )
        self.status_label.configure(text=f"✅ +{added} новых")
        async_helper.run_in_executor(self.app.sync_data)
        self.after(0, self.app.refresh_all_tabs)

    def refresh(self):
        self._all_apartments = [
            a for a in self.app.data.get("apartments", [])
            if a.get("status") == "search"
        ]
        self._apply_filters()

    def _approve_apartment(self, apartment: dict):
        for apt in self.app.data.get("apartments", []):
            if apt["id"] == apartment["id"]:
                apt["status"] = "approved"
                break
        async_helper.run_in_executor(self.app.sync_data)
        self.after(0, self.app.refresh_all_tabs)

    def _reject_apartment(self, apartment: dict):
        for apt in self.app.data.get("apartments", []):
            if apt["id"] == apartment["id"]:
                apt["status"] = "rejected"
                break
        async_helper.run_in_executor(self.app.sync_data)
        self.after(0, self.app.refresh_all_tabs)