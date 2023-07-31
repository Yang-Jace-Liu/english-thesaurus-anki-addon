import datetime
import http.client
import json
import traceback
from typing import List

import anki.cards
import anki.notes
from aqt import mw, gui_hooks

from .configs import Config
from .database import init_cache_database
from .worker import WorkerThread

# TODO: Use direct reference to the config
# TODO: Automatically find the column in note as a word

worker_thread: WorkerThread = None


def lookup_thesaurus(word: str):
    try:
        synonyms, antonyms = get_thesaurus_from_cache_database(word)
        if synonyms is None or antonyms is None:
            if Config.DEBUG_MODE:
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
            if Config.DEBUG_MODE:
                print(f"CACHE HIT: {word}")
        return synonyms[:5], antonyms[:5]
    except Exception:
        if Config.DEBUG_MODE:
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
        if Config.DEBUG_MODE:
            traceback.print_exc()
        return text


def add_thesaurus_trigger(text: str, card: anki.cards.Card, type: str) -> str:
    if type == "reviewAnswer":
        word = card.note()[Config.CARD_WORD_FIELD_NAME]
        if Config.DEBUG_MODE:
            print(f"Start looking up thesaurus for word: {word}")
        synonyms, antonyms = lookup_thesaurus(word)
        return inject_thesaurus(synonyms, antonyms, text)
    return text


def load_config():
    config = mw.addonManager.getConfig(__name__)

    Config.API_NINJAS_API_KEY = config['API_NINJAS_API_KEY']
    Config.DEBUG_MODE = config["DEBUG_MODE"]
    Config.CARD_WORD_FIELD_NAME = config["CARD_WORD_FIELD_NAME"]
    Config.CARD_TYPE = config["CARD_TYPE"]


def init_worker_thread():
    global worker_thread
    worker_thread = WorkerThread()
    worker_thread.setDaemon(True)
    worker_thread.start()


def startup_trigger():
    card_ids = mw.col.find_cards(f"is:due note:{Config.CARD_TYPE}")
    for card_id in card_ids:
        card = mw.col.get_card(card_id)
        word = card.note()[Config.CARD_WORD_FIELD_NAME]
        worker_thread.lookup_word(word)


load_config()

if Config.DEBUG_MODE:
    init_cache_database()
init_worker_thread()
gui_hooks.profile_did_open.append(startup_trigger)
gui_hooks.card_will_show.append(add_thesaurus_trigger)
