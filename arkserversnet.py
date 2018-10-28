import json, socket, sqlite3, logging
from time import sleep
from configreader import sqldb
from urllib.request import urlopen, Request

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def fetcharkserverdata():
    conn8 = sqlite3.connect(sqldb)
    c8 = conn8.cursor()
    c8.execute('SELECT name from instances')
    hinst = c8.fetchall()
    c8.close()
    conn8.close()
    for each in hinst:
        conn8 = sqlite3.connect(sqldb)
        c8 = conn8.cursor()
        c8.execute('SELECT * from instances WHERE name = ?', (each[0],))
        svrifo = c8.fetchone()
        c8.close()
        conn8.close()
        try:
            url = f'https://ark-servers.net/api/?object=servers&element=detail&key={svrifo[8]}'
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urlopen(req).read()
            adata = json.loads(html)
        except:
            pass
        else:
            if adata is not None:
                conn8 = sqlite3.connect(sqldb)
                c8 = conn8.cursor()
                c8.execute('UPDATE instances SET hostname = ?, rank = ?, score = ?, uptime = ?, votes = ?, arkversion = ? WHERE name = ?', (adata['hostname'], adata['rank'], adata['score'], adata['uptime'], adata['votes'], adata['version'], each[0]))
                conn8.commit()
                c8.close()
                conn8.close()


def arkserversnet():
    log.info(f'Starting ArkServersNet Data Puller')
    while True:
        fetcharkserverdata()
        sleep(1800)
