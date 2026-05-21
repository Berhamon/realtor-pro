import customtkinter as ctk
from tkinter import messagebox

from utils import async_helper
from ui.components import PhotoGallery, ExpandableText, ApartmentInfoBar


class ApprovedCard(ctk.CTkFrame):
    """Карточка одобренной квартиры"""

    def __init__(self, parent, apartment: dict, on_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.apartment = apartment
        self.on_change = on_change

        self.configure(
            fg_color="#1a2a1a", corner_radius=12,
            border_width=1, border_color="#2d5a2d"
        )
        self._build_ui()

    def _build_ui(self):
        # ── Заголовок ──────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="#1b3a1b", corner_radius=8)
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="✅ ОДОБРЕНО",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#81c784"
        ).pack(side="left", padx=8, pady=5)

        ctk.CTkLabel(
            header,
            text=f"📍 {self.apartment.get('address', 'Адрес не указан')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4fc3f7"
        ).pack(side="left", padx=8, pady=5)

        ctk.CTkLabel(
            header,
            text=f"💰 {self.apartment.get('price', '')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#81c784"
        ).pack(side="right", padx=10, pady=5)

        # ── Основной контент ───────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=4)

        # Галерея (кликабельная)
        self.gallery = PhotoGallery(
            content, width=260, height=195,
            fg_color="#1e1e1e"
        )
        self.gallery.pack(side="left", padx=(0, 10))
        self.gallery.load_photos(self.apartment.get("photos", []))

        # Правая колонка
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        # Мета-информация
        ApartmentInfoBar(
            right, self.apartment, show_map=True
        ).pack(fill="x")

        # Контакт
        contact_frame = ctk.CTkFrame(right, fg_color="#252525", corner_radius=6)
        contact_frame.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            contact_frame, text="👤 Контакт:",
            font=ctk.CTkFont(size=12), text_color="#aaaaaa"
        ).pack(side="left", padx=8, pady=5)

        self.contact_entry = ctk.CTkEntry(
            contact_frame,
            placeholder_text="Имя владельца/агента...",
            height=30, font=ctk.CTkFont(size=12)
        )
        self.contact_entry.pack(
            side="left", fill="x", expand=True, padx=5, pady=5
        )
        if self.apartment.get("contact_name"):
            self.contact_entry.insert(0, self.apartment["contact_name"])

        # Кнопки управления
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(
            btn_row,
            text="↩️ В поиск",
            width=100, height=30,
            command=lambda: self._change_status("search"),
            fg_color="#444444", hover_color="#555555",
            font=ctk.CTkFont(size=11), corner_radius=6
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_row,
            text="❌ Отклонить",
            width=110, height=30,
            command=lambda: self._change_status("rejected"),
            fg_color="#7a2020", hover_color="#8a3030",
            font=ctk.CTkFont(size=11), corner_radius=6
        ).pack(side="left")

        # Разворачиваемое описание
        ExpandableText(
            right,
            text=self.apartment.get("text", "Описание отсутствует"),
            accent_color="#81c784"
        ).pack(fill="x", pady=(0, 4))

        # ── Заметки ────────────────────────────────────
        notes_header = ctk.CTkFrame(self, fg_color="#1b3a1b", corner_radius=6)
        notes_header.pack(fill="x", padx=10, pady=(4, 0))

        ctk.CTkLabel(
            notes_header,
            text="📝 Мои заметки:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#81c784"
        ).pack(side="left", padx=10, pady=5)

        self.save_btn = ctk.CTkButton(
            notes_header,
            text="💾 Сохранить",
            width=110, height=28,
            command=self._save,
            fg_color="#2e7d32", hover_color="#388e3c",
            font=ctk.CTkFont(size=11), corner_radius=6
        )
        self.save_btn.pack(side="right", padx=8, pady=4)

        self.notes_box = ctk.CTkTextbox(
            self, height=90,
            font=ctk.CTkFont(size=12),
            fg_color="#1e1e1e", corner_radius=6
        )
        self.notes_box.pack(
            fill="x", padx=10, pady=(0, 10)
        )
        if self.apartment.get("notes"):
            self.notes_box.insert("1.0", self.apartment["notes"])

    def _save(self):
        self.apartment["notes"] = self.notes_box.get("1.0", "end-1c")
        self.apartment["contact_name"] = self.contact_entry.get()
        if self.on_change:
            self.on_change(self.apartment, "save")
        self.save_btn.configure(text="✅ Сохранено!")
        self.after(2000, lambda: self.save_btn.configure(text="💾 Сохранить"))

    def _change_status(self, status: str):
        self.apartment["status"] = status
        if self.on_change:
            self.on_change(self.apartment, "status")


class ApprovedTab(ctk.CTkFrame):
    """Вкладка одобренных квартир"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.cards = []
        self._build_ui()

    def _build_ui(self):
        self.configure(fg_color="#1a1a1a")

        header = ctk.CTkFrame(self, fg_color="#1b3a1b", height=58)
        header.pack(fill="x", padx=10, pady=(10, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="✅ Одобренные квартиры",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#81c784"
        ).pack(side="left", padx=15, pady=10)

        self.count_label = ctk.CTkLabel(
            header, text="0 квартир",
            font=ctk.CTkFont(size=13), text_color="#888888"
        )
        self.count_label.pack(side="right", padx=15)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="#1a1a1a", label_text=""
        )
        self.scroll_frame.pack(
            fill="both", expand=True, padx=10, pady=(5, 10)
        )

    def refresh(self):
        """Полная очистка и перерисовка"""
        # Уничтожаем все виджеты
        for widget in self.scroll_frame.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass
        self.cards.clear()

        approved = [
            a for a in self.app.data.get("apartments", [])
            if a.get("status") == "approved"
        ]
        self.count_label.configure(text=f"{len(approved)} квартир")

        if not approved:
            ctk.CTkLabel(
                self.scroll_frame,
                text=(
                    "✅ Одобренных квартир пока нет.\n\n"
                    "Перейдите в '🔍 Поиск' и одобрите квартиры."
                ),
                font=ctk.CTkFont(size=14),
                text_color="#555555",
                justify="center"
            ).pack(expand=True, pady=60)
            return

        for apt in approved:
            card = ApprovedCard(
                self.scroll_frame, apt,
                on_change=self._handle_change
            )
            card.pack(fill="x", pady=5, padx=5)
            self.cards.append(card)

    def _handle_change(self, apartment: dict, action: str):
        for apt in self.app.data.get("apartments", []):
            if apt["id"] == apartment["id"]:
                apt.update(apartment)
                break
        async_helper.run_in_executor(self.app.sync_data)
        if action == "status":
            self.after(0, self.app.refresh_all_tabs)