import http.client
import json
from typing import List

import anki.cards
import anki.notes
from aqt import gui_hooks, mw

# TODO: Make a config file and move API key there
# TODO: Save response from remote to a database
# TODO: Automatically find the column in note as a word

API_KEY = "API_KEY"
DATABASE_FILENAME = "cache.sqlite3"


def lookup_thesaurus(word: str):
    try:
        connection = http.client.HTTPSConnection("api.api-ninjas.com", timeout=3)
        connection.request('GET', f'/v1/thesaurus?word={word}', headers={'X-Api-Key': API_KEY})
        response = connection.getresponse().read().decode()
        response_json = json.loads(response)
        synonyms = list(filter(lambda x: len(x) > 0, response_json['synonyms']))
        antonyms = list(filter(lambda x: len(x) > 0, response_json['antonyms']))
        return synonyms[:5], antonyms[:5]
    except Exception:
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
        return text


def add_thesaurus(text: str, card: anki.cards.Card, type: str) -> str:
    if type == "reviewAnswer":
        word = card.note()["单词"]
        synonyms, antonyms = lookup_thesaurus(word)
        return inject_thesaurus(synonyms, antonyms, text)
    return text


def load_config():
    global API_KEY
    config = mw.addonManager.getConfig(__name__)
    API_KEY = config['API_NINJAS_API_KEY']

load_config()
gui_hooks.card_will_show.append(add_thesaurus)
