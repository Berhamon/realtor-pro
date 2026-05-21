import json
import os

DEFAULT_CONFIG = {
    "vk_token": "",
    "github_token": "",
    "github_repo": "",
    "github_username": "",
    "vk_groups": [],
    "yandex_maps_api": ""
}

CONFIG_FILE = "config.json"


def load_config():
    """Загрузка конфигурации из файла"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Добавляем недостающие ключи
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"Ошибка загрузки конфига: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Сохранение конфигурации в файл"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка сохранения конфига: {e}")
        return False