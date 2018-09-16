import logging, subprocess, sqlite3, time, threading
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

lastvoter = time.time()
votetable = []

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
            minstring = 'Minute'
        else:
            minstring = 'Min'
    else:
        if lshort is False:
            minstring = 'Minutes'
        else:
            minstring = 'Mins'
    hours = int(total_min / 60)
    if hours == 1:
        if lshort is False:
            hourstring = 'Hour'
        else:
            hourstring = 'Hr'
    else:
        if lshort is False:
            hourstring = 'Hours'
        else:
            hourstring = 'Hrs'
    days = int(hours / 24)
    if days == 1:
        if lshort is False:
            daystring = 'Day'
        else:
            daystring = 'Day'
    else:
        if lshort is False:
            daystring = 'Days'
        else:
            daystring = 'Days'
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
        minstring = 'Mins'
    hours = int(total_min / 60)
    if hours == 1:
        hourstring = 'Hour'
    else:
        hourstring = 'Hours'
    days = int(hours / 24)
    if days == 1:
        daystring = 'Day'
    else:
        daystring = 'Days'
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

def whoisonline(inst,oinst,whoasked):
    log.info(f'responding to a whoson request for {inst} from {whoasked}')
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

        subprocess.run('arkmanager rconcmd "ServerChat %s has %s players online: %s" @%s' % (inst, pcnt, plist, oinst), shell=True)

        c.close()
        conn.close()
    except:
        log.exception()
        subprocess.run('arkmanager rconcmd "ServerChat Server %s does not exist." @%s' % (inst, inst), shell=True)

def getlastvote(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastvote FROM instances WHERE name = ?', [inst])
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

def getsteamid(playernme):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT steamid FROM players WHERE playername = ?', (playernme,))
    sid = c.fetchone()
    c.close()
    conn.close()
    return ''.join(sid[0])

def populatevoters(inst):
    log.debug(f'populating vote table for {inst}')
    global votertable
    votertable = []
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE server = ?', [inst])
    pdata = c.fetchall()
    for row in pdata:
        chktme = time.time()-float(row[2])
        if chktme < 90:
            newvoter = [row[0],row[1],3]
            votertable.append(newvoter)
    log.error(votertable)




def castedvote(inst,whoasked,myvote):
    global votetable
    if not isvoting(inst):
        subprocess.run('arkmanager rconcmd "ServerChat no vote is taking place now" @%s' % (inst), shell=True)
    else:
        if myvote:
            mtxt = 'your YES vote has been cast'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)

        else:
            mtxt = 'your NO vote has been cast'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (getsteamid(whoasked), mtxt, inst), shell=True)



def voting(inst,whoasked):
    log.info(f'wild dino wipe voting has started for {inst}')
    global lastvoter
    populatevoters(inst)
    subprocess.run('arkmanager rconcmd "ServerChat wild dino wipe voting has started. agree or disagree now" @%s' % (inst), shell=True)
    time.sleep(60)
    lastvoter = time.time()
    log.info(f'voting thread has ended on {inst}')



    
    

def startvoter(inst,whoasked):
    if isvoting(inst):
        subprocess.run('arkmanager rconcmd "ServerChat voting has already started. cast your vote" @%s' % (inst), shell=True)
    elif time.time()-float(getlastvote(inst)) > 7200:   # 2 hours between votes  !!!!!! Reversed < for now to test, switch back!!
        rawtimeleft = 7200-(time.time()-float(getlastvote(inst)))
        timeleft = playedTime(rawtimeleft)
        subprocess.run('arkmanager rconcmd "ServerChat you must wait %s until next vote" @%s' % (timeleft,inst), shell=True)
    elif time.time()-float(lastvoter) > 600:  # 10 min between attempts   !!!! CHANGE BACK TO  <
        rawtimeleft = 600-(time.time()-lastvoter)
        timeleft = playedTime(rawtimeleft)
        subprocess.run('arkmanager rconcmd "ServerChat you must wait %s until next vote" @%s' % (timeleft,inst), shell=True)
    else:
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                instance[each]['votethread'] = threading.Thread(name = '%s-voter' % inst, target=voting, args=(inst,whoasked))
                instance[each]['votethread'].start()

def checkcommands(inst):
    cmdpipe = subprocess.Popen('arkmanager rconcmd getgamelog @%s' % (inst), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        rawline = line.split(' ')
        whoasked = rawline[1].lower()
        if line.startswith('Running command') or line.startswith('Error:'):
            pass
        elif line.find('!help') != -1:
            subprocess.run('arkmanager rconcmd "ServerChat Commands: lastdinowipe, lastrestart, lastseen <playername>, playedtime <playername>, whoson <servername>" @%s' % (inst), shell=True)
            log.info(f'responded to help request on {inst} from {whoasked}')
        elif line.find('!lastdinowipe') != -1:
            lastwipe = elapsedTime(time.time(),float(getlastwipe(inst)))
            subprocess.run('arkmanager rconcmd "ServerChat last wild dino wipe was %s ago" @%s' % (lastwipe, inst), shell=True)
            log.info(f'responded to a lastdinowipe query on {inst} from {whoasked}')
        elif line.find('!lastrestart') != -1:
            lastrestart = elapsedTime(time.time(),float(getlastrestart(inst)))
            subprocess.run('arkmanager rconcmd "ServerChat last server restart was %s ago" @%s' % (lastrestart, inst), shell=True)
            log.info(f'responded to a lastrestart query on {inst} from {whoasked}')
        elif line.find('!lastseen') != -1:
            rawseenname = line.split(':')
            orgname = rawseenname[1].strip()
            lsnname = rawseenname[2].split('!lastseen')
            seenname = lsnname[1].strip().lower()
            lsn = getlastseen(seenname)
            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lsn, inst), shell=True)
            log.info(f'responding to a lastseen request for {seenname} from {orgname}')
        elif line.find('!playedtime') != -1:
            seenname = rawline[4].lower()
            lpt = gettimeplayed(seenname)
            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (lpt, inst), shell=True)
            log.info(f'responding to a playedtime request for {seenname} on {inst} from {whoasked}')
        elif line.find('!whoson') != -1 or line.find('!whosonline') != -1:
            if len(rawline) == 5:
                ninst = rawline[4]
            else:
                ninst = inst
            whoson = whoisonline(ninst,inst,whoasked)
        elif line.find('!vote') != -1:
            log.info(f'responding to a dino wipe vote request on {inst} from {whoasked}')
            startvoter(inst,whoasked)
        elif line.find('!agree') != -1 or line.find('!yes') != -1:
            log.info(f'responding to YES vote on {inst} from {whoasked}')
            castedvote(inst,whoasked,True)
        elif line.find('!disagree') != -1 or line.find('!no') != -1:
            log.info(f'responding to NO vote on {inst} from {whoasked}')
            castedvote(inst,whoasked,False)

def clisten(inst):
    log.info(f'starting the command listener thread for {inst}')
    while True:
        checkcommands(inst)
        time.sleep(3)

