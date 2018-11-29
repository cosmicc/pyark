from datetime import datetime
from modules.configreader import instance, numinstances
from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.instances import getlastwipe, getlastrestart
from modules.timehelper import elapsedTime, playedTime, wcstamp, tzfix, estshift, Secs, Now
from time import sleep
import logging
import random
import socket
import subprocess
import threading

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

lastvoter = 0.1
votertable = []
votestarttime = Now()
arewevoting = False


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,), fetch='one')
        if isindb:
            dbupdate("""INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')""" % (inst, whos, msg.replace("'", ""), tstamp))

    elif whos == "ALERT":
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


def getsteamid(whoasked):
    sid = dbquery("SELECT steamid FROM players WHERE playername = '%s'" % (whoasked,), fetch='one')
    if sid is None:
        log.critical(f'Player lookup failed! possible renamed player: {whoasked}')
        return 0
    else:
        return sid[0]


def resptimeleft(inst, whoasked):
    dbtl = dbquery("SELECT restartcountdown, needsrestart FROM instances WHERE name = '%s'" % (inst, ), fetch='one')
    if dbtl[1] == 'True':
        subprocess.run('arkmanager rconcmd "ServerChat Server is restarting in %s minutes" @%s' %
                       (dbtl[0], inst), shell=True)
    else:
        subprocess.run('arkmanager rconcmd "ServerChat Server is not pending a restart" @%s' % (inst), shell=True)


def getlastseen(seenname):
    flast = dbquery("SELECT * FROM players WHERE playername = '%s'" % (seenname, ), fetch='one')
    if not flast:
        return 'no player found with that name'
    else:
        plasttime = elapsedTime(Now(), float(flast[2]))
        if plasttime != 'now':
            return f'{seenname.capitalize()} was last seen {plasttime} ago on {flast[3]}'
        else:
            return f'{seenname.capitalize()} is online now on {flast[3]}'


def respmyinfo(inst, whoasked):
    pinfo = getplayer(playername=whoasked)
    ptime = playedTime(pinfo[4])
    mtxt = f"Your current reward points: {pinfo[5]}.\nYour total play time is {ptime}\nYour home server is {pinfo[15].capitalize()}"
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)


def gettimeplayed(seenname):
    flast = dbquery("SELECT * FROM players WHERE playername = '%s'" % (seenname,), fetch='one')
    if not flast:
        return 'No player found'
    else:
        plasttime = playedTime(float(flast[4]))
        return f'{seenname.capitalize()} total playtime is {plasttime} on {flast[3]}'


def getserverlist():
    newlist = []
    flast = dbquery("SELECT name FROM instances")
    for each in flast:
        newlist.append(each[0])
    return newlist


def whoisonlinewrapper(inst, oinst, whoasked, crnt):
    log.info(f'responding to a whoson request from {whoasked}')
    if oinst == inst:
        slist = getserverlist()
        for each in slist:
            whoisonline(each, oinst, whoasked, True, crnt)
    else:
        whoisonline(inst, oinst, whoasked, False)


def whoisonline(inst, oinst, whoasked, filt, crnt):
    try:
        if crnt == 1:
            potime = 40
        elif crnt == 2:
            potime = Secs['hour']
        elif crnt == 3:
            potime = Secs['day']
        flast = dbquery("SELECT * FROM players WHERE server = '%s'" % (inst,))
        pcnt = 0
        plist = ''
        for row in flast:
            chktme = Now() - float(row[2])
            if chktme < potime:
                # print(row[1],chktme)
                pcnt += 1
                if plist == '':
                    plist = '%s' % (row[1].title())
                else:
                    plist = plist + ', %s' % (row[1].title())
        if pcnt != 0:
            if crnt == 1:
                subprocess.run('arkmanager rconcmd "ServerChat %s has %s players online: %s" @%s' %
                               (inst.capitalize(), pcnt, plist, oinst), shell=True)
            elif crnt == 2:
                subprocess.run('arkmanager rconcmd "ServerChat %s has had %s players in last hour: %s" @%s' %
                               (inst.capitalize(), pcnt, plist, oinst), shell=True)
            elif crnt == 3:
                subprocess.run('arkmanager rconcmd "ServerChat %s had had %s players in last day: %s" @%s' %
                               (inst.capitalize(), pcnt, plist, oinst), shell=True)

        if pcnt == 0 and not filt:
            subprocess.run('arkmanager rconcmd "ServerChat %s has no players online." @%s' % (inst.capitalize(), oinst), shell=True)
    except:
        log.exception()
        subprocess.run('arkmanager rconcmd "ServerChat Server %s does not exist." @%s' % (inst.capitalize(), inst), shell=True)


