import sys

from asyncpg import Record
import modules.players

sys.path.append('/home/ark/pyark')


async def test_asyncgetplayerinfo():
    assert type(await modules.players.asyncgetplayerinfo(steamid='76561198408657294')) is Record
    player = await modules.players.asyncgetplayerinfo(steamid='76561198408657294')
    assert player['playername'] == 'admin'
    assert type(await modules.players.asyncgetplayerinfo(playername='Admin')) is Record
    assert type(await modules.players.asyncgetplayerinfo(discordid='Rykker#7393')) is Record
    player = await modules.players.asyncgetplayerinfo(discordid='Rykker#7393')
    assert player['playername'] == 'rykker'
    assert type(await modules.players.asyncgetplayerinfo(steamname='Galaxy-Cluster')) is Record
    player = await modules.players.asyncgetplayerinfo(steamname='Galaxy-Cluster')
    assert player['playername'] == 'admin'
    assert type(await modules.players.asyncgetplayerinfo(steamname='galaxy-cluster')) is Record


async def test_asyncgetplayersonline():
    assert type(await modules.players.asyncgetplayersonline('ragnarok', fmt='count')) is int
    assert type(await modules.players.asyncgetplayersonline('ragnarok', fmt='string')) is str
    assert type(await modules.players.asyncgetplayersonline('ragnarok', fmt='list')) is list
    assert type(await modules.players.asyncgetplayersonline('all', fmt='count')) is int
    assert type(await modules.players.asyncgetplayersonline('ALL', fmt='string')) is str
    assert type(await modules.players.asyncgetplayersonline('all', fmt='list')) is list


async def test_getplayerstoday():
    assert type(await modules.players.getplayerstoday('ragnarok', fmt='count')) is int
    assert type(await modules.players.getplayerstoday('ragnarok', fmt='string')) is str
    assert type(await modules.players.getplayerstoday('ragnarok', fmt='list')) is list
    assert type(await modules.players.getplayerstoday('all', fmt='count')) is int
    assert type(await modules.players.getplayerstoday('ALL', fmt='string')) is str
    assert type(await modules.players.getplayerstoday('all', fmt='list')) is list


async def test_asyncgettopplayedplayers():
    assert type(await modules.players.asyncgettopplayedplayers('ragnarok', fmt='list')) is list
    assert type(await modules.players.asyncgettopplayedplayers('ragnarok', fmt='string')) is str
    assert type(await modules.players.asyncgettopplayedplayers('all', fmt='list')) is list
    assert type(await modules.players.asyncgettopplayedplayers('all', fmt='string')) is str
    assert len(await modules.players.asyncgettopplayedplayers('all', fmt='string', last=10)) == 10


async def test_asyncgetnewestplayers():
    assert type(await modules.players.asyncgetnewestplayers('ragnarok', fmt='list')) is list
    assert type(await modules.players.asyncgetnewestplayers('ragnarok', fmt='string')) is str
    assert type(await modules.players.asyncgetnewestplayers('all', fmt='list')) is list
    assert type(await modules.players.asyncgetnewestplayers('all', fmt='string')) is str
    assert len(await modules.players.asyncgetnewestplayers('all', fmt='string', last=10)) == 10
