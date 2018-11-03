from dbhelper import dbupdate
from urllib.request import urlopen
import json


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
    if auctiondata:
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


def writeauctionstats(steamid, numauctions, numitems, numdinos):
    dbupdate("UPDATE players SET totalauctions = '%s', itemauctions = '%s', dinoauctions = '%s' WHERE steamid = '%s'" % (numauctions, numitems, numdinos, steamid))
