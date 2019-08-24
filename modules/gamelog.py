from loguru import logger as log
from modules.timehelper import Now
from modules.servertools import removerichtext
import re


@log.catch
def gettribeinfo(linesplit):
    if len(linesplit) == 3 and linesplit[0].strip().startswith('Tribe'):
        tribename = linesplit[0][6:].strip()
        if linesplit[1].strip().startswith('ID'):
            tribeid = linesplit[1].split(':')[0][3:].strip()
            log.debug(f'Got tribe information for tribe [{tribename}] id [{tribeid}]')
        return tribename
    else:
        return None


@log.catch
def processgameline(inst, ptype, line):
        clog = log.patch(lambda record: record["extra"].update(instance=inst))
        logheader = f'{Now(fmt="dt").strftime("%a %I:%M%p")}|{inst.upper():>8}|{ptype:<7}| '
        linesplit = removerichtext(line[21:]).split(", ")
        if ptype == 'TRAP':
            tribename = gettribeinfo(linesplit)
            msgsplit = linesplit[2][10:].split('trapped:')
            playername = msgsplit[0].strip()
            dino = msgsplit[1].strip().replace(')', '').replace('(', '')
            clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) has trapped [{dino}]')
            # wglog(inst, f'{Now(fmt="string")}: [{playername.title()}] has trapped [{dino}]')
        elif ptype == 'RELEASE':
            tribename = gettribeinfo(linesplit)
            msgsplit = linesplit[2][10:].split('released:')
            playername = msgsplit[0].strip()
            dino = msgsplit[1].strip().replace(')', '').replace('(', '')
            clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) has released [{dino}]')
            # wglog(inst, f'{Now(fmt="string")}: [{playername.title()}] has released [{dino}]')
        elif ptype == 'DEATH':
            log.debug(f'DEATH: {linesplit[0]}')
            tribename = gettribeinfo(linesplit)
            playername = linesplit[2][21:].split('-', 1)[0].strip()
            # clog.log(ptype, f'tribe information collected for [{tribename}]')
           if tribename is None:
                deathsplit = removerichtext(line[21:]).split(" - ", 1)
                playername = deathsplit[0].strip()
                if deathsplit[1].find('was killed by') != -1:
                    killedby = deathsplit[1].split('was killed by')[1].strip()[:-1].replace('()', '').strip()
                    playerlevel = deathsplit[1].split('was killed by')[0].strip().replace('()', '')
                    clog.log(ptype, f'{logheader}[{playername.title()}] {playerlevel} was killed by [{killedby}]')
                    # wglog(inst, f'{Now(fmt="string")}: [{playername.title()}] {playerlevel} was killed by [{killedby}]')
                elif deathsplit[1].find('killed!') != -1:
                    clog.log(ptype, f'{logheader}[{playername.title()}] has been killed')
                    log.info(f'dt: {deathsplit}')
                    # wglog(inst, f'{Now(fmt="string")}: [{playername.title()}] has died')
                else:
                    log.warning(f'not found gameparse death: {deathsplit}')
        elif ptype == 'TAME':
                tribename = gettribeinfo(linesplit)
                if tribename is None:
                    tamed = linesplit[0].split(' Tamed ')[1].strip(')').strip('!')
                    clog.log(ptype, f'{logheader}A tribe has tamed [{tamed}]')
                else:
                    log.debug(f'TRIBETAME: {inst}, {linesplit}')
                    playername = linesplit[2][10:].split(' Tamed')[0].strip()
                    tamed = linesplit[2].split(' Tamed')[1].strip(')').strip('!').strip()
                    if playername.title() == 'Your Tribe':
                        clog.log(ptype, f'{logheader}[{tribename}] tamed [{tamed}]')
                    else:
                        clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) tamed [{tamed}]')
        elif ptype == 'DECAY':
            log.debug(f'{inst}, {ptype}, {linesplit}')
            clog.log(ptype, f'{line} ## {linesplit}')
            tribename = gettribeinfo(linesplit)
            decayitem = linesplit[2].split("'", 1)[1].split("'")[0]
            # decayitem = re.search('\(([^)]+)', linesplit[2]).group(1)
            clog.log(ptype, f'{logheader}{tribename} {decayitem}')
            # wglog(inst, removerichtext(line[21:]))
        elif ptype == 'CLAIM':
            log.debug(f'{inst}, {ptype}, {linesplit}')
            tribename = gettribeinfo(linesplit)
            playername = linesplit[2][10:].split(' claimed ')[0].strip()
            claimitem = linesplit[2].split("'", 1)[1].split("'")[0]
            # decayitem = re.search('\(([^)]+)', linesplit[2]).group(1)
            clog.log(ptype, f'{logheader} [{playername}] ({tribename}) has claimed [{claimitem}]')
 
        else:
            log.debug(f'UNKNOWN: {inst}, {ptype}, {linesplit}')
            clog.log(ptype, f'{linesplit}')
            # wglog(inst, removerichtext(line[21:]))
