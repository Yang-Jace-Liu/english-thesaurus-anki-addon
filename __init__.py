import traceback
from typing import List

import anki.cards
import anki.notes
from aqt import mw, gui_hooks

from .configs import Config
from .thesaurus_fetchers import ThesaurusFetcherIntf, ApiNinjasThesaurusFetcher
from .worker import WorkerThread

# TODO: Use direct reference to the config
# TODO: Automatically find the column in note as a word

worker_thread: WorkerThread = None


def inject_thesaurus(synonyms: List[str], antonyms: List[str], text: str) -> str:
    if synonyms is not None:
        synonyms = synonyms[:5]
    if antonyms is not None:
        antonyms = antonyms[:5]
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
        synonyms, antonyms = worker_thread.lookup_word(word)
        return inject_thesaurus(synonyms, antonyms, text)
    return text


def load_config():
    config = mw.addonManager.getConfig(__name__)

    Config.API_NINJAS_API_KEY = config['ApiNinjasApiKey']
    Config.DEBUG_MODE = config["DebugMode"]
    Config.CARD_WORD_FIELD_NAME = config["CardWordFieldName"]
    Config.CARD_TYPE = config["CardType"]
    Config.THESAURUS_SOURCE = config["ThesaurusSource"]


def init_thesaurus_fetcher() -> ThesaurusFetcherIntf:
    if Config.THESAURUS_SOURCE == "ApiNinjas":
        return ApiNinjasThesaurusFetcher()
    else:
        raise RuntimeError(f"Cannot find thesaurus source {Config.THESAURUS_SOURCE}")


def init_worker_thread():
    global worker_thread
    worker_thread = WorkerThread(init_thesaurus_fetcher())
    worker_thread.setDaemon(True)
    worker_thread.start()


def startup_trigger():
    card_ids = mw.col.find_cards(f"is:due note:{Config.CARD_TYPE}")
    for card_id in card_ids:
        card = mw.col.get_card(card_id)
        word = card.note()[Config.CARD_WORD_FIELD_NAME]
        worker_thread.schedule_lookup_word(word)


load_config()

init_worker_thread()
gui_hooks.profile_did_open.append(startup_trigger)
gui_hooks.card_will_show.append(add_thesaurus_trigger)
