from quart import Quart, websocket, render_template
from datetime import timedelta
from modules.asyncdb import asyncDB
from modules.redis import RedisClass
from modules.timehelper import Now, Secs, elapsedTime
from modules.clusterevents import asyncgetcurrenteventinfo, asyncgetnexteventinfo, d2dt_maint


webapp = Quart(__name__)


@webapp.context_processor
async def _itemauctiondata():
    async def itemauctiondata():
        return iter(await webapp.db.fetchall(f"SELECT * FROM auctiondata WHERE auctiontype = 'Item'"))
    return dict(itemauctiondata=await itemauctiondata())


@webapp.context_processor
async def _dinoauctiondata():
    async def dinoauctiondata():
        return iter(await webapp.db.fetchall(f"SELECT * FROM auctiondata WHERE auctiontype = 'Dino'"))
    return dict(dinoauctiondata=await dinoauctiondata())


@webapp.context_processor
async def _eventinfo():
    async def eventinfo():
        event = await asyncgetcurrenteventinfo()
        if not event:
            event = await asyncgetnexteventinfo()
            return {'active': False, 'title': event['title'], 'description': event['description'], 'timeleft': elapsedTime(d2dt_maint(event['starttime']), Now())}
        else:
            return {'active': True, 'title': event['title'], 'description': event['description'], 'timeleft': elapsedTime(d2dt_maint(event['endtime']), Now())}
    return dict(eventinfo=await eventinfo())


@webapp.context_processor
async def _currentlottery():
    async def currentlottery():
        now = Now('dt')
        lottery = await webapp.db.fetchone(
            f"""SELECT * FROM lotteryinfo WHERE completed = False and winner = 'Incomplete' and startdate <= '{now}' ORDER BY id DESC"""
        )
        if not lottery:
            nextlotterystart = await webapp.db.fetchone(f"""SELECT startdate from lotteryinfo WHERE completed = False and winner = 'Incomplete' and startdate > '{now}' ORDER BY id DESC""")
            if nextlotterystart:
                return {
                    "active": False,
                    "playercount": 0,
                    "payout": 0,
                    "ends": elapsedTime(nextlotterystart["startdate"], Now(), nowifmin=False),
                }
            else:
                return {
                    "active": False,
                    "playercount": 0,
                    "payout": 0,
                    "ends": "1 Hour",
                }
        else:
            lotterynames = await webapp.db.fetchall(
                f"SELECT playername FROM lotteryplayers ORDER BY TIMESTAMP ASC"
            )
            resp = []
            for player in iter(lotterynames):
                resp.append(player["playername"].title())
            return {
                "active": True,
                "playercount": lottery["players"],
                "payout": lottery["payout"],
                "ends": elapsedTime(lottery["startdate"] + timedelta(hours=lottery["days"]), Now(), nowifmin=False),
                "players": ", ".join(resp),
            }

    return dict(currentlottery=await currentlottery())


@webapp.context_processor
async def _newplayers():
    async def newplayers():
        nplayers = await webapp.db.fetchall(
            f"SELECT playername FROM players WHERE firstseen > {Now() - Secs['week']} ORDER BY firstseen DESC"
        )
        num = 0
        resp = []
        for player in iter(nplayers):
            num = num + 1
            resp.append(player['playername'].title())
        return {'count': num, 'names': ', '.join(resp)}
    return dict(newplayers=await newplayers())


@webapp.context_processor
async def _last7lotterys():
    async def last7lotterys():
        lotterys = await webapp.db.fetchall(
            f"SELECT winner, payout FROM lotteryinfo WHERE completed = True ORDER BY id DESC LIMIT 7"
        )
        num = 0
        resp = []
        for lottery in iter(lotterys):
            num = num + 1
            resp.append(
                {
                    "num": num,
                    "playername": lottery["winner"],
                    "points": lottery["payout"],
                }
            )
        return resp

    return dict(last7lotterys=await last7lotterys())


