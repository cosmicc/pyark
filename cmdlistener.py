from datetime import datetime, timedelta
from modules.configreader import instance, numinstances
from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.instances import homeablelist, getlastwipe, getlastrestart
from modules.timehelper import elapsedTime, playedTime, wcstamp, tzfix, Secs, Now, datetimeto
from lottery import getlastlotteryinfo
from time import sleep
from loguru import logger as log
import random
import subprocess
import threading
import os

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
    sid = dbquery("SELECT steamid FROM players WHERE (playername = '%s') or (alias = '%s')" % (whoasked, whoasked), fetch='one')
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


def newplayer(steamid, inst):
        pplayer = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid,), fetch='one')
        if not pplayer[23]:
            dbupdate("UPDATE players SET welcomeannounce = True WHERE steamid = '%s'" % (steamid,))
            log.info(f'Sending welcome message to [{pplayer[1].title()}] on [{inst.title()}]')
            sleep(3)
            mtxt = 'Welcome to the Ultimate Extinction Core Galaxy Server Cluster!'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
            sleep(3)
            mtxt = 'Rewards points earned as you play, Public teleporters, crafting area, Build a rewards vault, free starter items inside.'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
            sleep(3)
            mtxt = 'Press F1 or Discord at anytime for help. Have Fun!'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
            sleep(3)
            mtxt = 'Everyone welcome a new player to the cluster!'
            subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
            log.debug(f'welcome message thread complete for new player {steamid} on {inst}')
            writechat(inst, 'ALERT', f'<<< A New player has joined the cluster!', wcstamp())
        else:
            log.warning('Skipping welcome message, player already marked announced')


def respmyinfo(inst, whoasked):
    pinfo = getplayer(playername=whoasked)
    ptime = playedTime(pinfo[4])
    mtxt = f"Your current reward points: {pinfo[5] + pinfo[16]}.\nYour total play time is {ptime}\nYour home server is {pinfo[15].capitalize()}"
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
        pdata = dbquery("SELECT * FROM players WHERE playername = '%s' or alias = '%s'" % (whoasked, whoasked))
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
                bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n\n<RichColor Color="1,1,0,1">                            NO votes have won!</>\n  <RichColor Color="1,0,0,1">                      Wild dinos will NOT be wiped</>\n\n           You must wait 10 minutes before you can start another vote"""
                subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
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
    if vcnt >= tvoters / 2:
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
    log.log('VOTE', f'YES has won ({yesvoters}/{totvoters}), wild dinos are wiping on [{inst.title()}] in 15 seconds')
    bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n<RichColor Color="0,1,0,1">                     YES votes have won! ('%s' of '%s' Players)</>\n\n  <RichColor Color="1,1,0,1">               !! WIPING ALL WILD DINOS IN 10 SECONDS !!</>""" % (yesvoters, totvoters)
    subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
    writechat(inst, 'ALERT', f'### A wild dino wipe vote has won by YES vote ({yesvoters}/{totvoters}). \
Wiping wild dinos now.', wcstamp())
    sleep(7)
    subprocess.run('arkmanager rconcmd "Destroyall BeeHive_C" @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    sleep(3)
    subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    resetlastwipe(inst)
    log.log('WIPE', f'All wild dinos have been wiped from [{inst.title()}]')


def voting(inst, whoasked):
    log.log('VOTE', f'A wild dino wipe vote has started for [{inst.title()}] by [{whoasked.title()}]')
    global lastvoter
    global votestarttime
    global arewevoting
    global votertable
    arewevoting = True
    pon = populatevoters(inst)
    setvote(whoasked, 2)
    bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">             A Wild dino wipe vote has started with {pon} online players</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe\n                           Voting lasts 3 minutes"""
    subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
    votestarttime = Now()
    sltimer = 0
    writechat(inst, 'ALERT', f'### A wild dino wipe vote has been started by {whoasked.capitalize()}', wcstamp())
    while arewevoting:
        sleep(5)
        if votingpassed() and Now() - votestarttime > 10:
            wipeit(inst)
            arewevoting = False
        elif Now() - votestarttime > Secs['3min']:
            if enoughvotes():
                wipeit(inst)
                arewevoting = False
            else:
                yesvoters, totvoters = howmanyvotes()
                subprocess.run('arkmanager rconcmd "ServerChat Not enough votes (%s of %s). voting has ended." @%s' %
                               (yesvoters, totvoters, inst), shell=True)
                log.log('VOTE', f'Voting has ended on [{inst.title()}] Not enough votes ({yesvoters}/{totvoters})')
                writechat(inst, 'ALERT', f'### Wild dino wipe vote failed with not enough votes ({yesvoters} of \
{totvoters})', wcstamp())
                arewevoting = False
        else:
            if sltimer == 120:
                log.log('VOTE', f'Sending voting waiting message to vote on [{inst.title()}]')
                bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">                  A Wild dino wipe vote is waiting for votes!</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe"""
                subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)

        sltimer += 5
    log.debug(votertable)
    votertable = []
    lastvoter = Now()
    resetlastvote(inst)
    log.debug(f'voting thread has ended on {inst}')


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
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 4 hour timer')
    elif Now() - float(lastvoter) < Secs['10min']:      # 10 min between attempts
        rawtimeleft = Secs['10min'] - (Now() - lastvoter)
        timeleft = playedTime(rawtimeleft)
        subprocess.run('arkmanager rconcmd "ServerChat You must wait %s until next vote can start" @%s' %
                       (timeleft, inst), shell=True)
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 10 min timer')
    else:
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                instance[each]['votethread'] = threading.Thread(name='%s-voter' % inst, target=voting,
                                                                args=(inst, whoasked))
                instance[each]['votethread'].start()


