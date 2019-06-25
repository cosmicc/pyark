from modules.auctionhelper import fetchauctiondata, getauctionstats, writeauctionstats
from clusterevents import iseventtime, getcurrenteventinfo
from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.timehelper import elapsedTime, playedTime, wcstamp, Now
import logging
import socket
import subprocess
import threading
from time import sleep

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

welcomthreads = []
greetthreads = []

global instance


def resetplayerbit(steamid):
    dbupdate("UPDATE players SET restartbit = 0 WHERE steamid = '%s'" % (steamid,))


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,), fetch='one')
    elif whos == "ALERT" or isindb:
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                 (inst, whos, msg, tstamp))


def welcomenewplayer(steamid, inst):
        global welcomthreads
        log.info(f'welcome message thread started for new player {steamid} on {inst}')
        sleep(3)
        mtxt = 'Welcome to the Ultimate Extinction Core Galaxy Server Cluster!'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        sleep(3)
        mtxt = 'ARc rewards points earned as you play. Public teleporters, crafting area, and auction house. Build \
or find a rewards vault, free starter items.'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        sleep(3)
        mtxt = 'You get all your items back when you die automatically, The engram menu is laggy, sorry. Admins and \
help in discord. PRESS F1 AT ANYTIME FOR HELP. Have Fun!'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        sleep(3)
        mtxt = 'Everyone welcome a new player to the cluster!'
        subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
        log.debug(f'welcome message thread complete for new player {steamid} on {inst}')
        welcomthreads[:] = [d for d in welcomthreads if d.get('steamid') != steamid]


def iswelcoming(steamid):
    for each in welcomthreads:
        if each['steamid'] == steamid:
            if each['sthread'].is_alive():
                return True
            else:
                return False


def isgreeting(steamid):
    for each in greetthreads:
        if each['steamid'] == steamid:
            if each['gthread'].is_alive():
                return True
            else:
                return False


def serverisinrestart(steamid, inst, oplayer):
    rbt = dbquery("SELECT * FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if rbt[3] == "True":
        log.info(f'notifying player {oplayer[1]} that server {inst} will be restarting in {rbt[7]} min')
        mtxt = f'WARNING: server is restarting in {rbt[7]} minutes'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)


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


def checklottodeposits(steamid, inst):
    lottocheck = dbquery("SELECT * FROM lotterydeposits WHERE steamid = '%s'" % (steamid,))
    elpinfo = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid,), fetch='one')
    if lottocheck and inst == elpinfo[15]:
        for weach in lottocheck:
            if weach[4] == 1:
                log.info(f'{weach[3]} points added to {elpinfo[1]} for a lottery win')
                msg = f'{weach[3]} ARc points have been deposited into your account for a lottery win!'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, msg, inst), shell=True)
                subprocess.run('arkmanager rconcmd "ScriptCommand tcsar addarctotal %s %s" @%s' %
                               (steamid, weach[3], inst), shell=True)
            elif weach[4] == 0:
                log.info(f'{weach[3]} points removed from {elpinfo[1]} for a lottery entry')
                msg = f'{weach[3]} ARc points have been withdrawn from your account for a lottery entry'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, msg, inst), shell=True)
                subprocess.run('arkmanager rconcmd "ScriptCommand tcsar setarctotal %s %s" @%s' %
                               (steamid, str(int(elpinfo[5]) - int(weach[3])), inst), shell=True)
        dbupdate("DELETE FROM lotterydeposits WHERE steamid = '%s'" % (steamid,))


def checkifbanned(steamid):
    oplayer = dbquery("SELECT steamid FROM players WHERE steamid = '%s' AND banned != ''" % (steamid,), fetch='one')
    bplayer = dbquery("SELECT steamid FROM banlist WHERE steamid = '%s'" % (steamid,), fetch='one')
    if oplayer or bplayer:
        return True
    else:
        return False


