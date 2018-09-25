import logging, subprocess, sqlite3, time, threading, random, socket
from datetime import datetime, timedelta
from timehelper import *
from configreader import *

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

lastvoter = 0.1
votertable = []
votestarttime = time.time()
arewevoting = False

numinstances = int(config.get('general', 'instances'))
instance = [dict() for x in range(numinstances)]
instr = ''
for each in range(numinstances):
    a = config.get('instance%s' % (each), 'name')
    b = config.get('instance%s' % (each), 'logfile')
    instance[each] = {'name':a,'logfile':b}
    if instr == '':
        instr = '%s' % (a)
    else:
        instr=instr + ', %s' % (a)

def writechat(inst,whos,msg,tstamp):
    isindb = False
    if whos != 'ALERT':
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT * from players WHERE playername = ?', (whos,))
        isindb = c.fetchone()
        c.close()
        conn.close()
    elif whos == "ALERT" or isindb:
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', (inst,whos,msg,tstamp))
        conn.commit()
        c.close()
        conn.close()

def getsteamid(whoasked):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT steamid FROM players WHERE playername = ?', (whoasked,))
    sid = c.fetchone()
    c.close()
    conn.close()
    return ''.join(sid[0])

def resptimeleft(inst,whoasked):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT restartcountdown, needsrestart FROM instances WHERE name = ?', [inst])
    dbtl = c.fetchone()
    c.close()
    conn.close()
    if dbtl[1] == 'True':
        subprocess.run('arkmanager rconcmd "ServerChat server is restarting in %s minutes" @%s' % (dbtl[0], inst), shell=True)
    else:
        subprocess.run('arkmanager rconcmd "ServerChat server is not pending a restart" @%s' % (inst), shell=True)

def getlastrestart(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastrestart FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def getlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastdinowipe FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def getlastseen(seenname):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE playername = ?', [seenname])
    flast = c.fetchone()
    c.close()
    conn.close()
    if not flast:
        return 'no player found with that name'
    else:
        plasttime = elapsedTime(time.time(),float(flast[2]))
        if plasttime != 'now':
            return f'{seenname} was last seen {plasttime} ago on {flast[3]}'
        else:
            return f'{seenname} is online now on {flast[3]}'

def respmyinfo(inst,whoasked):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE playername = ?', [whoasked])
    pinfo = c.fetchone()
    c.close()
    conn.close()
    ptime = playedTime(float(pinfo[4].replace(',','')))
    mtxt = f"your current reward points: {pinfo[5]}. your total play time is {ptime}"
    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)

def gettimeplayed(seenname):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE playername = ?', [seenname])
    flast = c.fetchone()
    c.close()
    conn.close()
    if not flast:
        return 'No player found'
    else:
        plasttime = playedTime(float(flast[4].replace(',','')))
        return f'{seenname} total playtime is {plasttime} on {flast[3]}'

def getserverlist():
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newlist = []
    c.execute('SELECT name FROM instances')
    flast = c.fetchall()
    c.close()
    conn.close()
    for each in flast:
        newlist.append(each[0])
    return newlist

def whoisonlinewrapper(inst,oinst,whoasked,crnt):
    log.info(f'responding to a whoson request from {whoasked}')
    if oinst == inst:
        slist = getserverlist()
        for each in slist:
            whoisonline(each,oinst,whoasked,True,crnt)
    else:
        whoisonline(inst,oinst,whoasked,False)

