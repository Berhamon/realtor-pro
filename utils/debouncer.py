import threading
from typing import Callable


class Debouncer:
    """
    Debounce для поиска.
    Ждёт пока пользователь перестанет печатать
    и только потом выполняет поиск.
    Устраняет лаги при вводе текста.
    """

    def __init__(self, delay_ms: int = 300):
        self.delay_ms = delay_ms
        self.delay_sec = delay_ms / 1000
        self._timer: threading.Timer = None
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """
        Вызвать функцию с задержкой.
        Если вызвать снова до истечения задержки —
        таймер сбрасывается.
        """
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(
                self.delay_sec,
                self._execute,
                args=[func, *args],
                kwargs=kwargs
            )
            self._timer.daemon = True
            self._timer.start()

    def _execute(self, func: Callable, *args, **kwargs):
        """Выполнение функции"""
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Debouncer error: {e}")

    def cancel(self):
        """Отмена ожидающего вызова"""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None