#!/usr/bin/python3

import time, logging, sqlite3, subprocess, socket
from configreader import *

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

def gchatrelay(inst):
    while True:
        try:
            conn3 = sqlite3.connect(sqldb)
            c3 = conn3.cursor()
            c3.execute('SELECT * FROM globalbuffer')
            cbuff = c3.fetchall()
            c3.close()
            conn3.close()
            if cbuff:
                for each in cbuff:
                    if each[1] == 'ALERT' and float(each[4]) > time.time()-3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (each[3],inst), shell=True)
                    elif each[1] != inst and float(each[4]) > time.time()-3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s@%s: %s" @%s' % (each[2].capitalize(),each[1].capitalize(),each[3],inst), shell=True)
                    if float(each[4]) < time.time()-10:
                        conn3 = sqlite3.connect(sqldb)
                        c3 = conn3.cursor()
                        c3.execute('DELETE FROM globalbuffer WHERE id = ?', (each[0],))
                        conn3.commit()
                        c3.close()
                        conn3.close()
            time.sleep(3)
        except:
            log.critical('Critical Error in Global Chat Relayer!', exc_info=True)
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

