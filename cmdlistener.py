import sys, logging, subprocess, sqlite3, time, threading
from configparser import ConfigParser

log = logging.getLogger(__name__)

class ExtConfigParser(ConfigParser):
    def getlist(self, section, option):
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.split(','))))

    def getlistint(self, section, option):
        return [int(x) for x in self.getlist(section, option)]

configfile = '/home/ark/pyark.cfg'

config = ExtConfigParser()
config.read(configfile)

lastvoter = 0.1
votertable = []
votestarttime = time.time()
arewevoting = False

sharedpath = config.get('general', 'shared')
sqldb = f'{sharedpath}/db/pyark.db'
arkroot = config.get('general', 'arkroot')
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

def elapsedTime(start_time, stop_time, lshort=False):
    diff_time = start_time - stop_time
    total_min = diff_time / 60
    minutes = int(total_min % 60)
    if minutes == 1:
        if lshort is False:
            minstring = 'minute'
        else:
            minstring = 'min'
    else:
        if lshort is False:
            minstring = 'minutes'
        else:
            minstring = 'mins'
    hours = int(total_min / 60)
    if hours == 1:
        if lshort is False:
            hourstring = 'hour'
        else:
            hourstring = 'hr'
    else:
        if lshort is False:
            hourstring = 'hours'
        else:
            hourstring = 'hrs'
    days = int(hours / 24)
    if days == 1:
        if lshort is False:
            daystring = 'day'
        else:
            daystring = 'day'
    else:
        if lshort is False:
            daystring = 'days'
        else:
            daystring = 'days'
    if days != 0:
        return('{} {}, {} {}'.format(days, daystring, hours, hourstring))
    elif hours != 0:
        return('{} {}, {} {}'.format(hours, hourstring, minutes, minstring))
    elif minutes > 1:
        return('{} {}'.format(minutes, minstring))
    elif minutes <= 1:
        return('now')
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')

def playedTime(ptime):
    total_min = ptime / 60
    minutes = int(total_min % 60)
    if minutes == 1:
        minstring = 'Min'
    else:
        minstring = 'mins'
    hours = int(total_min / 60)
    if hours == 1:
        hourstring = 'hour'
    else:
        hourstring = 'hours'
    days = int(hours / 24)
    if days == 1:
        daystring = 'day'
    else:
        daystring = 'days'
    if days != 0:
        return('{} {}, {} {}'.format(days, daystring, hours-days*24, hourstring))
    elif hours != 0:
        return('{} {}, {} {}'.format(hours, hourstring, minutes-hours, minstring))
    elif minutes != 0:
        return('{} {}'.format(minutes, minstring))
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')

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
    #print(flast)
    if not flast:
        return 'no player found with that name'
    else:
        plasttime = elapsedTime(time.time(),float(flast[2]))
        if plasttime != 'now':
            return f'{seenname} was last seen {plasttime} ago on {flast[3]}'
        else:
            return f'{seenname} is online now on {flast[3]}'

def gettimeplayed(seenname):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE playername = ?', [seenname])
    flast = c.fetchone()
    c.close()
    conn.close()
    #print(flast)
    if not flast:
        return 'No player found'
    else:
        plasttime = playedTime(float(flast[4].replace(',','')))
        return f'{seenname} total playtime is {plasttime} on {flast[3]}'

def getserverlist():
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT name FROM instances')
    flast = c.fetchall()
    c.close()
    conn.close()
    log.warning(flast)


def whoisonlinewrapper(inst,oinst,whoasked):
    log.info(f'responding to a whoson request from {whoasked}')
    getserverlist()
    if oinst == inst:
        for each in range(numinstances):
            whoisonline(instance[each]['name'],oinst,whoasked,'True')
    else:
        whoisonline(inst,oinst,whoasked,'False')

def whoisonline(inst,oinst,whoasked,filt):
    log.warning(f'checking whos online on {inst} for {whoasked}')
    try:
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT * FROM players WHERE server = ?', [inst])
        flast = c.fetchall()
        pcnt = 0
        plist = ''
        for row in flast:
            chktme = time.time()-float(row[2])
            if chktme < 90:
                #print(row[1],chktme)
                pcnt += 1
                if plist == '':
                    plist = '%s' % (row[1])
                else:
                    plist=plist + ', %s' % (row[1])
        if pcnt != 0:
            subprocess.run('arkmanager rconcmd "ServerChat %s has %s players online: %s" @%s' % (inst, pcnt, plist, oinst), shell=True)
        if pcnt == 0 and not filt:
            subprocess.run('arkmanager rconcmd "ServerChat %s has no players online." @%s' % (inst, oinst), shell=True)

        c.close()
        conn.close()
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

