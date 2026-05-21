import asyncio
import aiohttp
import threading
from PIL import Image, ImageTk
from io import BytesIO
from typing import Optional, Callable
import hashlib
import os


class ImageCache:
    """
    Асинхронный кэш изображений.
    Загружает фото в фоне, не блокируя UI.
    Кэширует на диск для повторного использования.
    """

    CACHE_DIR = ".img_cache"

    def __init__(self):
        self._memory_cache: dict = {}
        self._lock = threading.Lock()
        self._pending: set = set()

        # Создаём папку кэша
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def _url_to_hash(self, url: str) -> str:
        """URL → хэш для имени файла"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, url: str) -> str:
        """Путь к кэшированному файлу"""
        return os.path.join(self.CACHE_DIR, self._url_to_hash(url) + ".jpg")

    def get_from_memory(self, url: str) -> Optional[Image.Image]:
        """Получить из памяти (мгновенно)"""
        with self._lock:
            return self._memory_cache.get(url)

    def _load_from_disk(self, url: str) -> Optional[Image.Image]:
        """Загрузить с диска если есть"""
        path = self._get_cache_path(url)
        if os.path.exists(path):
            try:
                img = Image.open(path)
                img.load()  # Полная загрузка
                with self._lock:
                    self._memory_cache[url] = img
                return img
            except Exception:
                os.remove(path)
        return None

    async def load_image_async(
        self,
        url: str,
        size: tuple,
        callback: Callable,
        widget_ref
    ):
        """
        Асинхронная загрузка изображения.
        1. Проверяем память → 2. Диск → 3. Сеть
        """
        # Проверяем память
        img = self.get_from_memory(url)
        if img:
            resized = img.resize(size, Image.LANCZOS)
            widget_ref.after(0, lambda: callback(resized, url))
            return

        # Проверяем диск
        img = self._load_from_disk(url)
        if img:
            resized = img.resize(size, Image.LANCZOS)
            widget_ref.after(0, lambda: callback(resized, url))
            return

        # Предотвращаем дублирование загрузок
        with self._lock:
            if url in self._pending:
                return
            self._pending.add(url)

        # Загружаем из сети
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        img = Image.open(BytesIO(data))
                        img = img.convert("RGB")

                        # Сохраняем в кэши
                        with self._lock:
                            self._memory_cache[url] = img

                        # Сохраняем на диск в фоне
                        cache_path = self._get_cache_path(url)
                        try:
                            img.save(cache_path, "JPEG", quality=85)
                        except Exception:
                            pass

                        resized = img.resize(size, Image.LANCZOS)
                        widget_ref.after(0, lambda: callback(resized, url))

        except asyncio.TimeoutError:
            print(f"Timeout загрузки: {url}")
        except Exception as e:
            print(f"Ошибка загрузки фото: {e}")
        finally:
            with self._lock:
                self._pending.discard(url)

    def clear_memory(self):
        """Очистка памяти"""
        with self._lock:
            self._memory_cache.clear()


# Глобальный кэш
image_cache = ImageCache()