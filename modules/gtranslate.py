from googletrans import Translator
from iso639 import languages as iso639


def trans_to_eng(text):
    try:
        translator = Translator()
        lang = translator.detect(text)
        if lang.lang != 'en':
            trans = translator.translate(text)
            result = trans.text + f' (Translated {iso639.get(part1=trans.src).name})'
            return result
        else:
            return text
    except:
        return '*' + text


def trans_from_eng(text, lang):
    if len(lang) == 2:
        nlang = lang
    elif len(lang) == 3:
        nlang = lang
    elif len(lang) > 3:
        nlang = lang
    try:
        translator = Translator()
        text = text + f' (Translated English)'
        trans = translator.translate(text, dest=nlang)
        result = {'language': iso639.get(part1=trans.src).name, 'iso639': trans.src, 'text': trans.text}
        return result['text']
    except:
        return f'{text} (Not Translated)'
