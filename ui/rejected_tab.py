import customtkinter as ctk

from utils import async_helper
from ui.components import PhotoGallery, ExpandableText, ApartmentInfoBar


class RejectedCard(ctk.CTkFrame):
    """Карточка отклонённой квартиры"""

    def __init__(self, parent, apartment: dict, on_restore=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.apartment = apartment
        self.on_restore = on_restore

        self.configure(
            fg_color="#2a1a1a", corner_radius=12,
            border_width=1, border_color="#5a2d2d"
        )
        self._build_ui()

    def _build_ui(self):
        # ── Заголовок ──────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="#3a1b1b", corner_radius=8)
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="❌ ОТКЛОНЕНО",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ef9a9a"
        ).pack(side="left", padx=8, pady=5)

        ctk.CTkLabel(
            header,
            text=f"📍 {self.apartment.get('address', 'Адрес не указан')}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#cccccc"
        ).pack(side="left", padx=8, pady=5)

        ctk.CTkLabel(
            header,
            text=f"💰 {self.apartment.get('price', '')}",
            font=ctk.CTkFont(size=13),
            text_color="#ef9a9a"
        ).pack(side="right", padx=10, pady=5)

        # ── Основной контент ───────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=4)

        # Галерея (кликабельная)
        self.gallery = PhotoGallery(
            content, width=220, height=175,
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

        # Разворачиваемое описание
        ExpandableText(
            right,
            text=self.apartment.get("text", "Описание отсутствует"),
            accent_color="#ef9a9a"
        ).pack(fill="x", pady=(4, 0))

        # ── Кнопки ─────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        actions.pack(fill="x", padx=10, pady=(6, 10))

        ctk.CTkButton(
            actions,
            text="↩️ Вернуть в поиск",
            width=160, height=32,
            command=lambda: self._restore("search"),
            fg_color="#444444", hover_color="#555555",
            font=ctk.CTkFont(size=12), corner_radius=8
        ).pack(side="left", padx=8, pady=6)

        ctk.CTkButton(
            actions,
            text="✅ Одобрить",
            width=120, height=32,
            command=lambda: self._restore("approved"),
            fg_color="#1a5c2a", hover_color="#2a6c3a",
            font=ctk.CTkFont(size=12), corner_radius=8
        ).pack(side="left", padx=(0, 5), pady=6)

        ctk.CTkLabel(
            actions,
            text=f"📅 {self.apartment.get('date', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        ).pack(side="right", padx=10, pady=6)

    def _restore(self, status: str):
        self.apartment["status"] = status
        if self.on_restore:
            self.on_restore(self.apartment)


class RejectedTab(ctk.CTkFrame):
    """Вкладка отклонённых квартир"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.cards = []
        self._build_ui()

    def _build_ui(self):
        self.configure(fg_color="#1a1a1a")

        header = ctk.CTkFrame(self, fg_color="#3a1b1b", height=58)
        header.pack(fill="x", padx=10, pady=(10, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="❌ Отклонённые квартиры",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ef9a9a"
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
        for widget in self.scroll_frame.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass
        self.cards.clear()

        rejected = [
            a for a in self.app.data.get("apartments", [])
            if a.get("status") == "rejected"
        ]
        self.count_label.configure(text=f"{len(rejected)} квартир")

        if not rejected:
            ctk.CTkLabel(
                self.scroll_frame,
                text=(
                    "❌ Отклонённых квартир пока нет.\n\n"
                    "Отклонённые объявления появятся здесь."
                ),
                font=ctk.CTkFont(size=14),
                text_color="#555555",
                justify="center"
            ).pack(expand=True, pady=60)
            return

        for apt in rejected:
            card = RejectedCard(
                self.scroll_frame, apt,
                on_restore=self._handle_restore
            )
            card.pack(fill="x", pady=4, padx=5)
            self.cards.append(card)

    def _handle_restore(self, apartment: dict):
        for apt in self.app.data.get("apartments", []):
            if apt["id"] == apartment["id"]:
                apt["status"] = apartment["status"]
                break
        async_helper.run_in_executor(self.app.sync_data)
        self.after(0, self.app.refresh_all_tabs)