def getlastvote(inst):
    flast = dbquery("SELECT lastdinowipe FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return ''.join(flast[0])


def isvoting(inst):
    for each in range(numinstances):
        if instance[each]['name'] == inst and 'votethread' in instance[each]:
            if instance[each]['votethread'].is_alive():
                return True
            else:
                return False


def populatevoters(inst):
    log.debug(f'populating vote table for {inst}')
    global votertable
    votertable = []
    pcnt = 0
    pdata = dbquery("SELECT * FROM players WHERE server = '%s'" % (inst,))
    for row in pdata:
        chktme = Now() - float(row[2])
        if chktme < 90:
            pcnt += 1
            newvoter = [row[0], row[1], 3]
            votertable.append(newvoter)
    log.debug(votertable)
    return pcnt


def setvote(whoasked, myvote):
    global votertable
    for each in votertable:
        if each[0] == getsteamid(whoasked):
            each[2] = myvote


def getvote(whoasked):
    for each in votertable:
        if each[0] == getsteamid(whoasked):
            return each[2]
    return 99


def castedvote(inst, whoasked, myvote):
    global arewevoting
    if not isvoting(inst):
        subprocess.run('arkmanager rconcmd "ServerChat No vote is taking place now" @%s' % (inst), shell=True)
    else:
        pdata = dbquery("SELECT * FROM players WHERE playername = '%s'" % (whoasked,))
        if getvote(whoasked) == 99:
            mtxt = 'Sorry, you are not eligible to vote in this round'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                           (getsteamid(whoasked), mtxt, inst), shell=True)
        elif not pdata:
            mtxt = 'Sorry, you are not eligible to vote. Tell an admin they need to update your name!'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                           (getsteamid(whoasked), mtxt, inst), shell=True)
        elif getvote(whoasked) == 2:
            mtxt = "You started the vote. you're assumed a YES vote."
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                           (getsteamid(whoasked), mtxt, inst), shell=True)
        elif getvote(whoasked) == 1:
            mtxt = 'You have already voted YES. you can only vote once.'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                           (getsteamid(whoasked), mtxt, inst), shell=True)
        else:
            if myvote:
                setvote(whoasked, 1)
                mtxt = 'Your YES vote has been cast'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                               (getsteamid(whoasked), mtxt, inst), shell=True)
            else:
                setvote(whoasked, 0)
                mtxt = 'Your NO vote has been cast'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                               (getsteamid(whoasked), mtxt, inst), shell=True)
                log.info(f'Voting NO has won, NO wild dino wipe will be performed for {inst}')
                sleep(1)
                subprocess.run('arkmanager rconcmd "ServerChat Voting has finished. NO has won." @%s' %
                               (inst), shell=True)
                sleep(1)
                subprocess.run('arkmanager rconcmd "ServerChat NO wild dino wipe will be performed" @%s' %
                               (inst), shell=True)
                writechat(inst, 'ALERT', f'### A wild dino wipe vote has failed with a NO vote from \
{whoasked.capitalize()}', wcstamp())
                arewevoting = False


def votingpassed():
    vcnt = 0
    tvoters = 0
    for each in votertable:
        tvoters += 1
        if each[2] == 1 or each[2] == 2:
            vcnt += 1
    if vcnt == tvoters:
        return True
    else:
        return False


def enoughvotes():
    vcnt = 0
    tvoters = 0
    for each in votertable:
        tvoters += 1
        if each[2] == 1 or each[2] == 2:
            vcnt += 1
    if vcnt >= tvoters - 1:
        return True
    else:
        return False


def resetlastvote(inst):
    newtime = Now()
    dbupdate("UPDATE instances SET lastvote = '%s' WHERE name = '%s'" % (newtime, inst))


def resetlastwipe(inst):
    newtime = Now()
    dbupdate("UPDATE instances SET lastdinowipe = '%s' WHERE name = '%s'" % (newtime, inst))


