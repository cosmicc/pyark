import sys

import modules.players as players

sys.path.append("/home/ark/pyark")


def test_getplayer():
    assert players.getplayer(99999999999999999) is None
    assert players.getplayer(76561198388849736) is not None
    assert players.getplayer(76561198388849736)[1] == "rykker"


def test_playerlastseen():
    assert type(players.getplayerlastseen(playername="rykker")) is int
    assert type(players.getplayerlastseen(steamid=76561198388849736)) is int


def test_playerlastserver():
    assert type(players.getplayerlastserver(playername="rykker")) is str
    assert type(players.getplayerlastserver(steamid=76561198388849736)) is str


def test_getplayersonline():
    assert type(players.getplayersonline("ragnarok")) is list
    assert type(players.getplayersonline("all")) is list
    assert type(players.getplayersonline("ragnarok", fmt="string")) is str
    assert type(players.getplayersonline("ragnarok", fmt="count")) is int
    assert type(players.getplayersonline("all", fmt="count")) is int
    assert type(players.getplayersonline("all", fmt="string")) is str


def test_getlastplayersonline():
    assert type(players.getlastplayersonline("all")) is list
    assert len(players.getlastplayersonline("all")) == 5
    assert len(players.getlastplayersonline("all", last=8)) == 8
    assert type(players.getlastplayersonline("all", fmt="string")) is str
    assert type(players.getlastplayersonline("all", fmt="list")) is list
    assert type(players.getlastplayersonline("ragnarok")) is list
    assert type(players.getlastplayersonline("ragnarok", fmt="count")) is int
