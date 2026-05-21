import customtkinter as ctk
from tkinter import messagebox
import threading
import webbrowser


class SettingsTab(ctk.CTkFrame):
    """Вкладка настроек"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.group_entries = []

        self.configure(fg_color="#1a1a1a")
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        """Построение интерфейса настроек"""
        # Прокручиваемая область
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # ======== VK НАСТРОЙКИ ========
        self._section_header(
            self.scroll,
            "🔑 ВКонтакте API",
            "#1a3a5c"
        )

        vk_frame = ctk.CTkFrame(self.scroll, fg_color="#252525", corner_radius=8)
        vk_frame.pack(fill="x", pady=(0, 15), padx=5)

        # VK Token
        ctk.CTkLabel(
            vk_frame,
            text="VK Access Token:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#4fc3f7"
        ).pack(anchor="w", padx=15, pady=(15, 3))

        ctk.CTkLabel(
            vk_frame,
            text="Получить: vk.com/dev → Мои приложения → Standalone → получить токен",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        ).pack(anchor="w", padx=15)

        self.vk_token_entry = ctk.CTkEntry(
            vk_frame,
            placeholder_text="vk1.a.xxxxxxxxxxxx",
            height=38,
            font=ctk.CTkFont(size=12),
            show="*"
        )
        self.vk_token_entry.pack(fill="x", padx=15, pady=(5, 5))

        show_vk_btn = ctk.CTkButton(
            vk_frame,
            text="👁️ Показать токен",
            width=150,
            height=28,
            command=self._toggle_vk_token,
            fg_color="#333333",
            hover_color="#444444",
            font=ctk.CTkFont(size=11)
        )
        show_vk_btn.pack(anchor="w", padx=15, pady=(0, 5))
        self.show_vk_btn = show_vk_btn
        self.vk_token_visible = False

        token_help_frame = ctk.CTkFrame(vk_frame, fg_color="#1a1a1a", corner_radius=6)
        token_help_frame.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkLabel(
            token_help_frame,
            text="Выберите способ получения токена:",
            font=ctk.CTkFont(size=12),
            text_color="#aaaaaa"
        ).pack(anchor="w", padx=8, pady=(8, 3))

        # Кнопки вариантов
        btn_row1 = ctk.CTkFrame(token_help_frame, fg_color="transparent")
        btn_row1.pack(fill="x", padx=8, pady=(0, 5))

        ctk.CTkButton(
            btn_row1,
            text="📱 Kate Mobile",
            width=150,
            height=32,
            command=lambda: webbrowser.open(
                "https://oauth.vk.com/authorize?"
                "client_id=2685278"
                "&display=page"
                "&redirect_uri=https://oauth.vk.com/blank.html"
                "&scope=groups,wall,photos,offline"
                "&response_type=token"
                "&v=5.131"
            ),
            fg_color="#1565c0",
            hover_color="#1976d2",
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_row1,
            text="🍎 VK iPhone",
            width=130,
            height=32,
            command=lambda: webbrowser.open(
                "https://oauth.vk.com/authorize?"
                "client_id=3140623"
                "&display=page"
                "&redirect_uri=https://oauth.vk.com/blank.html"
                "&scope=groups,wall,photos,offline"
                "&response_type=token"
                "&v=5.131"
            ),
            fg_color="#1a5c1a",
            hover_color="#1e6c1e",
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_row1,
            text="🤖 VK Android",
            width=140,
            height=32,
            command=lambda: webbrowser.open(
                "https://oauth.vk.com/authorize?"
                "client_id=2274003"
                "&display=page"
                "&redirect_uri=https://oauth.vk.com/blank.html"
                "&scope=groups,wall,photos,offline"
                "&response_type=token"
                "&v=5.131"
            ),
            fg_color="#7a3a00",
            hover_color="#8a4a00",
            font=ctk.CTkFont(size=11)
        ).pack(side="left")

        # Инструкция
        ctk.CTkLabel(
            token_help_frame,
            text="После перехода по ссылке → Разрешить → "
                "скопируйте токен из адресной строки\n"
                "(всё после access_token= и до &expires_in)",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            justify="left"
        ).pack(anchor="w", padx=8, pady=(0, 8))

        # ======== ГРУППЫ ВК ========
        self._section_header(
            self.scroll,
            "👥 Группы ВКонтакте для парсинга",
            "#1a3a1a"
        )

        self.groups_frame = ctk.CTkFrame(
            self.scroll,
            fg_color="#252525",
            corner_radius=8
        )
        self.groups_frame.pack(fill="x", pady=(0, 5), padx=5)

        ctk.CTkLabel(
            self.groups_frame,
            text="Добавляйте ссылки на группы ВК с объявлениями об аренде:",
            font=ctk.CTkFont(size=12),
            text_color="#aaaaaa"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.groups_list_frame = ctk.CTkFrame(
            self.groups_frame,
            fg_color="transparent"
        )
        self.groups_list_frame.pack(fill="x", padx=10)

        # Кнопка добавить группу
        ctk.CTkButton(
            self.groups_frame,
            text="➕ Добавить группу",
            width=170,
            height=35,
            command=self._add_group_entry,
            fg_color="#2e7d32",
            hover_color="#388e3c",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=15, pady=10)

        # ======== GITHUB НАСТРОЙКИ ========
        self._section_header(
            self.scroll,
            "🐙 GitHub (синхронизация данных)",
            "#2a1a3a"
        )

        gh_frame = ctk.CTkFrame(self.scroll, fg_color="#252525", corner_radius=8)
        gh_frame.pack(fill="x", pady=(0, 15), padx=5)

        # GitHub Token
        ctk.CTkLabel(
            gh_frame,
            text="GitHub Personal Access Token:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ce93d8"
        ).pack(anchor="w", padx=15, pady=(15, 3))

        ctk.CTkLabel(
            gh_frame,
            text="github.com → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        ).pack(anchor="w", padx=15)

        self.gh_token_entry = ctk.CTkEntry(
            gh_frame,
            placeholder_text="ghp_xxxxxxxxxxxx",
            height=38,
            font=ctk.CTkFont(size=12),
            show="*"
        )
        self.gh_token_entry.pack(fill="x", padx=15, pady=(5, 5))

        self.show_gh_btn = ctk.CTkButton(
            gh_frame,
            text="👁️ Показать токен",
            width=150,
            height=28,
            command=self._toggle_gh_token,
            fg_color="#333333",
            hover_color="#444444",
            font=ctk.CTkFont(size=11)
        )
        self.show_gh_btn.pack(anchor="w", padx=15, pady=(0, 5))
        self.gh_token_visible = False

        # GitHub Username
        ctk.CTkLabel(
            gh_frame,
            text="GitHub Username:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ce93d8"
        ).pack(anchor="w", padx=15, pady=(10, 3))

        self.gh_username_entry = ctk.CTkEntry(
            gh_frame,
            placeholder_text="ваш-логин-github",
            height=38,
            font=ctk.CTkFont(size=12)
        )
        self.gh_username_entry.pack(fill="x", padx=15, pady=(0, 5))

        # GitHub Repo
        ctk.CTkLabel(
            gh_frame,
            text="Название репозитория:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ce93d8"
        ).pack(anchor="w", padx=15, pady=(10, 3))

        ctk.CTkLabel(
            gh_frame,
            text="Введите название нового или существующего приватного репозитория",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        ).pack(anchor="w", padx=15)

        self.gh_repo_entry = ctk.CTkEntry(
            gh_frame,
            placeholder_text="realtor-data",
            height=38,
            font=ctk.CTkFont(size=12)
        )
        self.gh_repo_entry.pack(fill="x", padx=15, pady=(5, 5))

        # Кнопки GitHub
        gh_btn_frame = ctk.CTkFrame(gh_frame, fg_color="transparent")
        gh_btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        ctk.CTkButton(
            gh_btn_frame,
            text="🔗 Открыть GitHub",
            width=150,
            height=32,
            command=lambda: webbrowser.open("https://github.com"),
            fg_color="#333333",
            hover_color="#444444",
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            gh_btn_frame,
            text="🔧 Создать репозиторий",
            width=180,
            height=32,
            command=self._create_repo,
            fg_color="#6a3a8a",
            hover_color="#7a4a9a",
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            gh_btn_frame,
            text="🔄 Проверить соединение",
            width=190,
            height=32,
            command=self._test_github,
            fg_color="#1a5a3a",
            hover_color="#1a6a4a",
            font=ctk.CTkFont(size=11)
        ).pack(side="left")

        # ======== КНОПКА СОХРАНЕНИЯ ========
        save_frame = ctk.CTkFrame(self.scroll, fg_color="#252525", corner_radius=8)
        save_frame.pack(fill="x", pady=(10, 15), padx=5)

        self.save_status_label = ctk.CTkLabel(
            save_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#81c784"
        )
        self.save_status_label.pack(side="left", padx=15, pady=10)

        ctk.CTkButton(
            save_frame,
            text="💾 Сохранить все настройки",
            width=220,
            height=45,
            command=self._save_settings,
            fg_color="#c94000",
            hover_color="#e65100",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(side="right", padx=15, pady=10)

    def _section_header(self, parent, title: str, color: str):
        """Заголовок секции"""
        frame = ctk.CTkFrame(parent, fg_color=color, corner_radius=8, height=45)
        frame.pack(fill="x", pady=(10, 0), padx=5)
        frame.pack_propagate(False)

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white"
        ).pack(side="left", padx=15, pady=10)

    def _add_group_entry(self, url: str = ""):
        """Добавление поля для группы"""
        row = ctk.CTkFrame(self.groups_list_frame, fg_color="transparent")
        row.pack(fill="x", pady=3)

        entry = ctk.CTkEntry(
            row,
            placeholder_text="https://vk.com/group_name",
            height=35,
            font=ctk.CTkFont(size=12)
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        if url:
            entry.insert(0, url)

        def remove():
            self.group_entries.remove(entry)
            row.destroy()

        ctk.CTkButton(
            row,
            text="🗑️",
            width=35,
            height=35,
            command=remove,
            fg_color="#c62828",
            hover_color="#d32f2f",
            font=ctk.CTkFont(size=14)
        ).pack(side="right")

        self.group_entries.append(entry)

    def _toggle_vk_token(self):
        """Показать/скрыть VK токен"""
        self.vk_token_visible = not self.vk_token_visible
        if self.vk_token_visible:
            self.vk_token_entry.configure(show="")
            self.show_vk_btn.configure(text="🔒 Скрыть токен")
        else:
            self.vk_token_entry.configure(show="*")
            self.show_vk_btn.configure(text="👁️ Показать токен")

    def _toggle_gh_token(self):
        """Показать/скрыть GitHub токен"""
        self.gh_token_visible = not self.gh_token_visible
        if self.gh_token_visible:
            self.gh_token_entry.configure(show="")
            self.show_gh_btn.configure(text="🔒 Скрыть токен")
        else:
            self.gh_token_entry.configure(show="*")
            self.show_gh_btn.configure(text="👁️ Показать токен")

    def _load_settings(self):
        """Загрузка настроек в поля"""
        config = self.app.config

        if config.get("vk_token"):
            self.vk_token_entry.insert(0, config["vk_token"])

        if config.get("github_token"):
            self.gh_token_entry.insert(0, config["github_token"])

        if config.get("github_username"):
            self.gh_username_entry.insert(0, config["github_username"])

        if config.get("github_repo"):
            self.gh_repo_entry.insert(0, config["github_repo"])

        for group_url in config.get("vk_groups", []):
            self._add_group_entry(group_url)

    def _save_settings(self):
        """Сохранение настроек"""
        config = self.app.config

        config["vk_token"] = self.vk_token_entry.get().strip()
        config["github_token"] = self.gh_token_entry.get().strip()
        config["github_username"] = self.gh_username_entry.get().strip()
        config["github_repo"] = self.gh_repo_entry.get().strip()

        # Группы
        groups = []
        for entry in self.group_entries:
            url = entry.get().strip()
            if url:
                groups.append(url)
        config["vk_groups"] = groups

        # Переподключаем GitHub
        self.app.reconnect_github()

        from config import save_config
        if save_config(config):
            self.save_status_label.configure(
                text="✅ Настройки сохранены!",
                text_color="#81c784"
            )
            self.after(
                3000,
                lambda: self.save_status_label.configure(text="")
            )
        else:
            self.save_status_label.configure(
                text="❌ Ошибка сохранения!",
                text_color="#ef9a9a"
            )

    def _test_github(self):
        """Проверка GitHub подключения"""
        self.save_status_label.configure(
            text="🔄 Проверка GitHub...",
            text_color="#4fc3f7"
        )

        def test():
            connected = self.app.github_sync and self.app.github_sync.is_connected()
            if connected:
                self.after(
                    0,
                    lambda: self.save_status_label.configure(
                        text="✅ GitHub подключён!",
                        text_color="#81c784"
                    )
                )
            else:
                self.after(
                    0,
                    lambda: self.save_status_label.configure(
                        text="❌ GitHub не подключён! Сохраните настройки и попробуйте снова.",
                        text_color="#ef9a9a"
                    )
                )

        threading.Thread(target=test, daemon=True).start()

    def _create_repo(self):
        """Создание репозитория GitHub"""
        if not self.app.github_sync:
            messagebox.showerror(
                "Ошибка",
                "Сначала сохраните настройки GitHub!"
            )
            return

        def create():
            success = self.app.github_sync.create_repo_if_not_exists()
            if success:
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Успех",
                        "Репозиторий создан или уже существует!"
                    )
                )
            else:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Ошибка",
                        "Не удалось создать репозиторий.\n"
                        "Проверьте токен и имя пользователя."
                    )
                )

        threading.Thread(target=create, daemon=True).start()