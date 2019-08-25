from loguru import logger as log
from modules.dbhelper import dbupdate, dbquery
from modules.timehelper import Now


@log.catch
def putplayerintribe(tribeid, playername):
    tribeidb = dbquery(f"SELECT tribeid, players, tribename FROM tribes WHERE tribeid = '{tribeid}'", fetch='one')
    steamid = dbquery(f"SELECT steamid FROM players WHERE playername = '{playername.lower()}' AND online = True", fetch='one', single=True)
    if tribeidb and steamid:
        log.debug(f'tribeid: {tribeidb[0]}, {len(tribeidb)}  players: {type(tribeidb[1])} < {playername}')
        if tribeidb[1] is None:
            steamids = [steamid[0]]
            dbupdate(f"UPDATE tribes SET players = ARRAY{steamids} WHERE tribeid = '{tribeidb[0]}'")
            log.info(f'Adding [{playername}] to first player in database tribe [{tribeidb[2]}]')
        elif isinstance(tribeidb[1], list):
            if steamid[0] not in tribeidb[1]:
                tribeidb[1].append(steamid[0])
                log.debug(f'existing players new: {tribeidb[1]}')
                dbupdate(f"UPDATE tribes SET players = ARRAY{tribeidb[1]} WHERE tribeid = '{tribeidb[0]}'")
                log.info(f'Adding [{playername}] as additional player to database tribe [{tribeidb[2]}]')
        else:
            log.info('shouldnt go this far')


@log.catch
def getplayertribes(steamid):
    tribe = dbquery(f"SELECT tribename, server FROM tribes WHERE '{steamid}'=ANY(players)", fetch='all')
    return tribe


@log.catch
def gettribeinfo(linesplit, inst, ptype):
    if len(linesplit) == 3 and linesplit[0].strip().startswith('Tribe'):
        tribename = linesplit[0][6:].strip()
        if linesplit[1].strip().startswith('ID'):
            tribeid = linesplit[1].split(':')[0][3:].strip()
            indb = dbquery(f"SELECT tribeid from tribes where tribeid = '{tribeid}'", fetch='one', single=True)
            if not indb:
                dbupdate(f"INSERT INTO tribes (tribename, tribeid, server) VALUES ('{tribename}', '{int(tribeid)}', '{inst}')")
            if ptype != 'DECAY' or ptype != 'DEATH':
                dbupdate(f"""UPDATE tribes SET lastseen = '{Now(fmt="dt")}' WHERE tribeid = '{tribeid}'""")

            log.debug(f'Got tribe information for tribe [{tribename}] id [{tribeid}]')
            return tribename, tribeid
        else:
            return None, None
    else:
        return None, None
