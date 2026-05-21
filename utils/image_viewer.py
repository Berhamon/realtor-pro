import customtkinter as ctk
from PIL import Image, ImageTk
import tkinter as tk
from utils.image_cache import image_cache
from utils.async_helper import async_helper


class ImageViewer(ctk.CTkToplevel):
    """
    Полноэкранный просмотрщик фотографий.
    Поддерживает: зум, перетаскивание, листание, клавиши.
    """

    MIN_ZOOM = 0.1
    MAX_ZOOM = 8.0
    ZOOM_STEP = 0.15

    def __init__(self, parent, urls: list, start_index: int = 0):
        super().__init__(parent)

        self._urls = urls
        self._current_index = start_index
        self._zoom = 1.0
        self._pan_x = 0
        self._pan_y = 0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        self._loaded_images: dict = {}   # url -> PIL.Image (оригинал)
        self._tk_image = None
        self._destroyed = False

        self._setup_window()
        self._build_ui()
        self._bind_keys()
        self._load_current()

    def _setup_window(self):
        """Настройка окна"""
        self.title("📷 Просмотр фотографий")
        self.configure(fg_color="#0a0a0a")

        # Полноэкранный режим
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = min(1400, screen_w - 100)
        h = min(900, screen_h - 100)
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.minsize(800, 600)
        self.resizable(True, True)

        # Поверх других окон
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build_ui(self):
        """Построение интерфейса"""
        # ── Верхняя панель ─────────────────────────────
        top_bar = ctk.CTkFrame(self, fg_color="#111111", height=50)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        # Счётчик фото
        self.title_label = ctk.CTkLabel(
            top_bar,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        self.title_label.pack(side="left", padx=15, pady=10)

        # Кнопка закрыть
        ctk.CTkButton(
            top_bar,
            text="✕ Закрыть",
            width=100,
            height=34,
            command=self._close,
            fg_color="#5a1a1a",
            hover_color="#7a2a2a",
            font=ctk.CTkFont(size=13),
            corner_radius=8
        ).pack(side="right", padx=10, pady=8)

        # Кнопка полный экран
        self.fullscreen_btn = ctk.CTkButton(
            top_bar,
            text="⛶ Полный экран",
            width=140,
            height=34,
            command=self._toggle_fullscreen,
            fg_color="#1a3a5c",
            hover_color="#1e4a6c",
            font=ctk.CTkFont(size=12),
            corner_radius=8
        )
        self.fullscreen_btn.pack(side="right", padx=5, pady=8)

        # Зум инфо
        self.zoom_label = ctk.CTkLabel(
            top_bar,
            text="100%",
            font=ctk.CTkFont(size=13),
            text_color="#aaaaaa",
            width=60
        )
        self.zoom_label.pack(side="right", padx=5)

        # Кнопки зума
        ctk.CTkButton(
            top_bar,
            text="🔍+",
            width=45,
            height=34,
            command=self._zoom_in,
            fg_color="#2a2a2a",
            hover_color="#3a3a3a",
            font=ctk.CTkFont(size=14),
            corner_radius=8
        ).pack(side="right", padx=2, pady=8)

        ctk.CTkButton(
            top_bar,
            text="🔍-",
            width=45,
            height=34,
            command=self._zoom_out,
            fg_color="#2a2a2a",
            hover_color="#3a3a3a",
            font=ctk.CTkFont(size=14),
            corner_radius=8
        ).pack(side="right", padx=2, pady=8)

        ctk.CTkButton(
            top_bar,
            text="⟲ Сброс",
            width=80,
            height=34,
            command=self._reset_view,
            fg_color="#2a2a2a",
            hover_color="#3a3a3a",
            font=ctk.CTkFont(size=12),
            corner_radius=8
        ).pack(side="right", padx=2, pady=8)

        # ── Основная зона ──────────────────────────────
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.pack(fill="both", expand=True)

        # Кнопка "назад"
        self.prev_btn = ctk.CTkButton(
            main_area,
            text="❮",
            width=50,
            command=self._prev,
            fg_color="#1a1a1a",
            hover_color="#2a2a2a",
            font=ctk.CTkFont(size=28),
            corner_radius=0,
            border_width=0
        )
        self.prev_btn.pack(side="left", fill="y")

        # Canvas для фото
        self.canvas = tk.Canvas(
            main_area,
            bg="#0a0a0a",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        # Кнопка "вперёд"
        self.next_btn = ctk.CTkButton(
            main_area,
            text="❯",
            width=50,
            command=self._next,
            fg_color="#1a1a1a",
            hover_color="#2a2a2a",
            font=ctk.CTkFont(size=28),
            corner_radius=0,
            border_width=0
        )
        self.next_btn.pack(side="right", fill="y")

        # Загрузочный оверлей
        self.loading_label = ctk.CTkLabel(
            self.canvas,
            text="⏳ Загрузка...",
            font=ctk.CTkFont(size=18),
            text_color="#555555",
            fg_color="transparent"
        )

        # ── Нижняя панель (миниатюры) ──────────────────
        self.thumb_bar = ctk.CTkFrame(self, fg_color="#111111", height=80)
        self.thumb_bar.pack(fill="x", side="bottom")

        self.thumb_scroll = ctk.CTkScrollableFrame(
            self.thumb_bar,
            orientation="horizontal",
            fg_color="transparent",
            height=70
        )
        self.thumb_scroll.pack(fill="x", padx=5, pady=5)

        self._build_thumbnails()

        # Привязка событий мыши на canvas
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

    def _build_thumbnails(self):
        """Построение панели миниатюр"""
        self._thumb_buttons = []

        for i, url in enumerate(self._urls):
            btn = ctk.CTkButton(
                self.thumb_scroll,
                text=f"📷 {i+1}",
                width=65,
                height=55,
                command=lambda idx=i: self._goto(idx),
                fg_color="#2a2a2a",
                hover_color="#3a3a3a",
                font=ctk.CTkFont(size=11),
                corner_radius=6
            )
            btn.pack(side="left", padx=3, pady=5)
            self._thumb_buttons.append(btn)

            # Загружаем миниатюру асинхронно
            async_helper.run_coroutine(
                image_cache.load_image_async(
                    url=url,
                    size=(60, 50),
                    callback=lambda img, u, b=btn: self._set_thumb(img, u, b),
                    widget_ref=self
                )
            )

    def _set_thumb(self, img, url, btn):
        """Установка миниатюры"""
        if self._destroyed or img is None:
            return
        try:
            tk_img = ImageTk.PhotoImage(img)
            btn.configure(image=tk_img, text="")
            btn.image = tk_img  # Сохраняем ссылку
        except Exception:
            pass

    def _update_thumb_highlight(self):
        """Подсветка активной миниатюры"""
        for i, btn in enumerate(self._thumb_buttons):
            if i == self._current_index:
                btn.configure(fg_color="#1565c0", border_width=2, border_color="#4fc3f7")
            else:
                btn.configure(fg_color="#2a2a2a", border_width=0)

    # ── Загрузка фото ──────────────────────────────────

    def _load_current(self):
        """Загрузка текущего фото"""
        if not self._urls:
            return

        url = self._urls[self._current_index]
        self._update_title()
        self._update_thumb_highlight()

        # Если уже загружено — показываем
        if url in self._loaded_images:
            self._reset_view()
            return

        # Показываем загрузку
        self._show_loading(True)

        # Загружаем оригинал (большой размер)
        async_helper.run_coroutine(
            self._load_original_async(url)
        )

    async def _load_original_async(self, url: str):
        """Загрузка оригинального (полного) изображения"""
        import aiohttp
        from io import BytesIO

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        img = Image.open(BytesIO(data))
                        img = img.convert("RGB")
                        self._loaded_images[url] = img

                        if not self._destroyed:
                            self.after(0, lambda: self._on_image_ready(url))
        except Exception as e:
            if not self._destroyed:
                self.after(0, lambda: self._show_error(str(e)))

    def _on_image_ready(self, url: str):
        """Фото загружено — отображаем"""
        if self._destroyed:
            return

        # Убеждаемся что это текущее фото
        if self._urls[self._current_index] == url:
            self._show_loading(False)
            self._reset_view()

    def _show_loading(self, show: bool):
        """Показать/скрыть индикатор загрузки"""
        if self._destroyed:
            return
        if show:
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2 or 400,
                self.canvas.winfo_height() // 2 or 300,
                text="⏳ Загрузка...",
                font=("Arial", 20),
                fill="#555555",
                tags="loading"
            )
        else:
            self.canvas.delete("loading")

    def _show_error(self, msg: str):
        """Показать ошибку"""
        if self._destroyed:
            return
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2 or 400,
            self.canvas.winfo_height() // 2 or 300,
            text=f"❌ Ошибка загрузки\n{msg}",
            font=("Arial", 16),
            fill="#ef5350",
            justify="center"
        )

    # ── Отрисовка фото ─────────────────────────────────

    def _draw_image(self):
        """Отрисовка изображения с учётом зума и пана"""
        if self._destroyed:
            return

        url = self._urls[self._current_index]
        original = self._loaded_images.get(url)
        if original is None:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 2 or canvas_h < 2:
            return

        img_w, img_h = original.size

        # Вычисляем размер с учётом зума
        display_w = int(img_w * self._zoom)
        display_h = int(img_h * self._zoom)

        # Позиция (центр + пан)
        pos_x = canvas_w // 2 + self._pan_x
        pos_y = canvas_h // 2 + self._pan_y

        # Ресайз изображения
        try:
            resized = original.resize(
                (max(1, display_w), max(1, display_h)),
                Image.LANCZOS if display_w < 2000 else Image.NEAREST
            )
            self._tk_image = ImageTk.PhotoImage(resized)
        except Exception as e:
            print(f"Ошибка ресайза: {e}")
            return

        self.canvas.delete("photo")
        self.canvas.create_image(
            pos_x, pos_y,
            image=self._tk_image,
            anchor="center",
            tags="photo"
        )

        # Инфо о размере
        self.canvas.delete("info")
        self.canvas.create_text(
            10, canvas_h - 10,
            text=f"{img_w}×{img_h}px | {display_w}×{display_h}px",
            font=("Arial", 10),
            fill="#444444",
            anchor="sw",
            tags="info"
        )

        self.zoom_label.configure(text=f"{int(self._zoom * 100)}%")

    def _fit_to_window(self):
        """Подгонка изображения под размер окна"""
        url = self._urls[self._current_index]
        original = self._loaded_images.get(url)
        if original is None:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 2 or canvas_h < 2:
            self.after(100, self._fit_to_window)
            return

        img_w, img_h = original.size
        scale_x = canvas_w / img_w
        scale_y = canvas_h / img_h
        self._zoom = min(scale_x, scale_y) * 0.95

        self._zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom))
        self._draw_image()

    def _reset_view(self):
        """Сброс вида (fit to window)"""
        self._pan_x = 0
        self._pan_y = 0
        self.after(50, self._fit_to_window)

    # ── Зум ────────────────────────────────────────────

    def _zoom_in(self):
        self._zoom = min(self.MAX_ZOOM, self._zoom + self.ZOOM_STEP)
        self._draw_image()

    def _zoom_out(self):
        self._zoom = max(self.MIN_ZOOM, self._zoom - self.ZOOM_STEP)
        self._draw_image()

    def _zoom_at(self, x: int, y: int, delta: float):
        """Зум с привязкой к позиции курсора"""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # Позиция курсора относительно центра
        cx = x - canvas_w // 2
        cy = y - canvas_h // 2

        old_zoom = self._zoom
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, old_zoom * (1 + delta)))

        # Корректируем пан чтобы зум был под курсором
        ratio = new_zoom / old_zoom
        self._pan_x = cx + (self._pan_x - cx) * ratio
        self._pan_y = cy + (self._pan_y - cy) * ratio

        self._zoom = new_zoom
        self._draw_image()

    # ── События мыши ───────────────────────────────────

    def _on_mousewheel(self, event):
        """Зум колёсиком"""
        if event.num == 4:  # Linux прокрутка вверх
            delta = self.ZOOM_STEP
        elif event.num == 5:  # Linux прокрутка вниз
            delta = -self.ZOOM_STEP
        else:  # Windows/Mac
            delta = self.ZOOM_STEP if event.delta > 0 else -self.ZOOM_STEP

        self._zoom_at(event.x, event.y, delta)

    def _on_drag_start(self, event):
        """Начало перетаскивания"""
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._is_dragging = False
        self.canvas.configure(cursor="fleur")

    def _on_drag(self, event):
        """Перетаскивание"""
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y

        if abs(dx) > 3 or abs(dy) > 3:
            self._is_dragging = True

        self._pan_x += event.x - self._drag_start_x
        self._pan_y += event.y - self._drag_start_y
        self._drag_start_x = event.x
        self._drag_start_y = event.y

        self._draw_image()

    def _on_drag_end(self, event):
        """Конец перетаскивания"""
        self.canvas.configure(cursor="crosshair")
        self._is_dragging = False

    def _on_double_click(self, event):
        """Двойной клик — сброс зума"""
        if not self._is_dragging:
            self._reset_view()

    def _on_canvas_resize(self, event):
        """Изменение размера окна"""
        self.after(50, self._draw_image)

    # ── Навигация ──────────────────────────────────────

    def _prev(self):
        if len(self._urls) > 1:
            self._current_index = (self._current_index - 1) % len(self._urls)
            self._load_current()

    def _next(self):
        if len(self._urls) > 1:
            self._current_index = (self._current_index + 1) % len(self._urls)
            self._load_current()

    def _goto(self, index: int):
        self._current_index = index
        self._load_current()

    def _update_title(self):
        """Обновление заголовка"""
        total = len(self._urls)
        current = self._current_index + 1
        self.title_label.configure(
            text=f"📷 Фото {current} из {total}"
        )

        # Скрываем кнопки если одно фото
        if total <= 1:
            self.prev_btn.pack_forget()
            self.next_btn.pack_forget()

    # ── Управление с клавиатуры ────────────────────────

    def _bind_keys(self):
        self.bind("<Escape>", lambda e: self._close())
        self.bind("<Left>", lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Up>", lambda e: self._zoom_in())
        self.bind("<Down>", lambda e: self._zoom_out())
        self.bind("<r>", lambda e: self._reset_view())
        self.bind("<f>", lambda e: self._toggle_fullscreen())
        self.bind("<plus>", lambda e: self._zoom_in())
        self.bind("<minus>", lambda e: self._zoom_out())
        self.bind("<KP_Add>", lambda e: self._zoom_in())
        self.bind("<KP_Subtract>", lambda e: self._zoom_out())

    def _toggle_fullscreen(self):
        """Переключение полного экрана"""
        current = self.attributes("-fullscreen")
        self.attributes("-fullscreen", not current)
        if not current:
            self.fullscreen_btn.configure(text="⛶ Оконный режим")
        else:
            self.fullscreen_btn.configure(text="⛶ Полный экран")

    def _close(self):
        self._destroyed = True
        self.grab_release()
        self.destroy()