def getsteamid(whoasked):
    #log.error(whoasked)
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT steamid FROM players WHERE playername = ?', (whoasked,))
    sid = c.fetchone()
    c.close()
    conn.close()
    #log.error(sid)
    return ''.join(sid[0])

def populatevoters(inst):
    log.debug(f'populating vote table for {inst}')
    global votertable
    votertable = []
    pcnt = 0
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE server = ?', [inst])
    pdata = c.fetchall()
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
        if getvote(whoasked) == 99:
            mtxt = 'sorry, you are not eligible to vote in this round'
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
    subprocess.run('arkmanager rconcmd "ServerChat wild dino wipe voting has started with %s players. vote yes or no now" @%s' % (pon,inst), shell=True)
    votestarttime = time.time()
    sltimer = 0
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
                arewevoting = False
        else:
            if sltimer == 120 or sltimer == 240:
                log.info(f'sending voting waiting message to vote on {inst}')
                subprocess.run('arkmanager rconcmd "ServerChat wild dino wipe vote is waiting. make sure you have cast your vote yes or no." @%s' % (inst), shell=True)

        sltimer += 5
    log.info(f'final votertable for vote on {inst}')
    log.info(votertable)
    votertable = []
    lastvoter = time.time()
    resetlastvote(inst)
    log.info(f'voting thread has ended on {inst}')

def startvoter(inst,whoasked):
    global instance
    print(time.time()-float(getlastvote(inst)))
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
    #log.warning(rawline)
    #log.warning(rawname)
    #log.warning(rawname[0].lower())
    return rawname[0].lower()

def checkcommands(inst):
    cmdpipe = subprocess.Popen('arkmanager rconcmd getgamelog @%s' % (inst), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        whoasked = 'nobody' 
        if line.startswith('Running command') or line.startswith('Error:'):
            pass
        elif line.find('!help') != -1:
            whoasked = getnamefromchat(line)
            subprocess.run('arkmanager rconcmd "ServerChat Commands: lastdinowipe, lastrestart, vote, lastseen <playername>, playedtime <playername>, whoson <servername>" @%s' % (inst), shell=True)
            log.info(f'responded to help request on {inst} from {whoasked}')
        elif line.find('!lastdinowipe') != -1:
            whoasked = getnamefromchat(line)
            lastwipe = elapsedTime(time.time(),float(getlastwipe(inst)))
            subprocess.run('arkmanager rconcmd "ServerChat last wild dino wipe was %s ago" @%s' % (lastwipe, inst), shell=True)
            log.info(f'responded to a lastdinowipe query on {inst} from {whoasked}')
        elif line.find('!lastrestart') != -1:
            whoasked = getnamefromchat(line)
            lastrestart = elapsedTime(time.time(),float(getlastrestart(inst)))
            subprocess.run('arkmanager rconcmd "ServerChat last server restart was %s ago" @%s' % (lastrestart, inst), shell=True)
            log.info(f'responded to a lastrestart query on {inst} from {whoasked}')
        elif line.find('!lastseen') != -1:
            whoasked = getnamefromchat(line)
            rawseenname = line.split(':')
            orgname = rawseenname[1].strip()
            lsnname = rawseenname[2].split('!lastseen')
            seenname = lsnname[1].strip().lower()
            lsn = getlastseen(seenname)
            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lsn, inst), shell=True)
            log.info(f'responding to a lastseen request for {seenname} from {orgname}')
        elif line.find('!playedtime') != -1:
            whoasked = getnamefromchat(line)
            seenname = rawline[4].lower()
            lpt = gettimeplayed(seenname)
            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lpt, inst), shell=True)
            log.info(f'responding to a playedtime request for {seenname} on {inst} from {whoasked}')
        elif line.find('!whoson') != -1 or line.find('!whosonline') != -1:
            whoasked = getnamefromchat(line)
            rawline = line.split(':')
            lastlline = rawline[2].strip().split(' ')
            #log.warning(lastlline)
            if len(lastlline) == 2:
                ninst = lastlline[1] 
            else:
                ninst = inst
            whoisonlinewrapper(ninst,inst,whoasked)
        elif line.find('!vote') != -1 or line.find('!startvote') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to a dino wipe vote request on {inst} from {whoasked}')
            startvoter(inst,whoasked)
        elif line.find('!agree') != -1 or line.find('!yes') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to YES vote on {inst} from {whoasked}')
            castedvote(inst,whoasked,True)
        elif line.find('!disagree') != -1 or line.find('!no') != -1:
            whoasked = getnamefromchat(line)
            log.info(f'responding to NO vote on {inst} from {whoasked}')
            castedvote(inst,whoasked,False)

def clisten(inst):
    log.info(f'starting the command listener thread for {inst}')
    while True:
        try:
            checkcommands(inst)
            time.sleep(3)
        except:
            e = sys.exc_info()[0]
            log.critical(e)
