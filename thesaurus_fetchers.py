import datetime
import enum
import http.client
import json
from abc import ABC

from .configs import Config


class ThesaurusSource(enum.Enum):
    API_NINJAS = 1


class ThesaurusResult:
    def __init__(self, synonyms, antonyms, lookup_time, source):
        self._synonyms = synonyms
        self._antonyms = antonyms
        self._lookup_time = lookup_time
        self._source = source

    @property
    def synonyms(self) -> str:
        return self._synonyms

    @property
    def antonyms(self) -> str:
        return self._antonyms

    @property
    def lookup_time(self) -> str:
        return self._lookup_time

    @property
    def source(self) -> ThesaurusSource:
        return self._source


class ThesaurusFetcherIntf(ABC):
    def __init__(self):
        pass

    async def fetch_thesaurus_for_word(self, word: str) -> ThesaurusResult:
        raise NotImplementedError()


class ApiNinjasThesaurusFetcher(ThesaurusFetcherIntf):
    def __init__(self):
        super().__init__()

    async def fetch_thesaurus_for_word(self, word: str) -> ThesaurusResult:
        if Config.DEBUG_MODE:
            print(f"Fetching thesaurus from API Ninjas for word: {word}")

        lookup_time = datetime.datetime.now()
        connection = http.client.HTTPSConnection("api.api-ninjas.com", timeout=3)
        connection.request('GET', f'/v1/thesaurus?word={word}', headers={'X-Api-Key': Config.API_NINJAS_API_KEY})
        response = connection.getresponse().read().decode()
        response_json = json.loads(response)
        synonyms = list(filter(lambda x: len(x) > 0, response_json['synonyms']))
        antonyms = list(filter(lambda x: len(x) > 0, response_json['antonyms']))

        if Config.DEBUG_MODE:
            print(f"Done fetching thesaurus for word: {word}")

        return ThesaurusResult(synonyms, antonyms, lookup_time, source=ThesaurusSource.API_NINJAS)
