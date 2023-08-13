import asyncio
import threading
from typing import Tuple, List

from .configs import Config
from .database import get_thesaurus_from_cache_database, save_thesaurus_to_cache_database, init_cache_database
from .thesaurus_fetchers import ThesaurusFetcherIntf, ThesaurusResult


class WorkerThread(threading.Thread):
    def __init__(self, thesaurus_fetcher: ThesaurusFetcherIntf, async_task_pool_size: int = 5):
        super().__init__()
        self.thesaurus_fetcher = thesaurus_fetcher
        self.async_task_pool_size = async_task_pool_size
        self.loop: asyncio.AbstractEventLoop = None
        self.queue: asyncio.Queue = None
        self.sem: asyncio.Semaphore = None

    def run(self) -> None:
        init_cache_database()
        asyncio.run(self.async_main())

    async def async_main(self):
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.LifoQueue()
        self.sem = asyncio.Semaphore(self.async_task_pool_size)
        while True:
            await self.sem.acquire()
            word = await self.queue.get()
            asyncio.create_task(self._lookup_for_word(word))

    async def _lookup_for_word(self, word: str, prioritized: bool = False) -> Tuple[List[str], List[str]]:
        if Config.DEBUG_MODE:
            print(f"Start task for looking up work: {word}")

        synonyms, antonyms = await get_thesaurus_from_cache_database(word)
        if synonyms is None and antonyms is None:
            if Config.DEBUG_MODE:
                print(f"Cache Miss: {word}")
            synonyms_result: ThesaurusResult = await self.thesaurus_fetcher.fetch_thesaurus_for_word(word)
            synonyms, antonyms = synonyms_result.synonyms, synonyms_result.antonyms
            await save_thesaurus_to_cache_database(word, synonyms, antonyms, synonyms_result.lookup_time)
        else:
            if Config.DEBUG_MODE:
                print(f"Cache Hit: {word}")
        if not prioritized:
            self.sem.release()
        return synonyms, antonyms

    def schedule_lookup_word(self, word: str):
        async def lookup_word_async(word: str):
            if Config.DEBUG_MODE:
                print(f"Schedule task for looking up word: {word}")
            await self.queue.put(word)

        asyncio.run_coroutine_threadsafe(lookup_word_async(word), self.loop)

    def lookup_word(self, word: str):
        future = asyncio.run_coroutine_threadsafe(self._lookup_for_word(word, prioritized=True), self.loop)
        return future.result()