@webapp.context_processor
async def _lastlottery():
    async def lastlottery():
        return await webapp.db.fetchone(
            f"SELECT * FROM lotteryinfo WHERE completed = True ORDER BY id DESC"
        )

    return dict(lastlottery=await lastlottery())


@webapp.context_processor
async def _otherplayercounts():
    async def otherplayercounts():
        wcount = await webapp.db.fetchone(
            f"""SELECT COUNT(*) FROM players WHERE banned = '' AND lastseen >= '{Now() - Secs["week"]}'"""
        )
        mcount = await webapp.db.fetchone(
            f"""SELECT COUNT(*) FROM players WHERE banned = '' AND lastseen >= '{Now() - Secs["month"]}'"""
        )
        return {"week": wcount["count"], "month": mcount["count"]}

    return dict(otherplayercounts=await otherplayercounts())


@webapp.context_processor
async def _dailyplayers():
    async def dailyplayers():
        pnames = await webapp.db.fetchall(
            f"""SELECT playername FROM players WHERE banned = '' AND lastseen >= '{Now() - Secs["1day"]}' ORDER BY lastseen DESC"""
        )
        playernamelist = []
        for player in iter(pnames):
            playernamelist.append(player["playername"].title())
        playernames = ", ".join(playernamelist)
        count = len(playernamelist)
        return {"count": count, "names": playernames}

    return dict(dailyplayers=await dailyplayers())


@webapp.context_processor
async def _onlineplayers():
    async def onlineplayers():
        pnames = await webapp.db.fetchall(
            f"SELECT playername from players where online = True ORDER BY lastconnect DESC"
        )
        playernamelist = []
        for player in iter(pnames):
            playernamelist.append(player["playername"].title())
        playernames = ", ".join(playernamelist)
        count = len(playernamelist)
        return {"count": count, "names": playernames}

    return dict(onlineplayers=await onlineplayers())


@webapp.context_processor
async def _instancestats():
    async def instancestats():
        inatancedata = await webapp.db.fetchall(
            f"SELECT name, lastdinowipe, lastrestart, lastvote, restartreason, arkversion, rank, score, votes, connectingplayers, activeplayers, isup, arkbuild, hostname FROM instances ORDER BY name DESC"
        )
        returnlist = []
        for idata in instancedata:
            returnlist.append({'name': idata['name'], 'lastdinowipe': elapsedTime(Now(), idata['lastdinowipe']), 'lastrestart': elapsedTime(Now(), idata['lastrestart']), 'lastvote': elapsedTime(Now(), idata['lastvote']), 'restartreason': idata['restartreason'], 'arkversion': idata['arkversion'], 'rank': idata['rank'], 'score': idata['score'], 'votes': idata['votes'], 'connectingplayers': idata['connectingplayers'], 'activeplayers': idata['activeplayers'], 'isup': idata['isup'], 'arkbuild': idata['arkbuild'], 'hostname': idata['hostname']})
        return returnlist
    return dict(instancestats=iter(await instancestats()))


@webapp.context_processor
async def _instancedata():
    async def instancedata():
        return await webapp.db.fetchall(
            f"SELECT name, islistening, isup, needsrestart, restartcountdown, enabled, steamlink, activeplayers FROM instances ORDER BY name DESC"
        )
    return dict(instancedata=iter(await instancedata()))


@webapp.context_processor
async def _gallerylinks():
    async def gallerylinks():
        return iter(
            await webapp.db.fetchall(
                f"SELECT playername, link FROM gallerylinks ORDER BY id ASC"
            )
        )

    return dict(gallerylinks=iter(await gallerylinks()))


@webapp.before_serving
async def db_pool():
    webapp.db = asyncDB()
    await webapp.db.connect(min=3, max=20, timeout=240)


@webapp.before_serving
async def redis_pool():
    Redis = RedisClass()
    webapp.redis = Redis.redis


@webapp.after_serving
async def db_close():
    await webapp.db.close()


@webapp.route("/")
async def index():
    return await render_template("home.html")


@webapp.websocket("/ws")
async def ws():
    while True:
        await websocket.send("hello")
