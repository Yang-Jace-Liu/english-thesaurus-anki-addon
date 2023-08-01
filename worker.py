import asyncio
import random
import threading

from .configs import Config


class WorkerThread(threading.Thread):
    def __init__(self, async_task_pool_size: int = 5):
        super().__init__()
        self.async_task_pool_size = async_task_pool_size
        self.loop: asyncio.AbstractEventLoop = None

    def run(self) -> None:
        asyncio.run(self.async_main())

    async def async_main(self):
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.LifoQueue()
        self.sem = asyncio.Semaphore(self.async_task_pool_size)
        while True:
            await self.sem.acquire()
            word = await self.queue.get()
            asyncio.create_task(self._lookup_for_word(word))

    async def _lookup_for_word(self, word: str):
        if Config.DEBUG_MODE:
            print(f"looking up for word: {word}")
        await asyncio.sleep(random.random() * 5)
        self.sem.release()

    def lookup_word(self, word: str):
        async def lookup_word_async(word: str):
            if Config.DEBUG_MODE:
                print(f"Start looking up for word: {word}")
            await self.queue.put(word)
        asyncio.run_coroutine_threadsafe(lookup_word_async(word), self.loop)