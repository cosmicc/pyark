from modules.configreader import psql_host, psql_port, psql_user, psql_pw, gamelogfile
from loguru import logger as log
from modules.dbhelper import dbupdate
from modules.timehelper import Now
from modules.servertools import removerichtext
from modules.players import isplayeradmin
from modules.tribes import putplayerintribe, removeplayerintribe, gettribeinfo
import psycopg2
from time import sleep
import json
import modules.logging
from modules.processlock import plock
from os import nice, _exit
import signal

__name__ = "gamelogger"


def sig_handler(signal, frame):
    log.log('EXIT', f'Termination signal {signal} recieved. Exiting.')
    gl.close()
    _exit(0)


signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGHUP, sig_handler)
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGQUIT, sig_handler)


def checkgamelog(record):
    if record['level'] == 'TRAP' or record['level'] == 'ADMIN' or record['level'] == 'DEATH' or record['level'] == 'TAME' or record['level'] == 'DECAY' or record['level'] == 'DEMO' or record['level'] == 'TRIBE' or record['level'] == 'CLAIM' or record['level'] == 'RELEASE':
        return True
    else:
        return False


log.add(sink=gamelogfile, level=3, buffering=1, enqueue=True, backtrace=False, diagnose=False, serialize=False, colorize=True, format=modules.logging.gamelogformat, delay=False, filter=checkgamelog)


plock()

nice(19)