def howmanyvotes():
    vcnt = 0
    tvoters = 0
    for each in votertable:
        tvoters += 1
        if each[2] == 1 or each[2] == 2:
            vcnt += 1
    return vcnt, tvoters


def wipeit(inst):
    yesvoters, totvoters = howmanyvotes()
    log.info(f'voting yes has won ({yesvoters}/{totvoters}), wild dino wipe incoming for {inst}')
    subprocess.run('arkmanager rconcmd "ServerChat Voting has finished. YES has won (%s of %s)" @%s' %
                   (yesvoters, totvoters, inst), shell=True)
    writechat(inst, 'ALERT', f'### A wild dino wipe vote has won by YES vote ({yesvoters}/{totvoters}). \
Wiping wild dinos now.', wcstamp())
    sleep(3)
    subprocess.run('arkmanager rconcmd "ServerChat Wild dino wipe commencing in 10 seconds" @%s' % (inst), shell=True)
    sleep(10)
    subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' %
                   (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    resetlastwipe(inst)
    log.debug(f'voted wild dino wipe complete for {inst}')


def voting(inst, whoasked):
    log.info(f'wild dino wipe voting has started for {inst} by {whoasked}')
    global lastvoter
    global votestarttime
    global arewevoting
    global votertable
    arewevoting = True
    pon = populatevoters(inst)
    setvote(whoasked, 2)
    subprocess.run('arkmanager rconcmd "ServerChat Wild dino wipe voting has started with %s players. vote !yes or \
!no in global chat now" @%s' % (pon, inst), shell=True)
    votestarttime = Now()
    sltimer = 0
    writechat(inst, 'ALERT', f'### A wild dino wipe vote has been started by {whoasked.capitalize()}', wcstamp())
    while arewevoting:
        sleep(5)
        if votingpassed():
            wipeit(inst)
            arewevoting = False
        elif Now() - votestarttime > Secs['5min']:
            if enoughvotes():
                wipeit(inst)
                arewevoting = False
            else:
                yesvoters, totvoters = howmanyvotes()
                subprocess.run('arkmanager rconcmd "ServerChat Not enough votes (%s of %s). voting has ended." @%s' %
                               (yesvoters, totvoters, inst), shell=True)
                log.info(f'not enough votes ({yesvoters}/{totvoters}), voting has ended on {inst}')
                writechat(inst, 'ALERT', f'### Wild dino wipe vote failed with not enough votes ({yesvoters} of \
{totvoters})', wcstamp())
                arewevoting = False
        else:
            if sltimer == 120 or sltimer == 240:
                log.debug(f'sending voting waiting message to vote on {inst}')
                subprocess.run('arkmanager rconcmd "ServerChat Wild dino wipe vote is waiting. make sure you have \
cast your vote !yes or !no in global chat" @%s' % (inst), shell=True)
        sltimer += 5
    # log.info(f'final votertable for vote on {inst}')
    log.info(votertable)
    votertable = []
    lastvoter = Now()
    resetlastvote(inst)
    log.info(f'voting thread has ended on {inst}')


def startvoter(inst, whoasked):
    global instance
    if isvoting(inst):
        subprocess.run('arkmanager rconcmd "ServerChat Voting has already started. cast your vote" @%s' %
                       (inst), shell=True)
    elif Now() - float(getlastvote(inst)) < Secs['4hour']:          # 4 hours between wipes
        rawtimeleft = Secs['4hour'] - (Now() - float(getlastvote(inst)))
        timeleft = playedTime(rawtimeleft)
        subprocess.run('arkmanager rconcmd "ServerChat You must wait %s until next vote can start" @%s' %
                       (timeleft, inst), shell=True)
        log.info(f'vote start denied for {whoasked} on {inst} because 4 hour timer')
    elif Now() - float(lastvoter) < Secs['10min']:      # 10 min between attempts
        rawtimeleft = Secs['10min'] - (Now() - lastvoter)
        timeleft = playedTime(rawtimeleft)
        subprocess.run('arkmanager rconcmd "ServerChat You must wait %s until next vote can start" @%s' %
                       (timeleft, inst), shell=True)
        log.info(f'vote start denied for {whoasked} on {inst} because 10 min timer')
    else:
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                instance[each]['votethread'] = threading.Thread(name='%s-voter' % inst, target=voting,
                                                                args=(inst, whoasked))
                instance[each]['votethread'].start()


def getnamefromchat(chat):
    rawline = chat.split('(')
    if len(rawline) > 1:
        rawname = rawline[1].split(')')
        return rawname[0].lower()


def isserver(line):
    rawissrv = line.split(':')
    # print(rawissrv)
    if len(rawissrv) > 1:
        if rawissrv[1].strip() == 'SERVER':
            return True
        else:
            return False
    else:
        return False


def linker(minst, whoasked):
    dplayer = dbquery("SELECT * FROM players WHERE playername == '%s'" % (whoasked.lower(),), fetch='one')
    if dplayer:
        if dplayer[8] is None or dplayer[8] == '':
            rcode = ''.join(str(x) for x in random.sample(range(10), 4))
            log.info(f'generated code {rcode} for link request from {dplayer[1]} on {minst}')
            dbupdate("DELETE from linkrequests WHERE steamid = '%s'" % (dplayer[0],))
            dbupdate("INSERT INTO linkrequests (steamid, name, reqcode) VALUES ('%s', '%s', '%s')" % (dplayer[0], dplayer[1], str(rcode)))
            msg = f'Your discord link code is {rcode}, goto discord now and type !linkme {rcode}'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (dplayer[0], msg, minst), shell=True)
        else:
            log.info(f'link request for {dplayer[1]} denied, already linked')
            msg = f'You already have a discord account linked to this account'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (dplayer[0], msg, minst), shell=True)
    else:
        pass
        # user not found in db (wierd)
        log.error('wiredness...')


