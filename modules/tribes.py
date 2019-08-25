from loguru import logger as log
from modules.dbhelper import dbupdate, dbquery


@log.catch
def putplayerintribe(tribeid, playername):
    tribeidb = dbquery(f"SELECT tribeid, players, tribename FROM tribes WHERE tribeid = '{tribeid}'", fetch='one')
    steamid = dbquery(f"SELECT steamid FROM players WHERE playername = '{playername.lower()}' AND online = True", fetch='one', single=True)
    if tribeidb and steamid:
        #log.info(f'tribeid: {tribeidb[0]}, {len(tribeidb)}  players: {type(tribeidb[1])} < {playername}')
        if tribeidb[1] is None:
            steamids = [steamid[0]]
            dbupdate(f"UPDATE tribes SET players = ARRAY{steamids} WHERE tribeid = '{tribeidb[0]}'")
            log.info(f'Adding [{playername}] to first player in database tribe [{tribeidb[2]}]')
        elif isinstance(tribeidb[1], list):
            if steamid[0] not in tribeidb[1]:
                log.debug(f'existing players: {tribeidb[1]}')
                steamids = tribeidb[1].append(steamid[0])
                dbupdate(f"UPDATE tribes SET players = ARRAY{steamids} WHERE tribeid = '{tribeidb[0]}'")
                log.info(f'Adding [{playername}] as additional player to database tribe [{tribeidb[2]}]')
        else:
            log.info('shouldnt go this far')


@log.catch
def getplayertribes(steamid):
    tribe = dbquery(f"SELECT tribename, server FROM tribes WHERE '{steamid}'=ANY(players)", fetch='all')
    return tribe

