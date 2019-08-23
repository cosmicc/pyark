from modules.dbhelper import dbupdate
from modules.configreader import steamapikey
from urllib.request import urlopen, Request
import json
from loguru import logger as log


def fetchurldata(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urlopen(req).read()
    return json.loads(html)


@log.catch
def getsteaminfo(steamid):
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
        log.error(f'Error fetching steam api player data for [{steamid}]: {player}')
        return False
    else:
        log.debug(f'Updated steam API player information for steamid [{steamid}]')
        return player["personaname"]


@log.catch
def getsteambans(steamid):
    try:
        url = f'http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key={steamapikey}&steamids={steamid}'
        player = fetchurldata(url)['players'][0]
        if player['EconomyBan'] == 'none':
            economyban = False
        else:
            economyban = True
        dbupdate(f"""UPDATE players SET steamcommunityban = {player["CommunityBanned"]}, steamvacban = {player["VACBanned"]}, steamvacbannum = {player["NumberOfVACBans"]}, steamgamesbannum = {player["NumberOfGameBans"]}, steamlastbandays = {player["DaysSinceLastBan"]}, steameconomyban = {economyban} WHERE steamid = '{steamid}'""")
    except:
        log.error(f'Error fetching steam api ban data for [{steamid}]: {player}')
        return False
    else:
        log.debug(f'Updated Steam API ban information for steamid [{steamid}]')
        return True
