from loguru import logger as log
from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import Now
from modules.servertools import removerichtext


@log.catch
def putplayerintribe(tribeid, playername):
    tribeid = dbquery(f"SELECT tribeid, players FROM tribes WHERE tribeid = '{tribeid}'", fetch='one')
    steamid = dbquery(f"SELECT steamid FROM players WHERE playername = '{playername.lower()}' AND online = True", fetch='one', single=True)
    if tribeid and steamid:
        log.info(f'tribeid: {tribeid[0]}, {len(tribeid)}  players: {type(tribeid[1])} < {playername}')
        if tribeid[1] is None:
            dbupdate(f"UPDATE tribes SET players = array_cat(players, {steamid[0]}) WHERE tribeid = '{tribeid[0]}'")
            log.info(f'Adding [{playername}] to tribe db [tribename]')
        elif tribeid[1] is list:
            if playername.lower() not in tribeid[1]:
                dbupdate(f"UPDATE tribes SET players = array_cat(players, {steamid[0]}) WHERE tribeid = '{tribeid[0]}'")
                log.info(f'Adding [{playername}] to tribe db [{tribename}]')


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


@log.catch
def processgameline(inst, ptype, line):
        clog = log.patch(lambda record: record["extra"].update(instance=inst))
        logheader = f'{Now(fmt="dt").strftime("%a %I:%M%p")}|{inst.upper():>8}|{ptype:<7}| '
        linesplit = removerichtext(line[21:]).split(", ")
        if ptype == 'TRAP':
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            msgsplit = linesplit[2][10:].split('trapped:')
            playername = msgsplit[0].strip()
            putplayerintribe(tribeid, playername)
            dino = msgsplit[1].strip().replace(')', '').replace('(', '')
            clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) has trapped [{dino}]')
        elif ptype == 'RELEASE':
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            msgsplit = linesplit[2][10:].split('released:')
            playername = msgsplit[0].strip()
            putplayerintribe(tribeid, playername)
            dino = msgsplit[1].strip().replace(')', '').replace('(', '')
            clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) has released [{dino}]')
        elif ptype == 'DEATH':
            log.debug(f'DEATH: {linesplit[0]}')
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            if tribename is None:
                deathsplit = removerichtext(line[21:]).split(" - ", 1)
                playername = deathsplit[0].strip()
                if deathsplit[1].find('was killed by') != -1:
                    killedby = deathsplit[1].split('was killed by')[1].strip()[:-1].replace('()', '').strip()
                    playerlevel = deathsplit[1].split('was killed by')[0].strip().replace('()', '')
                    clog.log(ptype, f'{logheader}[{playername.title()}] {playerlevel} was killed by [{killedby}]')
                elif deathsplit[1].find('killed!') != -1:
                    level = deathsplit[1].split(' was killed!')[0].strip('()')
                    clog.log(ptype, f'{logheader}[{playername.title()}] {level} has been killed')
                else:
                    log.warning(f'not found gameparse death: {deathsplit}')
            else:
                log.info(f'deathskip: {linesplit}')
        elif ptype == 'TAME':
                tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
                if tribename is None:
                    tamed = linesplit[0].split(' Tamed ')[1].strip(')').strip('!')
                    clog.log(ptype, f'{logheader}A tribe has tamed [{tamed}]')
                else:
                    log.debug(f'TRIBETAME: {inst}, {linesplit}')
                    playername = linesplit[2][10:].split(' Tamed')[0].strip()
                    putplayerintribe(tribeid, playername)
                    tamed = linesplit[2].split(' Tamed')[1].strip(')').strip('!').strip()
                    if playername.title() == 'Your Tribe':
                        clog.log(ptype, f'{logheader}[{tribename}] tamed [{tamed}]')
                    else:
                        clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) tamed [{tamed}]')
        elif ptype == 'DEMO':
                tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
                if tribename is None:
                    clog.log(ptype, f'{logheader}SINGLDEMO: [{linesplit}]')
                else:
                    log.debug(f'TRIBEDEMO: {inst}, {linesplit}')
                    playername = linesplit[2][10:].split(' demolished a ')[0].strip()
                    putplayerintribe(tribeid, playername)
                    demoitem = linesplit[2].split(' demolished a ')[1].replace("'", "").strip(')').strip('!').strip()
                    clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) demolished a [{demoitem}]')
 
        elif ptype == 'DECAY':
            log.debug(f'{inst}, {ptype}, {linesplit}')
            clog.log(ptype, f'{line} ## {linesplit}')
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            decayitem = linesplit[2].split("'", 1)[1].split("'")[0]
            # decayitem = re.search('\(([^)]+)', linesplit[2]).group(1)
            clog.log(ptype, f'{logheader}{tribename} {decayitem}')
            # wglog(inst, removerichtext(line[21:]))
        elif ptype == 'CLAIM':
            log.debug(f'{inst}, {ptype}, {linesplit}')
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            if tribename:
                playername = linesplit[2][10:].split(' claimed ')[0].strip()
                putplayerintribe(tribeid, playername)
                claimitem = linesplit[2].split("'", 1)[1].split("'")[0]
            # decayitem = re.search('\(([^)]+)', linesplit[2]).group(1)
                clog.log(ptype, f'{logheader} [{playername}] ({tribename}) has claimed [{claimitem}]')
            else:
                clog.log(ptype, f'{logheader} SINGLECLAIM: {linesplit}')
 
        else:
            log.debug(f'UNKNOWN: {inst}, {ptype}, {linesplit}')
            clog.log(ptype, f'{linesplit}')
            # wglog(inst, removerichtext(line[21:]))
