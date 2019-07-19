#!/usr/bin/env python3

from modules.configreader import instance, hstname, logfile, colorlogfile, debugfile, critlogfile, loglevel
from modules.dbhelper import dbquery, dbupdate
from modules.pushover import pushover
from modules.instances import getinststatus, isinstanceenabled
from arkupdater import restartinstnow
from sys import exit
from time import sleep
from modules.timehelper import Secs, Now, elapsedTime
import psutil
import argparse
from loguru import logger as log
import os
import sys
import subprocess

__author__ = "Ian Perry"
__copyright__ = "Copyright 2018, Galaxy Media"
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Ian Perry"
__email__ = "ianperry99@gmail.com"
__progname__ = "pyark-daemon"
__description__ = "ark instance watchdog service"
__detaildesc__ = ""
__name__ = "arkwatchdog"

parser = argparse.ArgumentParser(prog=__progname__)
parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))
parser.add_argument('-q', '--quiet', action='store_true',
                    help='supress logging output to console. default: error logging')
parser.add_argument('-d', '--debug', action='store_true', help='verbose output (debug)')
parser.add_argument('-t', '--trace', action='store_true', help='super verbose output (trace)')
args = parser.parse_args()


logformat = '{time:YYYY-MM-DD HH:mm:ss.SSS} | {extra[hostname]: <5} | {level: <6} | {message} | {name}:{function}:{line}'

colorlogformat = '<level>{time:YYYY-MM-DD HH:mm:ss.SSS}</level> | <level>{extra[hostname]: <5}</level> | <level>{level: <6}</level> | <level>{message: <75}</level> | <fg 109>{name}:{function}:{line}</fg 109>'


log.configure(extra={'hostname': hstname, 'instance': 'MAIN'})

log.level("START", no=38, color="<light-yellow>", icon="¤")
log.level("WATCH", no=38, color="<light-yellow>", icon="¤")
log.level("UPDATE", no=20, color="<light-cyan>", icon="¤")
log.level("MAINT", no=20, color="<fg 86>", icon="¤")
log.level("TEST", no=5, color="<light-red>", icon="¤")

# Console Logging
if args.quiet:
    log.add(sink=sys.stderr, level=50, backtrace=False, diagnose=False, colorize=False, format=logformat)
elif args.trace:
    log.add(sink=sys.stdout, level=5, backtrace=True, diagnose=True, colorize=True, format=colorlogformat)
elif args.debug:
    log.add(sink=sys.stdout, level=10, backtrace=True, diagnose=True, colorize=True, format=colorlogformat)
else:
    log.add(sink=sys.stdout, level=20, backtrace=True, diagnose=True, colorize=True, format=colorlogformat)

# Info Logging pyark.log
log.add(sink=logfile, level=20, enqueue=True, backtrace=False, diagnose=False, colorize=False, format=logformat, rotation="1 day", retention="30 days", compression="gz")

# Info Color Logging pyark-color.log
log.add(sink=colorlogfile, level=20, enqueue=True, backtrace=False, diagnose=False, colorize=True, format=colorlogformat, rotation="1 day", retention="30 days", compression="gz")

# Debug Logging debug.log
if loglevel == 'DEBUG' or loglevel == 'TRACE' or args.debug or args.trace:
    if loglevel == 'DEBUG' or args.debug:
        lev = 10
    else:
        lev = 5
    log.add(sink=debugfile, level=lev, enqueue=True, backtrace=True, diagnose=True, colorize=True, format=colorlogformat, rotation="1 MB", retention="30 days", compression="gz", delay=True)

# Crit Logging admin.log
log.add(sink=critlogfile, level=40, enqueue=True, backtrace=True, diagnose=True, colorize=True, format=colorlogformat, rotation="1 MB", retention="30 days", compression="gz", delay=True)


def issharedmounted():
    return os.path.ismount('/home/ark/shared')


def float_trunc_1dec(num):
    try:
        tnum = num // 0.1 / 10
    except:
        return False
    else:
        return tnum


def serverneedsrestart():
    if os.path.isfile('/var/run/reboot-required'):
        return True
    else:
        return False


def arkprocesscpu(inst):
    arkprocess = psutil.Process(getinstpid(inst))
    return arkprocess.cpu_percent(interval=2)