def writechatlog(inst, whos, msg, tstamp):
    isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos, ), fetch='one')
    if isindb:
        clog = f'{tstamp} [{whos.upper()}]{msg}\n'
        with open(f"/home/ark/shared/logs/{inst}/chatlog/chat.log", "at") as f:
            f.write(clog)
        f.close()


def writeglobal(inst, whos, msg):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, Now()))


def processtcdata(inst, tcdata):
    steamid = tcdata['SteamID']
    playername = tcdata['PlayerName'].lower()
    playtime = int(float(tcdata['TotalPlayed'].replace(',', '')))
    rewardpoints = int(tcdata['Points'].replace(',', ''))
    pexist = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid, ), fetch='one')
    if not pexist:
        if steamid != '':
            log.info(f'player {playername} with steamid {steamid} was not found on {inst}. adding \
new player to cluster.')
            dbupdate("INSERT INTO players (steamid, playername, lastseen, server, playedtime, rewardpoints, \
                      firstseen, connects, discordid, banned, totalauctions, itemauctions, dinoauctions, restartbit, \
                      primordialbit, homeserver, transferpoints, lastpointtimestamp, lottowins) VALUES \
                      ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" %
                     (steamid, playername, Now(), inst, int(playtime), rewardpoints, Now(), 1, '', '', 0, 0, 0, 0,
                      0, inst, 0, Now(), 0))
    elif steamid != '':
        if inst == pexist[15]:
            log.debug(f'player {playername} with steamid {steamid} was found on home server {inst}. updating.')
            dbupdate("UPDATE players SET playername = '%s', playedtime = '%s', rewardpoints = '%s' WHERE steamid = '%s'" %
                     (playername, playtime, rewardpoints, steamid))
        elif inst == 'extinction':
            log.debug(f'player {playername} with steamid {steamid} was found on extinction server {inst}. skipping.')
        else:
            log.debug(f'player {playername} with steamid {steamid} was found on NON home server {inst}. updating.')
            if int(pexist[16]) != int(rewardpoints):
                if int(rewardpoints) != 0:
                    if Now() - float(pexist[17]) > 60:
                        log.info(f'adding {rewardpoints} non home points to {pexist[16]} transfer points for \
{playername} on {inst}')
                        dbupdate("UPDATE players SET transferpoints = '%s', lastpointtimestamp = '%s' WHERE steamid = '%s'" %
                                 (int(rewardpoints) + int(pexist[16]), str(Now()), str(steamid)))
                        subprocess.run('arkmanager rconcmd "ScriptCommand tcsar setarctotal %s 0" @%s' %
                                       (steamid, inst), shell=True)
                    else:
                        log.debug(f'reward points not past threshold for wait (to avoid duplicates) for \
{playername} on {inst}, skipping')
                else:
                    log.debug(f'zero reward points to account for {playername} on {inst}, skipping')
            else:
                log.debug(f'duplicate reward points to account for {playername} on {inst}, skipping')


