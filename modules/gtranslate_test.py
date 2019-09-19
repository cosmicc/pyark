import sys

import pytest
import modules.gtranslate

sys.path.append('/home/ark/pyark')


def test_trans_to_eng():
    with pytest.raises(TypeError):
        assert type(modules.gtranslate.trans_to_eng(132))
        assert type(modules.gtranslate.trans_to_eng(['Test', 'me']))
    assert type(modules.gtranslate.trans_to_eng('hello')) is str
    assert modules.gtranslate.trans_to_eng('hola') == 'Hello (Translated Spanish)'


def test_trans_from_eng():
    with pytest.raises(TypeError):
        assert type(modules.gtranslate.trans_from_eng(132, 543))
        assert type(modules.gtranslate.trans_from_eng(['Test', 'me']))
    assert type(modules.gtranslate.trans_from_eng('hola')) is str
    assert modules.gtranslate.trans_from_eng('hello') == 'Hello (Translated Spanish)'


