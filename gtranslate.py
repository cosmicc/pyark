from googletrans import Translator
import iso639


def trans_to_eng(text):
    translator = Translator()
    lang = translator.detect(text)
    if lang.lang != 'en':
        trans = translator.translate(text)
        result = trans.text + f' (Translated {iso639.to_name(trans.src)})'
        return result
    else:
        return text


def quicktranslate(text, lang='en'):
    translator = Translator()
    trans = translator.translate(text, dest=lang)
    result = {'language': iso639.to_name(trans.src), 'iso639': trans.src, 'text': trans.text}
    return result