def playergreet(steamid, inst):
    global greetthreads
    global welcomthreads
    gogo = 0
    xferpoints = 0
    if checkifbanned(steamid):
        log.warning(f'banned player with steamid {steamid} has tried to connect or is online on {inst}. kicking and banning.')
        subprocess.run("""arkmanager rconcmd 'kickplayer %s' @%s""" % (steamid, inst), shell=True)
        # subprocess.run("""arkmanager rconcmd 'banplayer %s' @%s""" % (steamid, inst), shell=True)
    else:
        oplayer = getplayer(steamid)
        if not oplayer:
            log.info(f'steamid {steamid} was not found. adding new player to cluster!')
            dbupdate("INSERT INTO players (steamid, playername, lastseen, server, playedtime, rewardpoints, \
                       firstseen, connects, discordid, banned, totalauctions, itemauctions, dinoauctions, restartbit, \
                       primordialbit, homeserver, transferpoints, lastpointtimestamp, lottowins) VALUES \
                       ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (steamid, 'newplayer', Now(), inst, '1', 50, Now(), 1, '', '', 0, 0, 0, 0, 0, inst, 0, Now(), 0))
            if not iswelcoming(steamid):
                welcom = threading.Thread(name='welcoming-%s' % steamid, target=welcomenewplayer, args=(steamid, inst))
                welcomthreads.append({'steamid': steamid, 'sthread': welcom})
                welcom.start()
            else:
                log.debug(f'welcome message thread already running for new player {steamid}')
            writechat(inst, 'ALERT', f'<<< A New player has joined the cluster!', wcstamp())
        else:
        # elif len(oplayer) > 2:
            if oplayer[16] != 0 and oplayer[15] == inst:
                xferpoints = int(oplayer[16])
                log.info(f'transferring {xferpoints} non home server points into account for \
{oplayer[1]} on {inst}')
                dbupdate("UPDATE players SET transferpoints = 0 WHERE steamid = '%s'" % (steamid,))
                subprocess.run('arkmanager rconcmd "ScriptCommand tcsar addarctotal %s %s" @%s' %
                               (steamid, xferpoints, inst), shell=True)
            if int(oplayer[2]) + 300 > Now():
                if oplayer[3] != inst:
                    pass
                    gogo = 1
                    #############################
                    mtxt = f'{oplayer[1].title()} has transferred here from {oplayer[3].capitalize()}'
                    subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
                    writechat(inst, 'ALERT', f'>><< {oplayer[1].capitalize()} has transferred from {oplayer[3].capitalize()} to {inst.capitalize()}', wcstamp())
                    log.info(f'player {oplayer[1].capitalize()} has transferred from {oplayer[3]} to {inst}')
                    #############################
                log.debug(f'online player {oplayer[1].title()} steamid {steamid} was found. updating info.')
                dbupdate("UPDATE players SET lastseen = '%s', server = '%s' WHERE steamid = '%s'" % (Now(), inst, steamid))
            else:
                log.info(f"player {oplayer[1].title()} has joined {inst}, total player's connections {int(oplayer[7])+1}. \
updating info.")
                dbupdate("UPDATE players SET lastseen = '%s', server = '%s', connects = '%s' WHERE steamid = '%s'" %
                         (Now(), inst, int(oplayer[7]) + 1, steamid))
                laston = elapsedTime(Now(), int(oplayer[2]))
                totplay = playedTime(int(oplayer[4]))
                try:
                    log.debug(f'fetching steamid {steamid} auctions from auction api website')
                    pauctions = fetchauctiondata(steamid)
                    totauctions, iauctions, dauctions = getauctionstats(pauctions)
                    writeauctionstats(steamid, totauctions, iauctions, dauctions)
                    strauctions = f', {totauctions} Auctions'
                except:
                    strauctions = ', 0 Auctions'
                    log.error(f'error in parsing auction data')
                sleep(3)
                newpoints = int(oplayer[5]) + xferpoints
                mtxt = f'Welcome back {oplayer[1].title()}, you have {newpoints} ARc reward points on \
{oplayer[15].capitalize()}{strauctions}, last online {laston} ago, total time played {totplay}'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
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
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, msg, inst), shell=True)
                sleep(2)
                if int(oplayer[14]) == 1 and int(oplayer[13]) == 1 and oplayer[3] == inst and inst != 'extiction':
                    mtxt = f'WARNING: Server has restarted since you logged in, vivarium your primordials!'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)
                    resetplayerbit(steamid)
                if oplayer[8] == '':
                    sleep(5)
                    mtxt = f'Your player is not linked with a discord account yet. type !linkme in global chat'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)
                if not isinlottery(steamid):
                    sleep(3)
                    mtxt = f'A lottery you have not entered yet is underway. Type !lotto for more information'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)

            if xferpoints != 0:
                    sleep(2)
                    mtxt = f'{xferpoints} rewards points were transferred to you from other cluster servers'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)
            checklottodeposits(steamid, inst)
            if int(oplayer[2]) + 60 < Now() and gogo == 0:
                mtxt = f'{oplayer[1].capitalize()} has joined the server'
                subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
                writechat(inst, 'ALERT', f'<<< {oplayer[1].capitalize()} has joined the server', wcstamp())
                serverisinrestart(steamid, inst, oplayer)
                if iseventtime():
                    eventinfo = getcurrenteventinfo()
                    sleep(2)
                    mtxt = f'{eventinfo[4]} event is currently active!'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)
                annc = dbquery("SELECT announce FROM general", fetch='one')
                if annc and annc[0] is not None:
                    sleep(2)
                    mtxt = annc[0]
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)

    greetthreads[:] = [d for d in greetthreads if d.get('steamid') != steamid]


def onlineupdate(inst):
    global greetthreads
    log.debug(f'starting online player watcher on {inst}')
    while True:
        try:
            cmdpipe = subprocess.Popen('arkmanager rconcmd ListPlayers @%s' % inst, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, shell=True)
            b = cmdpipe.stdout.read().decode("utf-8")
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
                            if f'greet-{nsteamid}' not in greetthreads:
                                if not isgreeting(nsteamid):
                                    gthread = threading.Thread(name='greet-%s' % nsteamid, target=playergreet,
                                                               args=(nsteamid, inst))
                                    greetthreads.append({'steamid': nsteamid, 'gthread': gthread})
                                    gthread.start()
                                else:
                                    log.debug(f'online player greeting aleady running for {nsteamid}')
                            else:
                                log.debug(f'greeting already running for {nsteamid}')
                        else:
                            log.error(f'problem with parsing online player - {rawline}')
            sleep(10)
        except:
            log.critical('Critical Error in Online Updater!', exc_info=True)