def whoisonline(inst,oinst,whoasked,filt,crnt):
    try:
        if crnt == 1:
            potime = 40
        elif crnt == 2:
            potime = 3600
        elif crnt == 3:
            potime = 86400
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT * FROM players WHERE server = ?', [inst])
        flast = c.fetchall()
        c.close()
        conn.close()
        pcnt = 0
        plist = ''
        for row in flast:
            chktme = time.time()-float(row[2])
            if chktme < potime:
                #print(row[1],chktme)
                pcnt += 1
                if plist == '':
                    plist = '%s' % (row[1])
                else:
                    plist=plist + ', %s' % (row[1])
        if pcnt != 0:
            if crnt == 1:
                subprocess.run('arkmanager rconcmd "ServerChat %s has %s players online: %s" @%s' % (inst, pcnt, plist, oinst), shell=True)
            elif crnt == 2:
                subprocess.run('arkmanager rconcmd "ServerChat %s has had %s players in last hour: %s" @%s' % (inst, pcnt, plist, oinst), shell=True)
            elif crnt ==3:
                subprocess.run('arkmanager rconcmd "ServerChat %s had had %s players in last day: %s" @%s' % (inst, pcnt, plist, oinst), shell=True)

        if pcnt == 0 and not filt:
            subprocess.run('arkmanager rconcmd "ServerChat %s has no players online." @%s' % (inst, oinst), shell=True)
    except:
        log.exception()
        subprocess.run('arkmanager rconcmd "ServerChat Server %s does not exist." @%s' % (inst, inst), shell=True)

def getlastvote(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastdinowipe FROM instances WHERE name = ?', [inst])
    flast = c.fetchone()
    c.close()
    conn.close()
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
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE server = ?', [inst])
    pdata = c.fetchall()
    c.close()
    conn.close()
    for row in pdata:
        chktme = time.time()-float(row[2])
        if chktme < 90:
            pcnt += 1
            newvoter = [row[0],row[1],3]
            votertable.append(newvoter)
    log.info(votertable)
    return pcnt

def setvote(whoasked,myvote):
    global votertable
    for each in votertable:
        if each[0] == getsteamid(whoasked):
            each[2] = myvote

def getvote(whoasked):
    for each in votertable:
        if each[0] == getsteamid(whoasked):
            return each[2]
    return 99


def castedvote(inst,whoasked,myvote):
    global arewevoting
    if not isvoting(inst):
        subprocess.run('arkmanager rconcmd "ServerChat no vote is taking place now" @%s' % (inst), shell=True)
    else:
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT * FROM players WHERE playername = ?', [whoasked])
        pdata = c.fetchall()
        c.close()
        conn.close()
        

        if getvote(whoasked) == 99:
            mtxt = 'sorry, you are not eligible to vote in this round'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)
        elif not pdata:
            mtxt = 'sorry, you are not eligible to vote. Tell an admin they need to update your name!'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)
        elif getvote(whoasked) == 2:
            mtxt = "you started the vote. you're assumed a YES vote."
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)
        elif getvote(whoasked) == 1:
            mtxt = 'you have already voted YES. you can only vote once.'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)
        else:
            if myvote:
                setvote(whoasked,1)
                mtxt = 'your YES vote has been cast'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)
            else:
                setvote(whoasked,0)
                mtxt = 'your NO vote has been cast'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)
                log.info(f'voting NO has won, NO wild dino wipe will be performed for {inst}')
                time.sleep(1)
                subprocess.run('arkmanager rconcmd "ServerChat voting has finished. NO has won." @%s' % (inst), shell=True)
                time.sleep(1)
                subprocess.run('arkmanager rconcmd "ServerChat NO wild dino wipe will be performed" @%s' % (inst), shell=True)
                writechat(inst,'ALERT',f'### A wild dino wipe vote has failed with a NO vote from {whoasked.capitalize()}',wcstamp())
                arewevoting=False

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
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET lastvote = ? WHERE name = ?', [newtime,inst])
    conn.commit()
    c.close()
    conn.close()

def resetlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET lastdinowipe = ? WHERE name = ?', [newtime,inst])
    conn.commit()
    c.close()
    conn.close()

def howmanyvotes():
    vcnt = 0
    tvoters = 0
    for each in votertable:
        tvoters += 1
        if each[2] == 1 or each[2] == 2:
            vcnt += 1
    return vcnt,tvoters