def homeserver(inst, whoasked, ext):
    steamid = getsteamid(whoasked)
    pinfo = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid,), fetch='one')
    if ext != '':
        tservers = ['ragnarok', 'island', 'volcano']
        if ext in tservers:
            if ext != pinfo[15]:
                if inst == pinfo[15]:
                    log.info(f'{whoasked} has transferred home servers from {pinfo[15]} to {ext} \
with {pinfo[5]} points')
                    subprocess.run('arkmanager rconcmd "ScriptCommand tcsar setarctotal %s 0" @%s' %
                                   (steamid, inst), shell=True)
                    dbupdate("UPDATE players SET transferpoints = '%s', homeserver = '%s' WHERE steamid = '%s'" %
                             (pinfo[5], ext, steamid))
                    msg = f'Your {pinfo[5]} points have been transferred to your new home server: {ext.capitalize()}'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (pinfo[0], msg, inst), shell=True)
                else:
                    msg = f'You must be on your home server {pinfo[15].capitalize()} to change your home'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (pinfo[0], msg, inst), shell=True)
            else:
                msg = f'{ext.capitalize()} is already your home server'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                               (pinfo[0], msg, inst), shell=True)
        else:
            msg = f'{ext.capitalize()} is not a server you can call home in the cluster.'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (pinfo[0], msg, inst), shell=True)
    else:
        msg = f'Your current home server is: {pinfo[15].capitalize()}'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (pinfo[0], msg, inst), shell=True)
        msg = f'Type !myhome <servername> to change your home.'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (pinfo[0], msg, inst), shell=True)


