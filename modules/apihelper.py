import json
from datetime import timedelta
from time import sleep
from urllib.request import Request, urlopen

from loguru import logger as log
from modules.configreader import steamapikey
from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import Now


def stopsleep(sleeptime, stop_event, name):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug(f'{name} thread has ended')
            exit(0)
        sleep(1)


def fetcharkserverdata():
    hinst = dbquery('SELECT name from instances')
    for each in hinst:
        svrifo = dbquery("SELECT * from instances WHERE name = '%s'" % (each[0],), fetch='one')
        try:
            url = f'https://ark-servers.net/api/?object=servers&element=detail&key={svrifo[8]}'
            adata = fetchurldata(url)
        except:
            log.error(f'Error fetching ArkServers data from web')
        else:
            if adata is not None:
                dbupdate("UPDATE instances SET hostname = '%s', rank = '%s', score = '%s', uptime = '%s', votes = '%s' WHERE name = '%s'" % (adata['hostname'], adata['rank'], adata['score'], adata['uptime'], adata['votes'], each[0]))


def arkservernet_thread(dtime, stop_event):
    log.debug(f'ArkserversnetAPI thread is starting ')
    while not stop_event.is_set():
        fetcharkserverdata()
        stopsleep(dtime, stop_event, 'ArkserversnetAPI')
    log.debug(f'ArkservernetAPI thread has ended')
    exit(0)


@log.catch
def fetchauctiondata(steamid):
    try:
        url = f"https://linode.ghazlawl.com/ark/mods/auctionhouse/api/json/v1/auctions/?PlayerSteamID={steamid}"
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urlopen(req).read()
        data = data.decode().encode()
        adata = json.loads(data)
        auctions = adata['Auctions']
        log.trace(f'fetched auction data {data}')
        if auctions:
            return auctions
        else:
            return False
    except:
        return False


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
def writeauctionstats(steamid, numauctions, numitems, numdinos):
    dbupdate("UPDATE players SET totalauctions = '%s', itemauctions = '%s', dinoauctions = '%s' WHERE steamid = '%s'" % (numauctions, numitems, numdinos, steamid))


@log.catch
def fetchurldata(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urlopen(req).read()
    log.trace(f'fetch data retrieved {html}')
    return json.loads(html)


@log.catch
def getsteaminfo(steamid, playername):
    try:
        url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={steamapikey}&steamids={steamid}'
        player = fetchurldata(url)['response']['players'][0]
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
        dbupdate(f"""UPDATE players SET steamname = '{player["personaname"]}', steamrealname = '{realname}', steamlastlogoff = {lastlogoff}, steamcreated = {steamcreated}, steamcountry = '{steamcountry}' WHERE steamid = '{steamid}'""")
    except:
        log.warning(f'HTTP Error fetching steam api player data for [{playername}] ({steamid})')
        return False
    else:
        log.debug(f'Updated steam API player information for [{playername}] ({steamid})')
        return player["personaname"]


@log.catch
def getsteambans(steamid, playername):
    try:
        url = f'http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key={steamapikey}&steamids={steamid}'
        player = fetchurldata(url)['players'][0]
        if player['EconomyBan'] == 'none':
            economyban = False
        else:
            economyban = True
        dbupdate(f"""UPDATE players SET steamcommunityban = {player["CommunityBanned"]}, steamvacban = {player["VACBanned"]}, steamvacbannum = {player["NumberOfVACBans"]}, steamgamesbannum = {player["NumberOfGameBans"]}, steamlastbandays = {player["DaysSinceLastBan"]}, steameconomyban = {economyban} WHERE steamid = '{steamid}'""")
    except:
        log.warning(f'Error fetching steam api ban data for [{playername}] ({steamid})')
        return False
    else:
        log.debug(f'Updated Steam API ban information for [{playername}] ({steamid}])')
        return True


@log.catch
def steamapi_thread(dtime, stop_event):
    log.debug('SteamAPI thread is starting')
    while not stop_event.is_set():
        players = dbquery(f"SELECT steamid, playername, steamrefreshtime FROM players WHERE refreshsteam = True")
        if players:
            log.trace(f'Found {len(players)} players for steamapi to process {players}')
            for player in players:
                log.trace(f'processing player steamapi [{player[1]}] ({player[0]})')
                refresh = False
                if player[2]:
                    if player[2] < Now(fmt='dt') - timedelta(days=1):
                        log.trace(f'player [{player[1]}] is past steam refresh time')
                        refresh = True
                        rtime = Now(fmt='dt')
                    else:
                        rtime = player[2]
                else:
                    log.trace(f'no steamrefreshtime found for player [{player[1]}]')
                    refresh = True
                    rtime = Now(fmt='dt')
                dbupdate(f"UPDATE players SET refreshsteam = False, steamrefreshtime = '{rtime}' WHERE steamid = '{player[0]}'")
                log.trace(f'retrieving steam information for player [{player[1]}] ({player[0]}]')
                if refresh:
                    getsteaminfo(player[0], player[1])
                    getsteambans(player[0], player[1])
                sleep(5)  # slow downi the requests
        stopsleep(dtime, stop_event, 'SteamAPI')
    log.debug(f'SteamAPI thread has ended')
    exit(0)


@log.catch
def auctionapi_thread(dtime, stop_event):
    log.debug('AuctionAPI thread is starting')
    while not stop_event.is_set():
        players = dbquery(f"SELECT steamid, playername, auctionrefreshtime FROM players WHERE refreshauctions = True OR online = True")
        if players:
            log.trace(f'Found {len(players)} players for auctionapi to process {players}')
            for player in players:
                log.trace(f'processing player auctionapi [{player[1]}] ({player[0]})')
                refresh = False
                if player[2]:
                    if player[2] < Now(fmt='dt') - timedelta(hours=1):
                        log.trace(f'player [{player[1]}] is past auction refresh time')
                        refresh = True
                        rtime = Now(fmt='dt')
                    else:
                        rtime = player[2]
                else:
                    log.trace(f'no auctionrefreshtime found for player [{player[1]}]')
                    refresh = True
                    rtime = Now(fmt='dt')
                dbupdate(f"UPDATE players SET refreshauctions = False, auctionrefreshtime = '{rtime}' WHERE steamid = '{player[0]}'")
                if refresh:
                    log.debug(f'retrieving auction information for player [{player[1]}] ({player[0]}]')
                    pauctions = fetchauctiondata(player[0])
                    totauctions, iauctions, dauctions = getauctionstats(pauctions)
                    writeauctionstats(player[0], totauctions, iauctions, dauctions)
                    log.debug(f'retrieved auctions for player [{player[1]}] total: {totauctions}, items: {iauctions}, dinos: {dauctions}')
                stopsleep(5, stop_event, 'AuctionAPI')  # slow down the requests
        stopsleep(dtime, stop_event, 'AuctionAPI')
    log.debug(f'AuctionAPI thread has ended')
    exit(0)
