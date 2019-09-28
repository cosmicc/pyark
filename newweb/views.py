from quart import Quart, websocket, render_template
from modules.asyncdb import asyncDB
from modules.redis import RedisClass
from modules.timehelper import Now, Secs


webapp = Quart(__name__)


@webapp.context_processor
async def _currentlottery():
    async def currentlottery():
        lottery = await webapp.db.fetchone(
            f"SELECT * FROM lotteryinfo WHERE completed = False"
        )
        if not lottery:
            return {"active": False, "playercount": 0, "payout": 0, "ends": 0}
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
                "ends": 0,
                "players": ", ".join(resp),
            }

    return dict(currentlottery=await currentlottery())


@webapp.context_processor
async def _newplayers():
    async def newplayers():
        nplayers = await webapp.db.fetchall(
            f"SELECT playername FROM players WHERE firstseen > {Now() - Secs['week']} ORDER BY firsseen DESC"
        )
        num = 0
        resp = []
        for player in iter(nplayers):
            num = num + 1
            resp.append(player)
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
async def _instancedata():
    async def instancedata():
        return await webapp.db.fetchall(
            f"SELECT name, isup, needsrestart, restartcountdown, enabled, steamlink, activeplayers FROM instances ORDER BY name"
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