def sendlotteryinfo(linfo, lpinfo, inst):
    if linfo[1] == 'points':
        msg = f'Current lottery is up to {linfo[2]} ARc reward points.'
    else:
        msg = f'Current lottery is for a {linfo[2]}.'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
    msg = f'{linfo[6]} players have entered into this lottery so far'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
    ltime = estshift(datetime.fromtimestamp(float(linfo[3]) + (Secs['hour'] * int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
    msg = f'Lottery ends {ltime} EST in {elapsedTime(float(linfo[3])+(3600*int(linfo[5])),Now())}'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
    amiin = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (lpinfo[0],), fetch='one')
    if amiin:
        msg = f'You are enterted into this lottery. Good Luck!'
    else:
        msg = f'Type !lotto join to spend {linfo[4]} points and enter into this lottery'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)


def lotteryquery(whoasked, lchoice, inst):
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE winner = 'Incomplete'", fetch='one')
    lpinfo = dbquery("SELECT * FROM players WHERE playername = '%s'" % (whoasked,), fetch='one')
    if linfo:
        if lchoice == 'join' or lchoice == 'enter':
            lpcheck = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (lpinfo[0],), fetch='one')
            if linfo[1] == 'points':
                lfo = 'ARc Rewards Points'
            else:
                lfo = linfo[2]
            ltime = estshift(datetime.fromtimestamp(float(linfo[3]) + (Secs['hour'] *
                                                                       int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
            if lpcheck is None:
                dbupdate("INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('%s', '%s', '%s', '%s')" %
                         (lpinfo[0], lpinfo[1], Now(), 0))
                if linfo[1] == 'points':
                    dbupdate("UPDATE lotteryinfo SET payoutitem = '%s' WHERE winner = 'Incomplete'" %
                             (str(int(linfo[2]) + int(linfo[4])), ))
                dbupdate("UPDATE lotteryinfo SET players = '%s' WHERE id = '%s'" % (int(linfo[6]) + 1, linfo[0]))
                msg = f'You have been added to the {lfo} lottery! A winner will be choosen on {ltime} in \
{elapsedTime(float(linfo[3])+(3600*int(linfo[5])),Now())}. Good Luck!'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
                log.info(f'player {whoasked} has joined the current active lottery.')
            else:
                msg = f'You are already participating in this lottery for {lfo}.  Lottery ends {ltime} in \
{elapsedTime(float(linfo[3])+(3600*int(linfo[5])),Now())}'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
        else:
            sendlotteryinfo(linfo, lpinfo, inst)
    else:
        msg = f'There are no current lotterys underway.'
        subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (msg, inst), shell=True)


def checkcommands(minst):
    inst = minst
    cmdpipe = subprocess.Popen('arkmanager rconcmd getgamelog @%s' % (minst), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        whoasked = 'nobody'
        if line.startswith('Running command') or line.startswith('Command processed') or line.startswith('Error:') \
           or isserver(line):
            pass
        elif line.find('!help') != -1:
            whoasked = getnamefromchat(line)
            subprocess.run('arkmanager rconcmd "ServerChat Commands: @all, !who, !lasthour, !lastday, !timeleft, \
!myinfo, !myhome, !lastwipe, !lastrestart, !vote, !lottery, !lastseen <playername>, !playtime <playername>" @%s' %
                           (minst), shell=True)
            log.info(f'responded to help request on {minst} from {whoasked}')
        elif line.find('@all') != -1:
            try:
                whoasked = getnamefromchat(line)
                rawline = line.split('(')
                if len(rawline) > 1:
                    rawname = rawline[1].split(')')
                    whoname = rawname[0].lower()
                    if len(rawname) > 1:
                        cmsg = rawname[1].split('@all')[1].strip()
                        if cmsg != '':
                            nmsg = line.split(': ')
                            if len(nmsg) > 2:
                                try:
                                    if nmsg[0].startswith('"'):
                                        dto = datetime.strptime(nmsg[0][3:], '%y.%m.%d_%H.%M.%S')
                                        dto = dto - tzfix
                                    else:
                                        dto = datetime.strptime(nmsg[0][2:], '%y.%m.%d_%H.%M.%S')
                                        dto = dto - tzfix
                                    tstamp = dto.strftime('%m-%d %I:%M%p')
                                    writeglobal(minst, whoname, cmsg)
                                    writechat('Global', whoname, cmsg, tstamp)
                                except:
                                    log.critical('could not parse date from chat', exc_info=True)
                        else:
                            subprocess.run("""arkmanager rconcmd "ServerChat Commands: You didn't supply a message \
to send to all servers" @%s""" % (minst), shell=True)
            except:
                log.critical('Critical Error in global chat writer!', exc_info=True)

        elif line.find('!lastdinowipe') != -1 or line.find('!lastwipe') != -1:
            whoasked = getnamefromchat(line)
            lastwipe = elapsedTime(Now(), getlastwipe(minst))
            subprocess.run('arkmanager rconcmd "ServerChat Last wild dino wipe was %s ago" @%s' %
                           (lastwipe, minst), shell=True)
            log.info(f'responded to a lastdinowipe query on {minst} from {whoasked}')

        elif line.find('!lastrestart') != -1:
            whoasked = getnamefromchat(line)
            lastrestart = elapsedTime(Now(), getlastrestart(minst))
            subprocess.run('arkmanager rconcmd "ServerChat Last server restart was %s ago" @%s' %
                           (lastrestart, minst), shell=True)
            log.info(f'responded to a lastrestart query on {minst} from {whoasked}')

        elif line.find('!lastseen') != -1:
            whoasked = getnamefromchat(line)
            rawseenname = line.split(':')
            orgname = rawseenname[1].strip()
            lsnname = rawseenname[2].split('!lastseen')
            if len(lsnname) > 1:
                seenname = lsnname[1].strip().lower()
                lsn = getlastseen(seenname)
                subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lsn, minst), shell=True)
            else:
                subprocess.run('arkmanager rconcmd "ServerChat You must specify a player name to search" @%s' %
                               (minst), shell=True)
            log.info(f'responding to a lastseen request for {seenname} from {orgname}')

        elif line.find('!playedtime') != -1:
            rawseenname = line.split(':')
            orgname = rawseenname[1].strip()
            lsnname = rawseenname[2].split('!playedtime')
            seenname = lsnname[1].strip().lower()
            whoasked = getnamefromchat(line)
            if lsnname:
                lpt = gettimeplayed(seenname)
            else:
                lpt = gettimeplayed(whoasked)
            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lpt, minst), shell=True)
            log.info(f'responding to a playedtime request for {whoasked}')
        elif line.find('!recent') != -1 or line.find('!whorecent') != -1 or line.find('!lasthour') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            if len(lastlline) == 2:
                ninst = lastlline[1]
            else:
                ninst = minst
            whoisonlinewrapper(ninst, minst, whoasked, 2)
        elif line.find('!today') != -1 or line.find('!lastday') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            if len(lastlline) == 2:
                ninst = lastlline[1]
            else:
                ninst = minst
            whoisonlinewrapper(ninst, minst, whoasked, 3)
        elif line.find('!mypoints') != -1 or line.find('!myinfo') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to a myinfo request on {minst} from {whoasked}')
            respmyinfo(minst, whoasked)
        elif line.find('!whoson') != -1 or line.find('!whosonline') != -1 or line.find('!who') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            if len(lastlline) == 2:
                ninst = lastlline[1]
            else:
                ninst = minst
            whoisonlinewrapper(ninst, minst, whoasked, 1)
        elif line.find('!myhome') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            if len(lastlline) == 2:
                ninst = lastlline[1]
            else:
                ninst = ''
            homeserver(minst, whoasked, ninst)
        elif line.find('!vote') != -1 or line.find('!startvote') != -1 or line.find('!votestart') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to a dino wipe vote request on {minst} from {whoasked}')
            startvoter(minst, whoasked)
        elif line.find('!agree') != -1 or line.find('!yes') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to YES vote on {minst} from {whoasked}')
            castedvote(minst, whoasked, True)
        elif line.find('!disagree') != -1 or line.find('!no') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to NO vote on {minst} from {whoasked}')
            castedvote(minst, whoasked, False)
        elif line.find('!timeleft') != -1 or line.find('!restart') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to a restart timeleft request on {minst} from {whoasked}')
            resptimeleft(minst, whoasked)
        elif line.find('!linkme') != -1 or line.find('!link') != -1:
            whoasked = getnamefromchat(line)
            linker(minst, whoasked)
        elif line.find('!lottery') != -1 or line.find('!lotto') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            if len(rawline) > 2:
                lastlline = rawline[2].strip().split(' ')
                if len(lastlline) == 2:
                    lchoice = lastlline[1]
                else:
                    lchoice = False
                lotteryquery(whoasked, lchoice, minst)
        elif line.find('[TCsAR]') != -1:
            dfg = line.split('||')
            dfh = dfg[1].split('|')
            tcdata = {}
            for each in dfh:
                ee = each.strip().split(': ')
                if len(ee) > 1:
                    tcdata.update({ee[0]: ee[1]})
            if 'SteamID' in tcdata:
                processtcdata(minst, tcdata)
        else:
            rawline = line.split('(')
            if len(rawline) > 1:
                rawname = rawline[1].split(')')
                whoname = rawname[0].lower()
                if len(rawname) > 1:
                    cmsg = rawname[1]
                    nmsg = line.split(': ')
                    if len(nmsg) > 2:
                        try:
                            if nmsg[0].startswith('"'):
                                dto = datetime.strptime(nmsg[0][3:], '%y.%m.%d_%H.%M.%S')
                            else:
                                dto = datetime.strptime(nmsg[0][2:], '%y.%m.%d_%H.%M.%S')
                            tstamp = dto.strftime('%m-%d %I:%M%p')
                            writechat(inst, whoname, cmsg, tstamp)
                            writechatlog(inst, whoname, cmsg, tstamp)
                        except:
                            log.critical('could not parse date from chat', exc_info=True)
        if line.startswith('Running command') or line.startswith('Command processed') \
                or line.startswith('Error:') or isserver(line):
            pass
        else:
            with open(f"/home/ark/shared/logs/{minst}/gamelog/game.log", "at") as f:
                lobber = line.replace('"', '').strip()
                if lobber != '':
                    f.write(f"""{line.replace('"','').strip()}\n""")
            f.close()


def clisten(minst):
    log.debug(f'starting the command listener thread for {minst}')
    while True:
        try:
            checkcommands(minst)
            sleep(2)
        except:
            log.critical('Critical Error in Command Listener!', exc_info=True)
