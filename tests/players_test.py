import sys
sys.path.append('/home/ark/pyark')
import modules.players as players


def test_getplayer():
    assert dbhelper.getplayer(99999999999999999) is None
    assert dbhelper.getplayer(76561198388849736) is not None
    assert dbhelper.getplayer(76561198388849736)[1] == 'rykker'


def test_playerlastseen():
    assert type(dbhelper.getplayerlastseen(playername='rykker')) is int
    assert type(dbhelper.getplayerlastseen(steamid=76561198388849736)) is int


def test_playerlastserver():
    assert type(dbhelper.getplayerlastserver(playername='rykker')) is str
    assert type(dbhelper.getplayerlastserver(steamid=76561198388849736)) is str


def test_getplayersonline():
    assert type(dbhelper.getplayersonline('ragnarok')) is list
    assert type(dbhelper.getplayersonline('all')) is list
    assert type(dbhelper.getplayersonline('ragnarok', fmt='string')) is str
    assert type(dbhelper.getplayersonline('ragnarok', fmt='count')) is int
    assert type(dbhelper.getplayersonline('all', fmt='count')) is int
    assert type(dbhelper.getplayersonline('all', fmt='string')) is str


def test_getlastplayersonline():
    assert type(dbhelper.getlastplayersonline('all')) is list
    assert len(dbhelper.getlastplayersonline('all')) == 5
    assert len(dbhelper.getlastplayersonline('all', last=8)) == 8
    assert type(dbhelper.getlastplayersonline('all', fmt='string')) is str
    assert type(dbhelper.getlastplayersonline('all', fmt='list')) is list
    assert type(dbhelper.getlastplayersonline('ragnarok')) is list
    assert type(dbhelper.getlastplayersonline('ragnarok', fmt='count')) is int
