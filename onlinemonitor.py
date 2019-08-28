from modules.auctionhelper import fetchauctiondata, getauctionstats, writeauctionstats
from clusterevents import iseventtime, getcurrenteventinfo
from modules.dbhelper import dbquery, dbupdate, cleanstring
from modules.players import getplayer, newplayer
from modules.timehelper import elapsedTime, playedTime, Now
from modules.servertools import serverexec
from modules.steamapi import getsteaminfo, getsteambans
from loguru import logger as log
import threading
from time import sleep

welcomthreads = []
greetthreads = []

global instance


@log.catch
def resetplayerbit(steamid):
    dbupdate("UPDATE players SET restartbit = 0 WHERE steamid = '%s'" % (steamid,))


@log.catch
def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,), fetch='one')
    elif whos == "ALERT" or isindb:
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                 (inst, whos, msg, tstamp))


@log.catch
def iswelcoming(steamid):
    for each in welcomthreads:
        if each['steamid'] == steamid:
            if each['sthread'].is_alive():
                return True
            else:
                return False


@log.catch
def isgreeting(steamid):
    for each in greetthreads:
        if each['steamid'] == steamid:
            if each['gthread'].is_alive():
                return True
            else:
                return False


@log.catch
def serverisinrestart(steamid, inst, oplayer):
    rbt = dbquery("SELECT * FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if rbt[3] == "True":
        log.log('UPDATE', f'Notifying player [{oplayer[1].title()}] that [{inst.title()}] will be restarting in {rbt[7]} min')
        mtxt = f'WARNING: server is restarting in {rbt[7]} minutes for a {rbt[5]}'
        serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@''{inst}'], nice=19, null=True)


@log.catch
def isinlottery(steamid):
    isinlotto = dbquery("SELECT * FROM lotteryinfo WHERE winner = 'Incomplete'", fetch='one')
    if isinlotto:
        isinlotto2 = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (steamid,), fetch='one')
        if isinlotto2:
            return True
        else:
            return False
    else:
        return True


@log.catch
def lottodeposits(steamid, inst):
    lottocheck = dbquery("SELECT * FROM lotterydeposits WHERE steamid = '%s'" % (steamid,))
    elpinfo = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid,), fetch='one')
    if lottocheck and inst == elpinfo[15]:
        for weach in lottocheck:
            if weach[4] == 1:
                log.log('POINTS', f'{weach[3]} lottery win points added to [{elpinfo[1].title()}]')
                msg = f'{weach[3]} Reward points have been deposited into your account for a lottery win!'
                serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {msg}', f'@{inst}'], nice=19, null=True)
                serverexec(['arkmanager', 'rconcmd', f'ScriptCommand tcsar addarctotal {steamid} {int(weach[3])}', f'@{inst}'], nice=19, null=True)
            elif weach[4] == 0:
                log.log('POINTS', f'{weach[3]} lottery entry points removed from [{elpinfo[1].title()}]')
                msg = f'{weach[3]} Reward points have been withdrawn from your account for a lottery entry'
                serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {msg}', f'@{inst}'], nice=19, null=True)
                serverexec(['arkmanager', 'rconcmd', f'ScriptCommand tcsar setarctotal {steamid} {int(elpinfo[5]) - int(weach[3])}', f'@{inst}'], nice=19, null=True)
        dbupdate("DELETE FROM lotterydeposits WHERE steamid = '%s'" % (steamid,))


@log.catch
def checkifbanned(steamid):
    oplayer = dbquery("SELECT steamid FROM players WHERE steamid = '%s' AND banned != ''" % (steamid,), fetch='one')
    bplayer = dbquery("SELECT steamid FROM banlist WHERE steamid = '%s'" % (steamid,), fetch='one')
    if oplayer or bplayer:
        return True
    else:
        return False


