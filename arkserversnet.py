from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import Secs
from time import sleep
from urllib.request import urlopen, Request
import json
import logging
import socket

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def fetchurldata(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urlopen(req).read()
    return json.loads(html)


def fetcharkserverdata():
    hinst = dbquery('SELECT name from instances')
    for each in hinst:
        svrifo = dbquery("SELECT * from instances WHERE name = '%s'" % (each[0],), fetch='one')
        try:
            url = f'https://ark-servers.net/api/?object=servers&element=detail&key={svrifo[8]}'
            adata = fetchurldata(url)
        except:
            log.error(f'Error fetching ArkServers data from web')
        else:
            if adata is not None:
                dbupdate("UPDATE instances SET hostname = '%s', rank = '%s', score = '%s', uptime = '%s', votes = '%s' WHERE name = '%s'" % (adata['hostname'], adata['rank'], adata['score'], adata['uptime'], adata['votes'], each[0]))


def arkserversnet():
    log.debug(f'Starting ArkServersNet Data Puller')
    while True:
        fetcharkserverdata()
        sleep(Secs['15min'])
