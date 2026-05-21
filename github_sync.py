import json
import base64
from github import Github, GithubException
from typing import Optional


DATA_FILE = "realtor_data.json"


class GitHubSync:
    def __init__(self, token: str, username: str, repo_name: str):
        self.token = token
        self.username = username
        self.repo_name = repo_name
        self.github = None
        self.repo = None
        self._connect()

    def _connect(self) -> bool:
        """Подключение к GitHub"""
        try:
            self.github = Github(self.token)
            user = self.github.get_user()
            self.repo = user.get_repo(self.repo_name)
            return True
        except GithubException as e:
            print(f"Ошибка подключения к GitHub: {e}")
            return False
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    def create_repo_if_not_exists(self) -> bool:
        """Создание репозитория если не существует"""
        try:
            user = self.github.get_user()
            try:
                self.repo = user.get_repo(self.repo_name)
                return True
            except GithubException:
                self.repo = user.create_repo(
                    self.repo_name,
                    description="Realtor App Data",
                    private=True,
                    auto_init=True
                )
                return True
        except Exception as e:
            print(f"Ошибка создания репозитория: {e}")
            return False

    def load_data(self) -> dict:
        """Загрузка данных из GitHub"""
        default_data = {
            "apartments": [],
            "last_updated": ""
        }

        if not self.repo:
            return default_data

        try:
            contents = self.repo.get_contents(DATA_FILE)
            content = base64.b64decode(contents.content).decode("utf-8")
            return json.loads(content)
        except GithubException as e:
            if e.status == 404:
                # Файл не существует, создаём
                self.save_data(default_data)
                return default_data
            print(f"Ошибка загрузки данных: {e}")
            return default_data
        except Exception as e:
            print(f"Ошибка: {e}")
            return default_data

    def save_data(self, data: dict) -> bool:
        """Сохранение данных на GitHub"""
        if not self.repo:
            return False

        try:
            from datetime import datetime
            data["last_updated"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            content = json.dumps(data, ensure_ascii=False, indent=2)

            try:
                # Обновляем существующий файл
                existing = self.repo.get_contents(DATA_FILE)
                self.repo.update_file(
                    DATA_FILE,
                    f"Update data {data['last_updated']}",
                    content,
                    existing.sha
                )
            except GithubException as e:
                if e.status == 404:
                    # Создаём новый файл
                    self.repo.create_file(
                        DATA_FILE,
                        "Initial data",
                        content
                    )
                else:
                    raise

            return True

        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")
            return False

    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.repo is not None