@log.catch
def playergreet(steamid, steamname, inst):
    global greetthreads
    global welcomthreads
    gogo = 0
    xferpoints = 0
    if checkifbanned(steamid):
        log.warning(f'BANNED player [{steamname}] [{steamid}] has tried to connect or is online on [{inst.title()}]. kicking and banning.')
        serverexec(['arkmanager', 'rconcmd', f'kickplayer {steamid}', f'@{inst}'], nice=5, null=True)
        # subprocess.run("""arkmanager rconcmd 'banplayer %s' @%s""" % (steamid, inst), shell=True)
    else:
        oplayer = getplayer(steamid)
        if not oplayer:
            welcom = threading.Thread(name='welcoming-%s' % steamid, target=newplayer, args=(steamid, steamname, inst))
            welcom.start()
        else:
            if oplayer[16] != 0 and oplayer[15] == inst:
                xferpoints = int(oplayer[16])
                log.log('POINTS', f'Transferred {xferpoints} non-home server points for \
[{oplayer[1].title()}] on [{inst.title()}]')
                dbupdate("UPDATE players SET transferpoints = 0 WHERE steamid = '%s'" % (steamid,))
                serverexec(['arkmanager', 'rconcmd', f'ScriptCommand tcsar addarctotal {steamid} {xferpoints}', f'@{inst}'], nice=19, null=True)
            if Now() - int(oplayer[2]) < 300:  # existing online player
                log.trace(f'Existing online player [{oplayer[1].title()}] was found on [{inst.title()}]. updating info.')
                dbupdate("UPDATE players SET online = True, lastseen = '%s', server = '%s' WHERE steamid = '%s'" % (Now(), inst, steamid))
            else:  # new player connection
                log.debug(f'New online player [{oplayer[1].title()}] was found on [{inst.title()}]. updating info.')
                steamname = getsteaminfo(steamid)
                getsteambans(steamid)
                if not steamname:
                    dbupdate("UPDATE players SET online = True, lastseen = %s, server = '%s', connects = %s WHERE steamid = '%s'" % (Now(), inst, int(oplayer[7]) + 1, steamid))
                else:
                    dbupdate("UPDATE players SET online = True, lastseen = %s, server = '%s', connects = %s, steamname = '%s' WHERE steamid = '%s'" % (Now(), inst, int(oplayer[7]) + 1, steamname, steamid))
                laston = elapsedTime(Now(), int(oplayer[2]))
                totplay = playedTime(int(oplayer[4]))
                try:
                    log.trace(f'fetching [{steamname}] [{steamid}] auctions from auction api website')
                    pauctions = fetchauctiondata(steamid)
                    totauctions, iauctions, dauctions = getauctionstats(pauctions)
                    writeauctionstats(steamid, totauctions, iauctions, dauctions)
                    log.debug(f'[{steamname}] auctions found: {iauctions} items, {dauctions} dinos, {totauctions} total')
                except:
                    log.error(f'error in parsing auction data')
                sleep(3)
                newpoints = int(oplayer[5]) + xferpoints
                mtxt = f'Welcome back {oplayer[1].title()}, you have {newpoints} reward points on \
{oplayer[15].capitalize()}, last online {laston} ago, total time played {totplay}'
                serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@{inst}'], nice=19, null=True)
                sleep(1)
                flast = dbquery("SELECT * FROM players WHERE server = '%s' AND steamid != '%s'" % (inst, steamid))
                pcnt = 0
                plist = ''
                potime = 40
                for row in flast:
                    chktme = Now() - int(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].title())
                        else:
                            plist = plist + ', %s' % (row[1].title())
                if pcnt != 0:
                    msg = f'There are {pcnt} other players online: {plist}'
                else:
                    msg = f'There are no other players are online on this server.'
                serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {msg}', f'@{inst}'], nice=19, null=True)
                sleep(2)
                if int(oplayer[14]) == 1 and int(oplayer[13]) == 1 and oplayer[3] == inst and inst != 'extiction':
                    mtxt = f'WARNING: Server has restarted since you logged in, vivarium your primordials!'
                    serverexec([f'arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@{inst}'], nice=19, null=True)
                    resetplayerbit(steamid)
                if oplayer[8] == '':
                    sleep(5)
                    mtxt = f'Your player is not linked with a discord account yet. type !linkme in global chat'
                    serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@{inst}'], nice=19, null=True)
                if not isinlottery(steamid):
                    sleep(3)
                    mtxt = f'A lottery you have not entered yet is underway. Type !lotto for more information'
                    serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@{inst}'], nice=19, null=True)

            if xferpoints != 0:
                    sleep(2)
                    mtxt = f'{xferpoints} rewards points were transferred to you from other cluster servers'
                    serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@{inst}'], nice=19, null=True)
            lottodeposits(steamid, inst)
            if int(oplayer[2]) + 60 < Now() and gogo == 0:
                # mtxt = f'{oplayer[1].capitalize()} has joined the server'
                # serverexec(['arkmanager', 'rconcmd', f'ServerChat {mtxt}', f'@{inst}'], nice=19, null=True)
                # writechat(inst, 'ALERT', f'<<< {oplayer[1].capitalize()} has joined the server', wcstamp())
                serverisinrestart(steamid, inst, oplayer)
                if iseventtime():
                    eventinfo = getcurrenteventinfo()
                    sleep(2)
                    mtxt = f'{eventinfo[4]} event is currently active!'
                    serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@{inst}'], nice=19, null=True)
                annc = dbquery("SELECT announce FROM general", fetch='one')
                if annc and annc[0] is not None:
                    sleep(2)
                    mtxt = annc[0]
                    serverexec(['arkmanager', 'rconcmd', f'ServerChatTo "{steamid}" {mtxt}', f'@{inst}'], nice=19, null=True)

    greetthreads[:] = [d for d in greetthreads if d.get('steamid') != steamid]


