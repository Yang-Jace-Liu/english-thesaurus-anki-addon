import asyncio
import datetime
import sqlite3
from typing import List, Tuple

from .configs import Constants, Config

db_connection: sqlite3.Connection = None

db_lock = asyncio.Lock()

def init_cache_database():
    connection = sqlite3.connect(Constants.DATABASE_FULL_PATH)
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS thesaurus (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        word TEXT UNIQUE NOT NULL,
        synonyms TEXT,
        antonyms TEXT,
        lookup_time DATETIME
    );""")

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS
    id_word ON thesaurus (word);
    """)
    connection.commit()

    global db_connection
    db_connection = connection


async def get_thesaurus_from_cache_database(word: str) -> Tuple[List[str], List[str]]:
    async with db_lock:
        cursor = db_connection.cursor()
        res = cursor.execute("""SELECT synonyms, antonyms FROM thesaurus WHERE word = ?""", (word,))
        result = res.fetchone()
        if result is None:
            return None, None
        else:
            return list(filter(lambda x: len(x) > 0, result[0].split(';'))), list(filter(lambda x: len(x) > 0, result[1].split(';')))


async def save_thesaurus_to_cache_database(word: str, synonyms: List[str], antonyms: List[str], lookup_time: datetime.datetime):
    async with db_lock:
        cursor = db_connection.cursor()
        synonyms_db_str = ";".join(synonyms)
        antonyms_db_str = ";".join(antonyms)
        cursor.execute("""INSERT INTO thesaurus(word, synonyms, antonyms, lookup_time) VALUES (?, ?, ?, ?)""",
                       (word, synonyms_db_str, antonyms_db_str, lookup_time))
        db_connection.commit()
        if Config.DEBUG_MODE:
            print(f"Save entry {word} into the database")