def getlaststart(inst):
    laststart = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (inst,), fetch='one', single=True)
    return laststart


def getserveruptime():
    return elapsedTime(Now(), psutil.boot_time())


def getcpustats():
    rawcpuload = psutil.getloadavg()
    numcores = psutil.cpu_count()
    cpufreq = psutil.cpu_freq()[0] / 1000
    load1 = (rawcpuload[0] / numcores) * 100
    load5 = (rawcpuload[1] / numcores) * 100
    load15 = (rawcpuload[2] / numcores) * 100
    return numcores, float_trunc_1dec(cpufreq), float_trunc_1dec(load1), float_trunc_1dec(load5), float_trunc_1dec(load15)


def getservermem():
    process = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE)
    out, err = process.communicate()
    lines = []
    lines = out.decode().split('\n')
    memvalues = lines[1].strip().split()
    swapvalues = lines[2].strip().split()
    memfree = memvalues[3]
    memavailable = memvalues[6]
    swapused = swapvalues[2]
    return memfree, memavailable, swapused


def getinstpid(inst):
    pidfile = f'/home/ark/ARK/ShooterGame/Saved/.arkserver-{inst}.pid'
    file = open(pidfile, 'r')
    arkpid = file.read()
    file.close()
    return int(arkpid)


def didserverjustboot():
    rawuptime = subprocess.run('tail /proc/uptime', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
    rawup = rawuptime.stdout.decode('utf-8').split(' ')
    if float(rawup[0]) < Secs['3min']:
        return True
    else:
        return False


def getinstmem(inst):
    instpid = getinstpid(inst)
    rawsts = subprocess.run('ps -p %s -o rss,vsz' % (instpid), stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, shell=True)
    instrss, instvsz = rawsts.stdout.decode('utf-8').split('\n')[1].split(' ')
    instrss = int(instrss) / 1000000 // 0.01 / 100
    instvsz = int(instvsz) / 1000000 // 0.01 / 100
    return instrss, instvsz


def checkpyark():
    for line in open('/tmp/pyark.lock', 'r'):
        pyarkpid = line
    if psutil.pid_exists(pyarkpid):
        pyarkproc = psutil.Process(pid=pyarkpid)
        print(pyarkproc.name())
        print(pyarkproc.exe())
        print(pyarkproc.status())
    else:
       print('no such process')

def startserver(inst, reason, restart=False):
    if issharedmounted():
        if loglevel != 'DEBUG' or loglevel != 'TRACE' or not args.debug or not args.trace:
            restartinstnow(inst)
        else:
            log.log('WATCH', f'Instance [{inst.title()}] Debug mode stops start/restart...')
    else:
        log.warning(f'Server {hstname} is waiting for drives to mount')


def main():
    isrunning = {}
    isonline = {}
    for seat in instance:
        isrunning[seat['name']] = {}
        isrunning[seat['name']].update({'isit': 0, 'count': 0})
        isonline[seat['name']] = {}
        isonline[seat['name']].update({'isit': 0, 'count': 0})
    log.log('START', f'Instance Watchdog Daemon is starting on {hstname}')
    if didserverjustboot():
        log.log('WATCH', 'server just booted, starting instances for the first time')
        while not issharedmounted():
            log.log('WATCH', 'Shared drive is not mounted, waiting for mount to complete...')
            sleep(60)
        if issharedmounted():
            for eat in instance:
                subprocess.run('arkmanager start @%s' % (eat['name']), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, shell=True)
                sleep(120)
            log.debug('sleeping 15 min while instances start')
            log.sleep(Secs['10min'])
    log.debug('starting watchdog loop')
    serverstatcount = 0
    while True:
        try:
            if serverstatcount == 5:
                serverstatcount = 0
            serverstatcount += 1
            if serverstatcount == 1:
                log.debug(f'Updating server stats for server {hstname.upper()}')
                memfree, memavail, swapused = getservermem()
                cpucores, cpufreq, cpuload1, cpuload5, cpuload15 = getcpustats()
                uptime = getserveruptime()

            for eachinst in instance:
                if isinstanceenabled(eachinst['name']):
                    isitrunning, isitonline = getinststatus(eachinst['name'])
                    if isitrunning:
                        log.debug(f'{eachinst["name"]} passed instance running check')
                        log.debug(f'updating process stats for {eachinst["name"]}')
                        arkservercpu = float_trunc_1dec(arkprocesscpu(eachinst["name"]))
                        actmem, totmem = getinstmem(eachinst['name'])
                        dbupdate("UPDATE instances SET actmem = '%s', totmem = '%s', arkcpu = '%s' WHERE name = '%s'" % (actmem, totmem, arkservercpu, eachinst['name']))
                        for neach in isrunning.copy():
                            if neach == eachinst['name']:
                                isrunning[neach].update({'isit': 1, 'count': 0})
                    elif int(getlaststart(eachinst['name'])[0]) > Secs['3min']:
                        log.warning(f'[{eachinst["name"].title()}] failed instance running check ({isrunning[neach]["count"] + 1}/3)')
                        for neach in isrunning.copy():
                            if neach == eachinst['name']:
                                isrunning[neach].update({'isit': 0, 'count': isrunning[neach]['count'] + 1})
                    else:
                        log.debug(f'skipping running check for 3 min startup for {eachinst["name"]}')

                    if isitrunning and not isitonline and Now() - int(getlaststart(eachinst['name'])[0]) > Secs['10min']:
                        log.warning(f'[{eachinst["name"].title()}] failed instance online check ({isonline[neach]["count"] + 1}/10)')
                        for neach in isonline.copy():
                            if neach == eachinst['name']:
                                isonline[neach].update({'isit': 0, 'count': isonline[neach]['count'] + 1})
                    elif isitonline:
                        log.debug(f'{eachinst["name"]} passed instance online check')
                        dbupdate("UPDATE instances SET uptimestamp = '%s' WHERE name = '%s'" % (Now(), eachinst['name']))
                        for neach in isonline.copy():
                            if neach == eachinst['name']:
                                isonline[neach].update({'isit': 1, 'count': 0})
                    else:
                        log.debug(f'skipping online check for 10 min startup for {eachinst["name"]}')

                    for feach in isrunning:
                        if feach == eachinst['name']:
                            if isrunning[feach]['count'] == 3:
                                isrunning[feach].update({'isit': 0, 'count': 0})
                                isonline[feach].update({'isit': 0, 'count': 0})
                                log.warning(f'Instance [{eachinst["name"]}] failed running checks! Starting Instance')
                                pmsg = f'Instance {eachinst["name"]} failed running checks!\nStarting Instance'
                                pushover('Watchdog', pmsg)
                                startserver(eachinst['name'], restart=False)
                    for feach in isonline:
                        if feach == eachinst['name']:
                            if isonline[feach]['count'] == 10:
                                isrunning[feach].update({'isit': 0, 'count': 0})
                                isonline[feach].update({'isit': 0, 'count': 0})
                                log.warning(f'Instance [{eachinst["name"]}] failed online checks! Restarting Instance')
                                pmsg = f'Instance {eachinst["name"]} failed online checks!\nRestarting Instance'
                                pushover('Watchdog', pmsg)

                                startserver(eachinst['name'], 'online')

                    if serverstatcount == 1:
                        dbupdate("UPDATE instances SET serverhost = '%s', svrmemfree = '%s', svrmemavail = '%s', svrswapused = '%s', cpucores = '%s', cpufreq = '%s', cpuload1 = '%s', cpuload5 = '%s', cpuload15 = '%s', serveruptime = '%s' WHERE name = '%s'" % (hstname, int(memfree), int(memavail), int(swapused), int(cpucores), cpufreq, cpuload1, cpuload5, cpuload15, uptime, eachinst['name']))

        except KeyboardInterrupt:
            log.critical('Keyboard Interrupt Detected, Exiting.')
            exit()
        except:
            log.exception('Critical Error in Ark Watchdog!')
        log.debug('sleeping 1 min between checks')
        try:
            log.trace(f'running:{isrunning}')
            log.trace(f'online:{isonline}')
            sleep(Secs['1min'])
        except KeyboardInterrupt:
            log.critical('Keyboard Interrupt Detected, Exiting.')
            exit()


if __name__ == 'arkwatchdog':
    main()