def wipeit(inst):
    yesvoters, totvoters = howmanyvotes()
    log.info(f'voting yes has won ({yesvoters}/{totvoters}), wild dino wipe incoming for {inst}')
    subprocess.run('arkmanager rconcmd "ServerChat voting has finished. YES has won (%s of %s)" @%s' % (yesvoters,totvoters,inst), shell=True)
    writechat(inst,'ALERT',f'### A wild dino wipe vote has won by YES vote ({yesvoters}/{totvoters}). Wiping wild dinos now.',wcstamp())
    time.sleep(3)
    subprocess.run('arkmanager rconcmd "ServerChat wild dino wipe commencing in 10 seconds" @%s' % (inst), shell=True)
    time.sleep(10)
    subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    resetlastwipe(inst)
    log.debug(f'voted wild dino wipe complete for {inst}')

def voting(inst,whoasked):
    log.info(f'wild dino wipe voting has started for {inst}')
    global lastvoter
    global votestarttime
    global arewevoting
    global votertable
    arewevoting = True
    pon = populatevoters(inst)
    log.info(f'making {whoasked} the vote leader')
    setvote(whoasked,2)
    subprocess.run('arkmanager rconcmd "ServerChat wild dino wipe voting has started with %s players. vote !yes or !no in global chat now" @%s' % (pon,inst), shell=True)
    votestarttime = time.time()
    sltimer = 0
    writechat(inst,'ALERT',f'### A wild dino wipe vote has been started by {whoasked.capitalize()}',wcstamp())
    while arewevoting:
        time.sleep(5)
        if votingpassed():
            wipeit(inst)
            arewevoting = False
        elif time.time()-votestarttime > 300:
            if enoughvotes():
                wipeit(inst)
                arewevoting = False
            else:
                yesvoters, totvoters = howmanyvotes()
                subprocess.run('arkmanager rconcmd "ServerChat not enough votes (%s of %s). voting has ended." @%s' % (yesvoters,totvoters,inst), shell=True)
                log.info(f'not enough votes ({yesvoters}/{totvoters}), voting has ended on {inst}')
                writechat(inst,'ALERT',f'### Wild dino wipe vote failed with not enough votes ({yesvoters} of {totvoters})',wcstamp())
                arewevoting = False
        else:
            if sltimer == 120 or sltimer == 240:
                log.info(f'sending voting waiting message to vote on {inst}')
                subprocess.run('arkmanager rconcmd "ServerChat wild dino wipe vote is waiting. make sure you have cast your vote !yes or !no in global chat" @%s' % (inst), shell=True)

        sltimer += 5
    log.info(f'final votertable for vote on {inst}')
    log.info(votertable)
    votertable = []
    lastvoter = time.time()
    resetlastvote(inst)
    log.info(f'voting thread has ended on {inst}')

def startvoter(inst,whoasked):
    global instance
    #print(time.time()-float(getlastvote(inst)))
    if isvoting(inst):
        subprocess.run('arkmanager rconcmd "ServerChat voting has already started. cast your vote" @%s' % (inst), shell=True)
    elif time.time()-float(getlastvote(inst)) < 14400:          # 2 hours between wipes
        rawtimeleft = 14400-(time.time()-float(getlastvote(inst)))
        timeleft = playedTime(rawtimeleft)
        subprocess.run('arkmanager rconcmd "ServerChat you must wait %s until next vote can start" @%s' % (timeleft,inst), shell=True)
        log.info(f'vote start denied for {whoasked} on {inst} because 2 hour timer')
    elif time.time()-float(lastvoter) < 600:  # 10 min between attempts   
        rawtimeleft = 600-(time.time()-lastvoter)
        timeleft = playedTime(rawtimeleft)
        subprocess.run('arkmanager rconcmd "ServerChat you must wait %s until next vote can start" @%s' % (timeleft,inst), shell=True)
        log.info(f'vote start denied for {whoasked} on {inst} because 10 min timer')
    else:
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                instance[each]['votethread'] = threading.Thread(name = '%s-voter' % inst, target=voting, args=(inst,whoasked))
                instance[each]['votethread'].start()

