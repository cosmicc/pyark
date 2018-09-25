import sqlite3, json
from urllib.request import urlopen
from configreader import *

sqldb = f'{sharedpath}/db/pyark.db'

def fetchauctiondata(steamid):
    try:
        data = urlopen(f"https://linode.ghazlawl.com/ark/mods/auctionhouse/api/json/v1/auctions/?PlayerSteamID={steamid}").read()
        data = data.decode()[:-20].encode()
        adata = json.loads(data)
        auctions = adata['Auctions']
        if auctions:
            return auctions
        else:
            return False
    except:
        return False

def getauctionstats(auctiondata):
    if auctiondata != False:
        numdinos = 0
        numitems = 0
        numauctions = len(auctiondata)
        for eauct in auctiondata:
            if eauct['Type'] == 'Dino':
                numdinos += 1
            elif eauct['Type'] == 'Item':
                numitems += 1
        return numauctions, numitems, numdinos
    else:
        return 0, 0, 0

def writeauctionstats(steamid,numauctions,numitems,numdinos):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('UPDATE players SET totalauctions = ?, itemauctions = ?, dinoauctions = ? WHERE steamid = ?', (numauctions,numitems,numdinos,steamid))
    conn4.commit()
    c4.close()
    conn4.close()