@log.catch
class GameLogger():
    def __init__(self):
        try:
            self.conn = psycopg2.connect(dbname='gamelog', user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
            self.c = self.conn.cursor()
        except psycopg2.OperationalError:
            log.critical('ERROR CONNECTING TO DATABASE SERVER')
            sleep(60)
        except:
            log.error(f'Error in database init: gamelogdb')

    def getlines(self):
        try:
            self.c.execute("SELECT * FROM gamelog")
            result = self.c.fetchall()
            for eline in result:
                self.c.execute(f"DELETE FROM gamelog WHERE id = {eline[0]}")
                self.conn.commit()
            return result
        except:
            log.error('Error in getlines() gamelog line retriever from db')

    def process(self):
        lines = self.getlines()
        if lines:
            for line in lines:
                data = self.convertline(line[1])
                processgameline(data['record']['extra']['instance'].lower(), data['record']['level']['name'].upper(), data['text'])

    def close(self):
        self.c.close()
        self.conn.close()


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
            clog.debug(f'{ptype} - {linesplit}')
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
                log.debug(f'deathskip: {linesplit}')
        elif ptype == 'TAME':
                clog.debug(f'{ptype} - {linesplit}')
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
                clog.debug(f'{ptype} - {linesplit}')
                tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
                if tribename is None:
                    clog.log(ptype, f'{logheader}SINGLDEMO: [{linesplit}]')
                else:
                    log.debug(f'TRIBEDEMO: {inst}, {linesplit}')
                    playername = linesplit[2][10:].split(' demolished a ')[0].strip()
                    putplayerintribe(tribeid, playername)
                    if len(linesplit[2].split(' demolished a ')) > 0 and linesplit[2].find(' demolished a ') != -1:
                        demoitem = linesplit[2].split(' demolished a ')[1].replace("'", "").strip(')').strip('!').strip()
                        clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) demolished a [{demoitem}]')
        elif ptype == 'ADMIN':
                clog.debug(f'{ptype} - {linesplit}')
                steamid = linesplit[2].strip()[9:].strip(')')
                pname = linesplit[0].split('PlayerName: ')[1]
                cmd = linesplit[0].split('AdminCmd: ')[1].split(' (PlayerName:')[0].upper()
                if not isplayeradmin(steamid):
                    clog.warning(f'{logheader}Admin command [{cmd}] executed by NON-ADMIN [{pname.title()}] !')
                    dbupdate("INSERT INTO kicklist (instance,steamid) VALUES ('%s','%s')" % (inst, steamid))
                    dbupdate("UPDATE players SET banned = 'true' WHERE steamid = '%s')" % (steamid, ))
                else:
                    clog.log(ptype, f'{logheader}[{pname.title()}] executed admin command [{cmd}] ')
        elif ptype == 'DECAY':
            clog.debug(f'{ptype} - {linesplit}')
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            decayitem = linesplit[2].split("'", 1)[1].split("'")[0]
            # decayitem = re.search('\(([^)]+)', linesplit[2]).group(1)
            clog.log(ptype, f'{logheader}Tribe ({tribename}) auto-decayed [{decayitem}]')
            # wglog(inst, removerichtext(line[21:]))
        elif ptype == 'CLAIM':
            log.debug(f'{ptype} : {linesplit}')
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            if tribename:
                if linesplit[2].find(" claimed '") != -1:
                    playername = linesplit[2][10:].split(' claimed ')[0].strip()
                    putplayerintribe(tribeid, playername)
                    claimitem = linesplit[2].split("'", 1)[1].split("'")[0]
                    clog.log(ptype, f'{logheader}[{playername}] of ({tribename}) has claimed [{claimitem}]')
                elif linesplit[2].find(" unclaimed '") != -1:
                    playername = linesplit[2][10:].split(' claimed ')[0].strip()
                    putplayerintribe(tribeid, playername)
                    claimitem = linesplit[2].split("'", 1)[1].split("'")[0]
                    clog.log(ptype, f'{logheader}[{playername}] of ({tribename}) has un-claimed [{claimitem}]')
            else:
                clog.log(ptype, f'{logheader} SINGLECLAIM: {linesplit}')
        elif ptype == 'TRIBE':
            clog.debug(f'{ptype} - {linesplit}')
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            if tribeid is not None:
                if linesplit[2].find(' was added to the Tribe by ') != -1:
                    playername = linesplit[2][10:].split(' was added to the Tribe by ')[0].strip()
                    playername2 = linesplit[2][10:].split(' was added to the Tribe by ')[1].strip().strip(')').strip('!')
                    putplayerintribe(tribeid, playername)
                    putplayerintribe(tribeid, playername2)
                    clog.log(ptype, f'[{playername.title()}] was added to Tribe ({tribename}) by [{playername2.title()}]')
                elif linesplit[2].find(' was removed from the Tribe!') != -1:
                    playername = linesplit[2][10:].split(' was removed from the Tribe!')[0].strip()
                    removeplayerintribe(tribeid, playername)
                    clog.log(ptype, f'[{playername.title()}] was removed from Tribe ({tribename})')
                elif linesplit[2].find(' was added to the Tribe!') != -1:
                    playername = linesplit[2][10:].split(' was added to the Tribe!')[0].strip()
                    putplayerintribe(tribeid, playername)
                    clog.log(ptype, f'[{playername.title()}] was added to the Tribe ({tribename})')
                elif linesplit[2].find(' set to Rank Group ') != -1:
                    playername = linesplit[2][10:].split(' set to Rank Group ')[0].strip()
                    putplayerintribe(tribeid, playername)
                    rankgroup = linesplit[2][10:].split(' set to Rank Group ')[1].strip().strip('!')
                    clog.log(ptype, f'[{playername.title()}] set to rank group [{rankgroup}] in Tribe ({tribename})')
            else:
                clog.log(ptype, f'{logheader}{linesplit}')
        else:
            log.debug(f'UNKNOWN {ptype} - {linesplit}')
            clog.log(ptype, f'{linesplit}')


if __name__ == 'gamelogger':
    gl = GameLogger()
    while True:
        try:
            gl.process()
            sleep(1)
        except KeyboardInterrupt:
            log.critical(f'Keyboard Interrupt termination recieved. Exiting.')
            gl.close()
            _exit(0)
        except:
            log.exception(f'Exception in Pyark Main Routine! Exiting')
            gl.close()
            _exit(1)