def getnamefromchat(chat):
    rawline = chat.split('(')
    rawname = rawline[1].split(')')
    return rawname[0].lower()

def isserver(line):
    rawissrv = line.split(':')
    #print(rawissrv)
    if len(rawissrv) > 1:
        if rawissrv[1].strip() == 'SERVER':
            return True
        else:
            return False
    else:
        return False

def linker(minst,whoasked):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE playername == ?', (whoasked,))
    dplayer = c.fetchone()
    c.close()
    conn.close()
    if dplayer:
        if dplayer[8] == None or dplayer[8] == '':
            rcode = ''.join(str(x) for x in random.sample(range(10), 4))
            log.info(f'generated code {rcode} for link request from {dplayer[1]} on {minst}')
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('DELETE from linkrequests WHERE steamid = ?', (dplayer[0],))
            conn.commit()
            c.execute('INSERT INTO linkrequests (steamid, name, reqcode) VALUES (?, ?, ?)', (dplayer[0],dplayer[1],str(rcode)))
            conn.commit()
            c.close()
            conn.close()
            msg = f'your discord link code is {rcode}, goto discord now and type !linkme {rcode}'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (dplayer[0],msg,minst), shell=True)
        else:
            log.info(f'link request for {dplayer[1]} denied, already linked')
            msg = f'you already have a discord account linked to this account'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (dplayer[0],msg,minst), shell=True)
    else:
        pass
        # user not found in db (wierd)

def writechat(inst,whos,msg,tstamp):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * from players WHERE playername = ?', (whos,))
    isindb = c.fetchone()
    c.close()
    conn.close()
    if isindb:
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', (inst,whos,msg,tstamp))
        conn.commit()
        c.close()
        conn.close()

def writeglobal(inst,whos,msg):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('INSERT INTO globalbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', (inst,whos,msg,time.time()))
    conn.commit()
    c.close()
    conn.close()