@log.catch
def doublecheckonline(inst):
    players = dbquery(f"SELECT * FROM players WHERE online = True AND lastseen <= {Now() - 280}", fmt='dict', fetch='all')
    for player in players:
        log.warning(f'Player [{player["playername"].title()}] wasnt found logging off. Clearing player from online status')
        steamid = player["steamid"]
        steamname = getsteaminfo(steamid)
        getsteambans(steamid)
        if not steamname:
            dbupdate("UPDATE players SET online = False, server = '%s', WHERE steamid = '%s'" % (inst, steamid))
        else:
            dbupdate("UPDATE players SET online = False, server = '%s', steamname = '%s' WHERE steamid = '%s'" % (inst, steamname, steamid))


def onlineupdate(inst):
    global greetthreads
    log.debug(f'starting online player watcher on {inst}')
    while True:
        try:
            cmdpipe = serverexec(['arkmanager', 'rconcmd', 'ListPlayers', f'@{inst}'], nice=19, null=False)
            b = cmdpipe.stdout.decode("utf-8")
            for line in iter(b.splitlines()):
                if line.startswith('Running command') or line.startswith('"') or line.startswith(' "') \
                   or line.startswith('Error:'):
                    pass
                else:
                    if line.startswith('"No Players'):
                        pass
                    else:
                        rawline = line.split(',')
                        if len(rawline) > 1:
                            nsteamid = rawline[1].strip()
                            steamname = cleanstring(rawline[0].split('. ', 1)[1])
                            if f'greet-{nsteamid}' not in greetthreads:
                                if not isgreeting(nsteamid):
                                    gthread = threading.Thread(name='greet-%s' % nsteamid, target=playergreet,
                                                               args=(nsteamid, steamname, inst))
                                    greetthreads.append({'steamid': nsteamid, 'gthread': gthread})
                                    gthread.start()
                                else:
                                    log.debug(f'online player greeting aleady running for {steamname}')
                            else:
                                log.debug(f'greeting already running for {steamname}')
                        else:
                            log.error(f'problem with parsing online player - {rawline}')
            doublecheckonline(inst)
            sleep(15)
        except:
            log.exception('Critical Error in Online Updater!')
            sleep(10)
