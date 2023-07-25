import datetime
import http.client
import json
import os
import sqlite3
import traceback
from typing import List, Tuple

import anki.cards
import anki.notes
from aqt import gui_hooks, mw

# TODO: Use direct reference to the config
# TODO: Automatically find the column in note as a word

API_KEY = "API_KEY"
DEBUG_MODE = False
ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILENAME = "user_files/cache.sqlite3"

DATABASE_CONNECTION: sqlite3.Connection = None


def lookup_thesaurus(word: str):
    try:
        synonyms, antonyms = get_thesaurus_from_cache_database(word)
        if synonyms is None or antonyms is None:
            if DEBUG_MODE:
                print(f"CACHE MISS: {word}")
            lookup_time = datetime.datetime.now()
            connection = http.client.HTTPSConnection("api.api-ninjas.com", timeout=3)
            connection.request('GET', f'/v1/thesaurus?word={word}', headers={'X-Api-Key': API_KEY})
            response = connection.getresponse().read().decode()
            response_json = json.loads(response)
            synonyms = list(filter(lambda x: len(x) > 0, response_json['synonyms']))
            antonyms = list(filter(lambda x: len(x) > 0, response_json['antonyms']))
            save_thesaurus_to_cache_database(word, synonyms, antonyms, lookup_time)
        else:
            if DEBUG_MODE:
                print(f"CACHE HIT: {word}")
        return synonyms[:5], antonyms[:5]
    except Exception:
        if DEBUG_MODE:
            traceback.print_exc()
        return [], []


def inject_thesaurus(synonyms: List[str], antonyms: List[str], text: str) -> str:
    try:
        anchor = '<div id="back">'
        ind = text.find(anchor)
        if ind < 0:
            return text
        ind += len(anchor)

        synonyms_text = ""
        if len(synonyms) > 0:
            synonyms_text = f"""<center><span style="font-size: 16px"><div style=''><b>Synonyms:</b> {', '.join(synonyms)}</div></span></center>"""

        antonyms_text = ""
        if len(antonyms) > 0:
            antonyms_text = f"""<center><span style="font-size: 16px"><div style=''><b>Antonyms:</b> {', '.join(antonyms)}</div></span></center>"""

        return text[:ind] + synonyms_text + antonyms_text + text[ind:]
    except Exception:
        if DEBUG_MODE:
            traceback.print_exc()
        return text


def add_thesaurus(text: str, card: anki.cards.Card, type: str) -> str:
    if type == "reviewAnswer":
        word = card.note()["单词"]
        if DEBUG_MODE:
            print(f"Start looking up thesaurus for word: {word}")
        synonyms, antonyms = lookup_thesaurus(word)
        return inject_thesaurus(synonyms, antonyms, text)
    return text


def load_config():
    config = mw.addonManager.getConfig(__name__)

    global API_KEY
    API_KEY = config['API_NINJAS_API_KEY']

    global DEBUG_MODE
    DEBUG_MODE = config["DEBUG_MODE"]


def init_cache_database():
    connection = sqlite3.connect(os.path.join(ADDON_PATH, DATABASE_FILENAME))
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

    global DATABASE_CONNECTION
    DATABASE_CONNECTION = connection


def get_thesaurus_from_cache_database(word: str) -> Tuple[List[str], List[str]]:
    cursor = DATABASE_CONNECTION.cursor()
    res = cursor.execute("""SELECT synonyms, antonyms FROM thesaurus WHERE word = ?""", (word,))
    result = res.fetchone()
    if result is None:
        return None, None
    else:
        return list(filter(lambda x: len(x) > 0, result[0].split(';'))), list(filter(lambda x: len(x) > 0, result[1].split(';')))


def save_thesaurus_to_cache_database(word: str, synonyms: List[str], antonyms: List[str], lookup_time: datetime.datetime):
    cursor = DATABASE_CONNECTION.cursor()
    synonyms_db_str = ";".join(synonyms)
    antonyms_db_str = ";".join(antonyms)
    cursor.execute("""INSERT INTO thesaurus(word, synonyms, antonyms, lookup_time) VALUES (?, ?, ?, ?)""",
                   (word, synonyms_db_str, antonyms_db_str, lookup_time))
    DATABASE_CONNECTION.commit()
    if DEBUG_MODE:
        print(f"Save entry {word} into the database")


load_config()
init_cache_database()
gui_hooks.card_will_show.append(add_thesaurus)
