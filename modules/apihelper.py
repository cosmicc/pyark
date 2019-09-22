import json
from datetime import timedelta

import asyncio
from loguru import logger as log
from modules.asyncdb import DB as db
from modules.configreader import steamapikey
from modules.redis import globalvar
from modules.timehelper import Now


async def asyncarkserverdatafetcher(session):
    instances = await globalvar.getlist('allinstances')
    for inst in instances:
        svrifo = await db.fetchone(f"SELECT * from instances WHERE name = '{inst}'")
        try:
            url = f'https://ark-servers.net/api/?object=servers&element=detail&key={svrifo["arkservernet"]}'
            adata = await asyncfetchurldata(session, url)
        except:
            log.error(f'Error fetching ArkServers data from web')
        else:
            log.trace(f'Updated ArkServerNet API information for [{inst}]')
            if adata is not None:
                await db.update("UPDATE instances SET hostname = '%s', rank = '%s', score = '%s', uptime = '%s', votes = '%s' WHERE name = '%s'" % (adata['hostname'], adata['rank'], adata['score'], adata['uptime'], adata['votes'], inst))
        await asyncio.sleep(5)


@log.catch
async def asyncfetchauctiondata(session, steamid, playername):
    try:
        url = f"https://linode.ghazlawl.com/ark/mods/auctionhouse/api/json/v1/auctions/?PlayerSteamID={steamid}"
        data = await asyncfetchurldata(session, url)
        auctions = data['Auctions']
        log.trace(f'fetched auction data {data}')
        log.debug(f'Updated Auction API player information for [{playername}] ({steamid})')
        if auctions:
            return auctions
        else:
            return (0, 0, 0)
    except:
        log.error(f'error fetching auction information for [{playername}]')


@log.catch
def getauctionstats(auctiondata):
    if auctiondata:
        numdinos = 0
        numitems = 0
        numauctions = len(auctiondata)
        for eauct in auctiondata:
            if eauct['Type'] == 'Dino':
                numdinos += 1
            elif eauct['Type'] == 'Item':
                numitems += 1
        return numauctions, numitems, numdinos
    else:
        return 0, 0, 0


@log.catch
async def asyncwriteauctionstats(steamid, numauctions, numitems, numdinos):
    await db.update("UPDATE players SET totalauctions = '%s', itemauctions = '%s', dinoauctions = '%s' WHERE steamid = '%s'" % (numauctions, numitems, numdinos, steamid))


@log.catch
async def asyncfetchurldata(session, url):
    async with session.get(url) as response:
        html = await response.text()
        log.trace(f'fetch data retrieved {html}')
        try:
            return json.loads(html)
        except json.decoder.JSONDecodeError:
            log.error(f'fetchurldata error [{html}]')


@log.catch
async def getsteaminfo(steamid, playername, session):
    try:
        url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={steamapikey}&steamids={steamid}'
        player = await asyncfetchurldata(session, url)
        player = player['response']['players'][0]
        if 'loccountrycode' in player:
            steamcountry = player['loccountrycode']
        else:
            steamcountry = 'None'
        if 'realname' in player:
            realname = player['realname']
        else:
            realname = 'None'
        if 'steamcreated' in player:
            steamcreated = player['steamcreated']
        else:
            steamcreated = 0
        if 'lastlogoff' in player:
            lastlogoff = player['lastlogoff']
        else:
            lastlogoff = 0
        await db.update(f"""UPDATE players SET steamname = '{player["personaname"]}', steamrealname = '{realname}', steamlastlogoff = {lastlogoff}, steamcreated = {steamcreated}, steamcountry = '{steamcountry}' WHERE steamid = '{steamid}'""")
    except:
        log.exception(f'HTTP Error fetching steam api player data for [{playername}] ({steamid})')
        return False
    else:
        log.debug(f'Updated steam API player information for [{playername}] ({steamid})')
        return True


@log.catch
async def getsteambans(steamid, playername, session):
    try:
        url = f'http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key={steamapikey}&steamids={steamid}'
        player = await asyncfetchurldata(session, url)
        player = player['players'][0]
        if player['EconomyBan'] == 'none':
            economyban = False
        else:
            economyban = True
        await db.update(f"""UPDATE players SET steamcommunityban = {player["CommunityBanned"]}, steamvacban = {player["VACBanned"]}, steamvacbannum = {player["NumberOfVACBans"]}, steamgamesbannum = {player["NumberOfGameBans"]}, steamlastbandays = {player["DaysSinceLastBan"]}, steameconomyban = {economyban} WHERE steamid = '{steamid}'""")
    except:
        log.exception(f'Error fetching steam api ban data for [{playername}] ({steamid})')
        return False
    else:
        log.debug(f'Updated Steam API ban information for [{playername}] ({steamid}])')
        return True


@log.catch
async def asyncsteamapifetcher(session):
    players = await db.fetchall(f"SELECT steamid, playername, steamrefreshtime FROM players WHERE refreshsteam = True")
    if players:
        log.trace(f'Found {len(players)} players for steamapi to process {players}')
        for player in players:
            log.trace(f'processing player steamapi [{player["playername"]}] ({player["steamid"]})')
            refresh = False
            if player['steamrefreshtime']:
                if player['steamrefreshtime'] < Now(fmt='dt') - timedelta(days=1):
                    log.trace(f'player [{player["playername"]}] is past steam refresh time')
                    refresh = True
                    rtime = Now(fmt='dt')
                else:
                    rtime = player['steamrefreshtime']
            else:
                log.trace(f'no steamrefreshtime found for player [{player["playername"]}]')
                refresh = True
                rtime = Now(fmt='dt')
            await db.update(f"UPDATE players SET refreshsteam = False, steamrefreshtime = '{rtime}' WHERE steamid = '{player[0]}'")
            log.trace(f'retrieving steam information for player [{player["playername"]}] ({player["steamid"]}]')
            if refresh:
                await getsteaminfo(player["steamid"], player["playername"], session)
                await getsteambans(player["steamid"], player["playername"], session)
            await asyncio.sleep(2)  # slow downi the requests


@log.catch
async def asyncauctionapifetcher(session):
    players = await db.fetchall(f"SELECT steamid, playername, auctionrefreshtime FROM players WHERE refreshauctions = True OR online = True")
    if players:
        log.trace(f'Found {len(players)} players for auctionapi to process {players}')
        for player in players:
            log.trace(f"processing player auctionapi [{player['playername']}] ({player['steamid']})")
            refresh = False
            if player['auctionrefreshtime']:
                if player['auctionrefreshtime'] < Now(fmt='dt') - timedelta(hours=1):
                    log.trace(f"player [{player['playername']}] is past auction refresh time")
                    refresh = True
                    rtime = Now(fmt='dt')
                else:
                    rtime = player['auctionrefreshtime']
            else:
                log.trace(f"no auctionrefreshtime found for player [{player['playername']}]")
                refresh = True
                rtime = Now(fmt='dt')
            await db.update(f"UPDATE players SET refreshauctions = False, auctionrefreshtime = '{rtime}' WHERE steamid = '{player[0]}'")
            if refresh:
                log.debug(f"retrieving auction information for player [{player['playername']}] ({player['steamid']}]")
                pauctions = await asyncfetchauctiondata(session, player['steamid'], player['playername'])
                totauctions, iauctions, dauctions = getauctionstats(pauctions)
                await asyncwriteauctionstats(player['steamid'], totauctions, iauctions, dauctions)
                log.debug(f"retrieved auctions for player [{player['playername']}] total: {totauctions}, items: {iauctions}, dinos: {dauctions}")
            await asyncio.sleep(5)