def getnamefromchat(chat):
    try:
        rawlineorg = chat.split(':')
        if len(rawlineorg) > 1:
            rawline = rawlineorg[1].split(' (')
            rawline = rawline[1][:-1].strip()
            return rawline.lower()
    except:
        log.error(f'GetNameFromChat Error: {chat}')


def getnamefromchaterror(inst):
    # subprocess.run('arkmanager rconcmd "ServerChat Someone has a colon : in their steam name. This makes me, the bot, have issues. This needs to be removed from your steam name please!" @%s' % (inst,), shell=True)
    pass


def processadminline(line):
    line.replace('"', '').strip()
    newline = line[12:]
    newlinesplit = newline.split(':')
    if newlinesplit[0].strip() == 'AdminCmd':
        pline = newline[10:]
    else:
        pline = newline
    log.log('ADMIN', pline)


def isserver(line):
    rawissrv = line.split(':')
    if len(rawissrv) > 1:
        if rawissrv[1].strip() == 'SERVER':
            return True
        else:
            return False
    else:
        return False


def linker(minst, whoasked):
    dplayer = dbquery("SELECT * FROM players WHERE playername = '%s' or alias = '%s'" % (whoasked.lower(), whoasked.lower()), fetch='one')
    if dplayer:
        if dplayer[8] is None or dplayer[8] == '':
            rcode = ''.join(str(x) for x in random.sample(range(10), 4))
            log.info(f'Generated code [{rcode}] for link request from [{dplayer[1].title()}] on [{minst.title()}]')
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
        log.error(f'User not found in DB {whoasked}!')


