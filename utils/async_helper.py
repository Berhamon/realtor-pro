import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
import queue


class AsyncHelper:
    """
    Менеджер асинхронных задач.
    Запускает event loop в отдельном потоке,
    не блокируя главный UI поток.
    """

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="AsyncHelperLoop"
        )
        self._thread.start()

    def _run_loop(self):
        """Запуск event loop в отдельном потоке"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_coroutine(self, coro, callback: Callable = None):
        """
        Запуск корутины без блокировки UI.
        callback вызывается с результатом в главном потоке.
        """
        async def wrapper():
            try:
                result = await coro
                return result
            except Exception as e:
                print(f"AsyncHelper error: {e}")
                return None

        future = asyncio.run_coroutine_threadsafe(wrapper(), self._loop)

        if callback:
            def on_done(fut):
                result = fut.result()
                callback(result)
            future.add_done_callback(on_done)

        return future

    def run_in_executor(self, func: Callable, *args, callback: Callable = None):
        """
        Запуск обычной блокирующей функции
        в пуле потоков без блокировки UI.
        """
        async def wrapper():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, func, *args
            )

        return self.run_coroutine(wrapper(), callback=callback)

    def shutdown(self):
        """Остановка"""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._executor.shutdown(wait=False)


# Глобальный экземпляр
async_helper = AsyncHelper()