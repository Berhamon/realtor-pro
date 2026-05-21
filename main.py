import customtkinter as ctk
import threading
from tkinter import messagebox

from config import load_config, save_config
from github_sync import GitHubSync
from utils import async_helper
from ui.search_tab import SearchTab
from ui.approved_tab import ApprovedTab
from ui.rejected_tab import RejectedTab
from ui.settings_tab import SettingsTab

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class RealtorApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.config = load_config()
        self.data = {"apartments": []}
        self.github_sync = None

        self.title("🏠 Риэлтор Профи")
        self.geometry("1280x820")
        self.minsize(1100, 700)

        self._build_ui()
        self.reconnect_github()
        self._load_data_async()

    def _build_ui(self):
        # Шапка
        header = ctk.CTkFrame(self, fg_color="#0d1117", height=65)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="🏠 Риэлтор Профи",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#4fc3f7"
        ).pack(side="left", padx=20, pady=10)

        self.github_status = ctk.CTkLabel(
            header,
            text="⚪ GitHub: не подключён",
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        )
        self.github_status.pack(side="right", padx=20)

        self.sync_btn = ctk.CTkButton(
            header,
            text="🔄 Синхронизировать",
            width=170,
            height=38,
            command=self._manual_sync,
            fg_color="#1a3a5c",
            hover_color="#1e4a6c",
            font=ctk.CTkFont(size=12),
            corner_radius=8
        )
        self.sync_btn.pack(side="right", padx=10, pady=12)

        # Вкладки
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#1a1a1a",
            segmented_button_fg_color="#252525",
            segmented_button_selected_color="#1565c0",
            segmented_button_selected_hover_color="#1976d2",
            segmented_button_unselected_color="#252525",
            segmented_button_unselected_hover_color="#333333",
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabview.add("🔍 Поиск")
        self.tabview.add("✅ Одобренные")
        self.tabview.add("❌ Отклонённые")
        self.tabview.add("⚙️ Настройки")

        self.search_tab = SearchTab(
            self.tabview.tab("🔍 Поиск"), self
        )
        self.search_tab.pack(fill="both", expand=True)

        self.approved_tab = ApprovedTab(
            self.tabview.tab("✅ Одобренные"), self
        )
        self.approved_tab.pack(fill="both", expand=True)

        self.rejected_tab = RejectedTab(
            self.tabview.tab("❌ Отклонённые"), self
        )
        self.rejected_tab.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(
            self.tabview.tab("⚙️ Настройки"), self
        )
        self.settings_tab.pack(fill="both", expand=True)

        # Статус бар
        statusbar = ctk.CTkFrame(self, fg_color="#0d1117", height=28)
        statusbar.pack(fill="x", side="bottom")
        statusbar.pack_propagate(False)

        self.statusbar_label = ctk.CTkLabel(
            statusbar,
            text="⏳ Загрузка...",
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        )
        self.statusbar_label.pack(side="left", padx=15)

        ctk.CTkLabel(
            statusbar,
            text="v2.0.0 async",
            font=ctk.CTkFont(size=11),
            text_color="#333333"
        ).pack(side="right", padx=15)

    def reconnect_github(self):
        """Асинхронное подключение к GitHub"""
        token = self.config.get("github_token", "")
        username = self.config.get("github_username", "")
        repo = self.config.get("github_repo", "")

        if not all([token, username, repo]):
            self.github_status.configure(
                text="⚪ GitHub: не настроен",
                text_color="#888888"
            )
            return

        def connect():
            self.github_sync = GitHubSync(token, username, repo)
            if self.github_sync.is_connected():
                self.after(0, lambda: self.github_status.configure(
                    text=f"🟢 GitHub: {username}/{repo}",
                    text_color="#81c784"
                ))
            else:
                self.after(0, lambda: self.github_status.configure(
                    text="🔴 GitHub: ошибка",
                    text_color="#ef9a9a"
                ))

        async_helper.run_in_executor(connect)

    def _load_data_async(self):
        """Асинхронная загрузка данных"""
        self.statusbar_label.configure(text="⏳ Загрузка данных...")

        def load():
            data = self._load_data()
            self.data = data
            count = len(data.get("apartments", []))
            self.after(0, lambda: (
                self.refresh_all_tabs(),
                self.statusbar_label.configure(
                    text=f"✅ Загружено {count} квартир"
                )
            ))

        async_helper.run_in_executor(load)

    def _load_data(self) -> dict:
        """Загрузка данных (синхронно, вызывается из executor)"""
        if self.github_sync and self.github_sync.is_connected():
            return self.github_sync.load_data()

        import json, os
        if os.path.exists("local_data.json"):
            try:
                with open("local_data.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return {"apartments": []}

    def sync_data(self):
        """
        Синхронизация данных.
        Можно вызывать из любого потока.
        """
        # Локальное сохранение
        import json
        try:
            with open("local_data.json", "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка локального сохранения: {e}")

        # GitHub
        if self.github_sync and self.github_sync.is_connected():
            success = self.github_sync.save_data(self.data)
            msg = "✅ Синхронизировано" if success else "⚠️ Только локально"
        else:
            msg = "⚠️ Сохранено локально"

        self.after(0, lambda: self.statusbar_label.configure(text=msg))

    def _manual_sync(self):
        """Ручная синхронизация"""
        self.sync_btn.configure(state="disabled", text="⏳ Синхронизация...")

        def do():
            remote = self._load_data()
            remote_map = {a["id"]: a for a in remote.get("apartments", [])}
            local_map = {a["id"]: a for a in self.data.get("apartments", [])}
            merged = {**remote_map, **local_map}
            self.data["apartments"] = list(merged.values())
            self.sync_data()
            self.after(0, lambda: (
                self.refresh_all_tabs(),
                self.sync_btn.configure(
                    state="normal",
                    text="🔄 Синхронизировать"
                )
            ))

        async_helper.run_in_executor(do)

    def refresh_all_tabs(self):
        """Обновление всех вкладок (в главном потоке)"""
        self.search_tab.refresh()
        self.approved_tab.refresh()
        self.rejected_tab.refresh()

        total = len(self.data.get("apartments", []))
        approved = sum(
            1 for a in self.data.get("apartments", [])
            if a.get("status") == "approved"
        )
        search_count = sum(
            1 for a in self.data.get("apartments", [])
            if a.get("status") == "search"
        )
        self.statusbar_label.configure(
            text=f"Всего: {total} | "
                 f"В поиске: {search_count} | "
                 f"Одобрено: {approved}"
        )

    def on_closing(self):
        """Закрытие приложения"""
        async_helper.shutdown()
        self.destroy()


def main():
    app = RealtorApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()