def checkcommands(minst):
    inst = minst
    cmdpipe = subprocess.Popen('arkmanager rconcmd getgamelog @%s' % (minst), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        whoasked = 'nobody' 
        #log.warning(f'###{line}')
        if line.startswith('Running command') or line.startswith('Command processed') or line.startswith('Error:') or isserver(line):
            pass
        elif line.find('!help') != -1:
            whoasked = getnamefromchat(line)
            subprocess.run('arkmanager rconcmd "ServerChat Commands: @all, !who, !lasthour, !lastday, !timeleft, !myinfo, !lastwipe, !lastrestart, !vote, !lastseen <playername>, !playtime <playername>" @%s' % (minst), shell=True)
            log.info(f'responded to help request on {minst} from {whoasked}')

        elif line.find('!global') != -1 or line.find('@all') != -1:
            try:
                whoasked = getnamefromchat(line)
                rawline = line.split('(')
                if len(rawline) > 1:
                    rawname = rawline[1].split(')')
                    whoname = rawname[0].lower()
                    if len(rawname) > 1:
                        cmsg = rawname[1].split(' ')[2]
                        print(f'!!!{cmsg}')
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
                                writeglobal(minst,whoname,cmsg)
                                writechat('Global',whoname,cmsg,tstamp)
                            except:
                                log.warning('could not parse date from chat')
                    else:
                        subprocess.run("""arkmanager rconcmd "ServerChat Commands: You didn't supply a message to send to all servers" @%s""" % (minst), shell=True)


            except:
                log.critical('Critical Error in global chat writer!', exc_info=True)


        elif line.find('!lastdinowipe') != -1 or line.find('!lastwipe') != -1:
            whoasked = getnamefromchat(line)
            lastwipe = elapsedTime(time.time(),float(getlastwipe(minst)))
            subprocess.run('arkmanager rconcmd "ServerChat last wild dino wipe was %s ago" @%s' % (lastwipe, minst), shell=True)
            log.info(f'responded to a lastdinowipe query on {minst} from {whoasked}')
        elif line.find('!lastrestart') != -1:
            whoasked = getnamefromchat(line)
            lastrestart = elapsedTime(time.time(),float(getlastrestart(minst)))
            subprocess.run('arkmanager rconcmd "ServerChat last server restart was %s ago" @%s' % (lastrestart, minst), shell=True)
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
                subprocess.run('arkmanager rconcmd "ServerChat you must specify a player name to search" @%s' % (minst), shell=True)
            log.info(f'responding to a lastseen request for {seenname} from {orgname}')
        elif line.find('!playedtime') != -1 or line.find('!playtime') != -1 or line.find('!totalplayed') != -1:
            whoasked = getnamefromchat(line)
            seenname = rawline[4].lower()
            lpt = gettimeplayed(seenname)
            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lpt, minst), shell=True)
            log.info(f'responding to a playedtime request for {seenname} on {minst} from {whoasked}')
        elif line.find('!recent') != -1 or line.find('!whorecent') != -1 or line.find('!lasthour') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            if len(lastlline) == 2:
                ninst = lastlline[1]
            else:
                ninst = minst
            whoisonlinewrapper(ninst,minst,whoasked,2)
        elif line.find('!today') != -1 or line.find('!lastday') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            if len(lastlline) == 2:
                ninst = lastlline[1]
            else:
                ninst = minst
            whoisonlinewrapper(ninst,minst,whoasked,3)
        elif line.find('!mypoints') != -1 or line.find('!myinfo') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to a myinfo request on {minst} from {whoasked}')
            respmyinfo(minst,whoasked)
        elif line.find('!whoson') != -1 or line.find('!whosonline') != -1 or line.find('!who') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            if len(lastlline) == 2:
                ninst = lastlline[1] 
            else:
                ninst = minst
            whoisonlinewrapper(ninst,minst,whoasked,1)
        elif line.find('!vote') != -1 or line.find('!startvote') != -1 or line.find('!votestart') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to a dino wipe vote request on {minst} from {whoasked}')
            startvoter(minst,whoasked)
        elif line.find('!agree') != -1 or line.find('!yes') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to YES vote on {minst} from {whoasked}')
            castedvote(minst,whoasked,True)
        elif line.find('!disagree') != -1 or line.find('!no') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to NO vote on {minst} from {whoasked}')
            castedvote(minst,whoasked,False)
        elif line.find('!timeleft') != -1 or line.find('!restart') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to a restart timeleft request on {minst} from {whoasked}')
            resptimeleft(minst,whoasked)
        elif line.find('!linkme') != -1 or line.find('!link') != -1:
            whoasked = getnamefromchat(line)
            linker(minst,whoasked)
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
                                dto = dto - tzfix
                            else:
                                dto = datetime.strptime(nmsg[0][2:], '%y.%m.%d_%H.%M.%S')
                                dto = dto - tzfix
                            tstamp = dto.strftime('%m-%d %I:%M%p')
                            writechat(inst,whoname,cmsg,tstamp)
                        except:
                            log.warning('could not parse date from chat')

def clisten(minst):
    log.debug(f'starting the command listener thread for {minst}')
    while True:
        try:
            checkcommands(minst)
            time.sleep(2)
        except:
            log.critical('Critical Error in Command Listener!', exc_info=True)
            try:
                if c in vars():
                    c.close()
            except:
                pass
            try:
                if conn in vars():
                    conn.close()
            except:
                pass
            try:
                if c1 in vars():
                    c1.close()
            except:
                pass
            try:
                if conn1 in vars():
                    conn1.close()
            except:
                pass