def writechatlog(inst, whos, msg, tstamp):
    isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos, ), fetch='one')
    if isindb:
        clog = f"""{tstamp} [{whos.upper()}]{msg}\n"""
        if not os.path.exists(f'/home/ark/shared/logs/{inst}'):
            log.error(f'Log directory /home/ark/shared/logs/{inst} does not exist! creating')
            os.mkdir(f'/home/ark/shared/logs/{inst}', 0o777)
            os.chown(f'/home/ark/shared/logs/{inst}', 1001, 1005)
        with open(f"/home/ark/shared/logs/{inst}/chat.log", "at") as f:
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
            log.info(f'Player [{playername.title()}] on [{inst.title()}] was not found. Adding new player')
            dbupdate("INSERT INTO players (steamid, playername, lastseen, server, playedtime, rewardpoints, \
                      firstseen, connects, discordid, banned, totalauctions, itemauctions, dinoauctions, restartbit, \
                      primordialbit, homeserver, transferpoints, lastpointtimestamp, lottowins, welcomeannounce) VALUES \
                      ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" %
                     (steamid, playername, Now(), inst, int(playtime), rewardpoints, Now(), 1, '', '', 0, 0, 0, 0,
                      0, inst, 0, Now(), 0, False))
            welcom = threading.Thread(name='welcoming-%s' % steamid, target=newplayer, args=(steamid, inst))
            welcom.start()
    elif steamid != '':
        if playername.lower() != pexist[1].lower():
            log.info(f'Player name update for [{pexist[1]}] to [{playername}]')
            dbupdate("UPDATE players SET playername = '%s' WHERE steamid = '%s'" % (playername, steamid))
        if not pexist[23]:
            welcom = threading.Thread(name='welcoming-%s' % steamid, target=newplayer, args=(steamid, inst))
            welcom.start()
        if inst == pexist[15]:
            log.trace(f'player {playername} with steamid {steamid} was found on home server {inst}. updating info.')
            dbupdate("UPDATE players SET playedtime = '%s', rewardpoints = '%s' WHERE steamid = '%s'" %
                     (playtime, rewardpoints, steamid))
        else:
            log.trace(f'player {playername} with steamid {steamid} was found on NON home server {inst}. updating info.')
            if int(pexist[16]) != int(rewardpoints):
                if int(rewardpoints) != 0:
                    if Now() - float(pexist[17]) > 60:
                        log.debug(f'adding {rewardpoints} non home points to {pexist[16]} transfer points for \
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
        tservers = []
        tservers = homeablelist()
        ext = ext.lower()
        if ext in tservers:
            if ext != pinfo[15]:
                if inst == pinfo[15]:
                    log.info(f'[{whoasked.title()}] has transferred home servers from [{pinfo[15].title()}] to [{ext.title()}] \
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


def lastlotto(whoasked, inst):
    lastl = getlastlotteryinfo()
    msg = f'Last lottery was won by {lastl["winner"].upper()} for {lastl["payout"]} points {elapsedTime(datetimeto(lastl["startdate"] + timedelta(hours=int(lastl["days"])), fmt="epoch"),Now())} ago'
    subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (msg, inst), shell=True)


def lotteryinfo(linfo, lpinfo, inst):
    msg = f'Current lottery is up to {linfo["payout"]} ARc reward points.'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
    msg = f'{linfo["players"]} players have entered into this lottery so far'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
    msg = f'Lottery ends in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
    amiin = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (lpinfo[0],), fetch='one')
    if amiin:
        msg = f'You are enterted into this lottery. Good Luck!'
    else:
        msg = f'Type !lotto join to spend {linfo["buyin"]} points and enter into this lottery'
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)


def lottery(whoasked, lchoice, inst):
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
    lpinfo = dbquery("SELECT * FROM players WHERE playername = '%s' or alias = '%s'" % (whoasked, whoasked), fetch='one')
    if linfo:
        if lchoice == 'join' or lchoice == 'enter':
            log.log('CMD', f'Responding to a [!lotto join] request from [{whoasked.title()}] on [{inst.title()}]')
            lpcheck = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (lpinfo[0],), fetch='one')
            lfo = 'ARc Rewards Points'
            # ltime = estshift(datetime.fromtimestamp(float(linfo[3]) + (Secs['hour'] * int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
            if lpcheck is None:
                dbupdate("INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('%s', '%s', '%s', '%s')" %
                         (lpinfo[0], lpinfo[1], Now(fmt='dt'), 0))
                dbupdate("UPDATE lotteryinfo SET payout = '%s', players = '%s' WHERE completed = False" % (linfo['payout'] + linfo['buyin'] * 2, linfo['players'] + 1))
                msg = f'You have been added to the {lfo} lottery! A winner will be choosen in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}. Good Luck!'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
                log.log('LOTTO', f'Player [{whoasked.title()}] has joined the current active lottery')
            else:
                msg = f'You are already participating in this lottery for {lfo}.  Lottery ends in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)
        else:
            log.log('CMD', f'Responding to a [!lotto] request from [{whoasked.title()}] on [{inst.title()}]')
            lotteryinfo(linfo, lpinfo, inst)
    else:
        log.info(f'Responding to a [!lotto] request from [{whoasked.title()}] on [{inst.title()}]')
        msg = f'There are no current lotterys underway.'
        subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (msg, inst), shell=True)


