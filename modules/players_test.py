import sys

from asyncpg import Record
import modules.players

sys.path.append('/home/ark/pyark')


async def test_asyncgetplayerinfo():
    assert type(await modules.players.asyncgetplayerinfo(steamid='76561198408657294')) is Record
    assert type(await modules.players.asyncgetplayerinfo(steamid='11111101011650101')) is Record
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
    assert type(await modules.players.asyncgetplayerinfo(instance='coliseum', fmt='count')) is int
    assert type(await modules.players.asyncgetplayerinfo(instance='coliseum', fmt='string')) is str
    assert type(await modules.players.asyncgetplayerinfo(instance='coliseum', fmt='list')) is list
    assert await modules.players.asyncgetplayerinfo(instance='coliseum', fmt='count') == 0
    assert await modules.players.asyncgetplayerinfo(instance='coliseum', fmt='string') == ''
