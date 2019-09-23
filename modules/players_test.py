import sys

from asyncpg import Record
import modules.players
import pytest

sys.path.append('/home/ark/pyark')


async def test_asyncgetplayerinfo():
    assert await modules.players.asyncgetplayerinfo(steamid='76561198408657294') is Record
    player = await modules.players.asyncgetplayerinfo(steamid='76561198408657294')
    assert player['playername'] == 'admin'
    assert await len(modules.players.asyncgetplayerinfo(steamid='76561198408657294')) == 1
    assert await modules.players.asyncgetplayerinfo(playername='Admin') is Record
    assert await len(modules.players.asyncgetplayerinfo(playername='Admin')) == 1
    assert await modules.players.asyncgetplayerinfo(discordid='Rykker#7393') is Record
    player = await modules.players.asyncgetplayerinfo(discordid='Rykker#7393')
    assert player['playername'] == 'rykker'
    assert await len(modules.players.asyncgetplayerinfo(discordid='Rykker#7393')) == 1
    assert await modules.players.asyncgetplayerinfo(steamname='Galaxy-Cluster') is Record
    player = await modules.players.asyncgetplayerinfo(steamname='Galaxy-Cluster')
    assert player['playername'] == 'admin'
    assert await len(modules.players.asyncgetplayerinfo(steamname='Galaxy-Cluster')) == 1
    assert await modules.players.asyncgetplayerinfo(steamname='galaxy-cluster') is Record
    assert await len(modules.players.asyncgetplayerinfo(steamname='galaxy-cluster')) == 1
