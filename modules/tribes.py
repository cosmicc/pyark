from loguru import logger as log
from modules.dbhelper import dbupdate, dbquery
from modules.timehelper import Now


@log.catch
def putplayerintribe(tribeid, playername):
    tribeidb = dbquery(f"SELECT tribeid, players, tribename FROM tribes WHERE tribeid = '{tribeid}'", fetch='one')
    steamid = dbquery(f"SELECT steamid FROM players WHERE playername = '{playername.lower()}' AND online = True", fetch='one', single=True)
    if tribeidb and steamid:
        log.trace(f'tribeid: {tribeidb[0]}, {len(tribeidb)}  players: {type(tribeidb[1])} < {playername}')
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
    tribes = dbquery(f"SELECT * FROM tribes WHERE '{steamid}'=ANY(players)", fmt='dict', fetch='all')
    return tribes


@log.catch
def gettribesplayers(tribeid, fmt='steamids'):
    players = dbquery(f"SELECT players FROM tribes WHERE tribeid = '{tribeid}'", fetch='one', single=True)
    if players[0] is not None:
        if fmt == 'steamids':
            return players[0]
        elif fmt == 'names' or fmt == 'playernames':
            playerlist = ''
            for player in players[0]:
                playername = dbquery(f"SELECT playername FROM players WHERE steamid = '{player}'", fetch='one', single=True)
                if playerlist == '':
                    playerlist = playername[0]
                else:
                    playerlist = playerlist + f', {playername[0]}'
            return playerlist
        else:
            return None
    else:
        return None


@log.catch
def gettribeinfo(linesplit, inst, ptype):
    if len(linesplit) == 3 and linesplit[0].strip().startswith('Tribe'):
        tribename = linesplit[0][6:].strip()
        if linesplit[1].strip().startswith('ID'):
            tribeid = linesplit[1].split(':')[0][3:].strip()
            indb = dbquery(f"SELECT tribeid from tribes where tribeid = '{tribeid}'", fetch='one', single=True)
            if not indb:
                dbupdate(f"INSERT INTO tribes (tribename, tribeid, server) VALUES ('{tribename}', '{int(tribeid)}', '{inst}')")
            if ptype != 'DECAY' and ptype != 'DEATH':
                dbupdate(f"""UPDATE tribes SET lastseen = '{Now(fmt="dt")}' WHERE tribeid = '{tribeid}'""")

            log.debug(f'Got tribe information for tribe [{tribename}] id [{tribeid}]')
            return tribename, tribeid
        else:
            return None, None
    else:
        return None, None


@log.catch
def gettribes():
    tribes = dbquery(f"SELECT * FROM tribes ORDER BY tribename DESC", fetch='all', fmt='dict', single=True)
    return tribes


@log.catch
def gettribesreport():
    tribes = dbquery(f"SELECT * FROM tribes ORDER BY lastseen DESC", fetch='all', fmt='dict', single=True)
    for tribe in tribes:
        players = gettribesplayers(tribe['tribeid'], fmt='playernames')
        print(f"Tribe: {tribe['tribename']} ({tribe['tribeid']}) of {tribe['server']} Lastseen: {tribe['lastseen']} Players: {players}")
