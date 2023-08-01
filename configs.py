import os


class Constants:
    ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
    DATABASE_FILENAME = "user_files/cache.sqlite3"

    DATABASE_FULL_PATH = os.path.join(ADDON_PATH, DATABASE_FILENAME)


class Config:
    THESAURUS_SOURCE: str = None

    DEBUG_MODE: bool = False

    API_NINJAS_API_KEY: str = None

    CARD_TYPE: str = ""

    CARD_WORD_FIELD_NAME: str = ""