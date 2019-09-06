import asyncio
import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config
from fastapi import FastAPI
from modules.asyncdb import asyncDB

api = FastAPI()
config = Config()
config.bind = ["172.31.250.115:8080"]
db = asyncDB(min=1, max=5)


@api.on_event("startup")
async def startup_event():
    await db.connect()


@api.on_event("shutdown")
async def shutdown_event():
    await db.close()


@api.get('/players/online')
async def players_online():
    players = await db.fetchall('SELECT * FROM players WHERE online = True')
    allplayers = []
    for player in players:
        allplayers.append(player['playername'])
    return {'players': len(players), 'names': allplayers}


@api.get('/servers/status')
async def servers_status():
    insts = await db.fetchall('SELECT * FROM instances')
    nap = []
    for inst in insts:
        if inst['isup'] == 1:
            if inst['needsrestart'] == "True":
                status = 'restarting'
            else:
                status = "online"
        else:
            status = "offline"
        nap.append(status)
    return nap

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
asyncloop = asyncio.new_event_loop()
asyncio.set_event_loop(asyncloop)
asyncloop.run_until_complete(serve(api, config))