def checkcommands(minst):
    inst = minst
    cmdpipe = subprocess.Popen('arkmanager rconcmd getgamelog @%s' % (minst), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        if len(line) < 3 or line.startswith('Running command') or line.startswith('Command processed') or isserver(line):
            pass
        elif line.find('AdminCmd:') != -1 or line.find('Admin Removed Soul Recovery Entry:') != -1 or line.find('[WBUI]') != -1 or line.find('Force respawning Wild Dinos!') != -1:
            processadminline(line.replace('"', '').strip())
        elif line.find('released:') != -1 or line.find('trapped:') != -1 or line.find(' was killed!') != -1 or line.find('joined this ARK!') != -1 or line.find('Tamed a') != -1 or line.find('</>') != -1 or line.startswith('Error:') or line.find('starved to death!') != -1 or line.find('left this ARK!') != -1:
            if not os.path.exists(f'/home/ark/shared/logs/{minst}'):
                log.error(f'Log directory /home/ark/shared/logs/{minst} does not exist! creating')
                os.mkdir(f'/home/ark/shared/logs/{minst}', 0o777)
                os.chown(f'/home/ark/shared/logs/{minst}', 1001, 1005)
            with open(f"/home/ark/shared/logs/{minst}/game.log", "at") as f:
                lobber = line.replace('"', '').strip()
                if lobber != '':
                    f.write(f"""{line.replace('"','').strip()}\n""")
            f.close()
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
            whoasked = getnamefromchat(line)
            log.trace(f'chatline who: {whoasked}')
            if whoasked is None:
                getnamefromchaterror(minst)
            else:
                if line.find('!help') != -1:
                    subprocess.run('arkmanager rconcmd "ServerChat Commands: @all, !who, !lasthour, !lastday, !timeleft, \
                    !myinfo, !myhome, !lastwipe, !lastrestart, !vote, !lottery, !lastseen <playername>, !playtime <playername>" @%s' %
                                   (minst), shell=True)
                    log.log('CMD', f'Responding to a [!help] request from [{whoasked.title()}] on [{minst.title()}]')
                elif line.find('@all') != -1:
                    try:
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
                                            log.exception('could not parse date from chat')
                                else:
                                    subprocess.run("""arkmanager rconcmd "ServerChat Commands: You didn't supply a message \
        to send to all servers" @%s""" % (minst), shell=True)
                    except:
                        log.exception('Critical Error in global chat writer!')

                elif line.find('!lastdinowipe') != -1 or line.find('!lastwipe') != -1:
                    lastwipe = elapsedTime(Now(), getlastwipe(minst))
                    subprocess.run('arkmanager rconcmd "ServerChat Last wild dino wipe was %s ago" @%s' %
                                   (lastwipe, minst), shell=True)
                    log.log('CMD', f'Responding to a [!lastwipe] request from [{whoasked.title()}] on [{minst.title()}]')

                elif line.find('!lastrestart') != -1:
                    lastrestart = elapsedTime(Now(), getlastrestart(minst))
                    subprocess.run('arkmanager rconcmd "ServerChat Last server restart was %s ago" @%s' %
                                   (lastrestart, minst), shell=True)
                    log.log('CMD', f'Responding to a [!lastrestart] request from [{whoasked.title()}] on [{minst.title()}]')

                elif line.find('!lastseen') != -1:
                    rawseenname = line.split(':')
                    orgname = rawseenname[1].strip()
                    lsnname = rawseenname[2].split('!lastseen')
                    if len(lsnname) > 1:
                        seenname = lsnname[1].strip().lower()
                        lsn = getlastseen(seenname)
                        subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lsn, minst), shell=True)
                        log.log('CMD', f'Responding to a [!lastseen] request for [{seenname.title()}] from [{orgname.title()}] on [{minst.title()}]')
                    else:
                        subprocess.run('arkmanager rconcmd "ServerChat You must specify a player name to search" @%s' %
                                       (minst), shell=True)
                        log.log('CMD', f'Responding to a invalid [!lastseen] request from [{orgname.title()}] on [{minst.title()}]')

                elif line.find('!playedtime') != -1:
                    rawseenname = line.split(':')
                    orgname = rawseenname[1].strip()
                    lsnname = rawseenname[2].split('!playedtime')
                    seenname = lsnname[1].strip().lower()
                    if lsnname:
                        lpt = gettimeplayed(seenname)
                    else:
                        lpt = gettimeplayed(whoasked)
                    subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lpt, minst), shell=True)
                    log.log('CMD', f'Responding to a [!playedtime] request for [{whoasked.title()}] on [{minst.title()}]')

                elif line.find('!recent') != -1 or line.find('!whorecent') != -1 or line.find('!lasthour') != -1:
                    rawline = line.split(':')
                    lastlline = rawline[2].strip().split(' ')
                    if len(lastlline) == 2:
                        ninst = lastlline[1]
                    else:
                        ninst = minst
                    log.log('CMD', f'Responding to a [!recent] request for [{whoasked.title()}] on [{minst.title()}]')
                    whoisonlinewrapper(ninst, minst, whoasked, 2)

                elif line.find('!today') != -1 or line.find('!lastday') != -1:
                    rawline = line.split(':')
                    lastlline = rawline[2].strip().split(' ')
                    if len(lastlline) == 2:
                        ninst = lastlline[1]
                    else:
                        ninst = minst
                    log.log('CMD', f'Responding to a [!today] request for [{whoasked.title()}] on [{minst.title()}]')
                    whoisonlinewrapper(ninst, minst, whoasked, 3)

                elif line.find('!mypoints') != -1 or line.find('!myinfo') != -1:
                    log.log('CMD', f'Responding to a [!myinfo] request from [{whoasked.title()}] on [{minst.title()}]')
                    respmyinfo(minst, whoasked)

                elif line.find('!whoson') != -1 or line.find('!online') != -1 or line.find('!who') != -1:
                    rawline = line.split(':')
                    lastlline = rawline[2].strip().split(' ')
                    if len(lastlline) == 2:
                        ninst = lastlline[1]
                    else:
                        ninst = minst
                    log.log('CMD', f'Responding to a [!who] request for [{whoasked.title()}] on [{minst.title()}]')
                    whoisonlinewrapper(ninst, minst, whoasked, 1)

                elif line.find('!myhome') != -1 or line.find('!home') != -1 or line.find('!sethome') != -1:
                    rawline = line.split(':')
                    lastlline = rawline[2].strip().split(' ')
                    if len(lastlline) == 2:
                        ninst = lastlline[1]
                    else:
                        ninst = ''
                    log.log('CMD', f'Responding to a [!myhome] request for [{whoasked.title()}] on [{minst.title()}]')
                    homeserver(minst, whoasked, ninst)

                elif line.find('!vote') != -1 or line.find('!startvote') != -1 or line.find('!wipe') != -1:
                    log.debug(f'Responding to a [!vote] request from [{whoasked.title()}] on [{minst.title()}]')
                    startvoter(minst, whoasked)

                elif line.find('!agree') != -1 or line.find('!yes') != -1:
                    log.debug(f'responding to YES vote on {minst} from {whoasked}')
                    castedvote(minst, whoasked, True)

                elif line.find('!disagree') != -1 or line.find('!no') != -1:
                    log.log('VOTE', f'Responding to NO vote on [{minst.title()}] from [{whoasked.title()}]')
                    castedvote(minst, whoasked, False)

                elif line.find('!timeleft') != -1 or line.find('!restart') != -1:
                    log.log('CMD', f'Responding to a [!timeleft] request from [{whoasked.title()}] on [{minst.title()}]')
                    resptimeleft(minst, whoasked)

                elif line.find('!linkme') != -1 or line.find('!link') != -1:
                    log.log('CMD', f'Responding to a [!linkme] request from [{whoasked.title()}] on [{minst.title()}]')
                    linker(minst, whoasked)

                elif line.find('!lottery') != -1 or line.find('!lotto') != -1:
                    rawline = line.split(':')
                    if len(rawline) > 2:
                        lastlline = rawline[2].strip().split(' ')
                        if len(lastlline) == 2:
                            lchoice = lastlline[1]
                        else:
                            lchoice = False
                        lottery(whoasked, lchoice, minst)

                elif line.find('!lastlotto') != -1 or line.find('!winner') != -1:
                    log.log('CMD', f'Responding to a [!lastlotto] request from [{whoasked.title()}] on [{minst.title()}]')
                    lastlotto(minst, whoasked)

                elif line.startswith('!'):
                    lpinfo = dbquery("SELECT * FROM players WHERE playername = '%s' or alias = '%s'" % (whoasked, whoasked), fetch='one')
                    log.warning(f'Invalid command request from [{whoasked.title()}] on [{minst.title()}]')
                    msg = "Invalid command. Try !help"
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (lpinfo[0], msg, inst), shell=True)

                else:
                    log.trace(f'chatline elsed: {line}')
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
                                    log.log('CHAT', f'{inst} | {whoname} | {cmsg[2:]}')
                                    writechat(inst, whoname, cmsg.replace("'", ""), tstamp)
                                    writechatlog(inst, whoname, cmsg, tstamp)

                                except:
                                    log.exception('could not parse date from chat')


@log.catch
def clisten(minst):
    log.debug(f'starting the command listener thread for {minst}')
    while True:
        try:
            checkcommands(minst)
            sleep(2)
        except:
            log.exception('Critical Error in Command Listener!')
            sleep(10)
