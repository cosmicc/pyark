from fastapi import FastAPI
from modules.asyncdb import asyncDB
from modules.redis import instancevar, globalvar, instancestate

app = FastAPI(openapi_prefix="/api")

db = asyncDB()


@app.on_event("startup")
async def startup():
    await db.connect(min=1, max=5, timeout=60)


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.get('/servers/status')
async def servers_status():
    instances = await globalvar.getlist('allinstances')
    statuslist = ()
    for inst in instances:
        if await instancevar.getint(inst, 'islistening') == 1:
            if await instancestate.check(inst, 'restartwaiting'):
                status = 'restarting'
            else:
                status = 'online'
        else:
            status = 'offline'
        statuslist = statuslist + ((status,))
    return statuslist


@app.get("/players/online")
async def players_online():
    return await db.fetchone(f"SELECT COUNT(*) FROM players WHERE online = True")


@app.get("/players/info")
async def players_info(steamid=None, playername=None):
    if steamid:
        player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
        if player:
            return player, 200
        else:
            return {'message': 'steamid does not exist'}, 400
    elif playername:
        player = await db.fetchone(f"SELECT * FROM players WHERE playername = '{playername}'")
        if player:
            return player, 200
        else:
            return {'message': 'playername does not exist'}, 400
    else:
        return {'message': 'you must specify a steamid or playermame'}, 400


@app.route('/servers/info')
async def servers_info(servername=None):
    instances = await globalvar.getlist('allinstances')
    if servername is not None:
        if servername in instances:
            return await db.fetchone(f"SELECT * FROM instances WHERE name = '{servername}'"), 200
        else:
            return {'message': 'invalid server name'}, 400
    else:
        return {'message': 'you must specify a server name'}, 400


@app.get("/")
def read_root():
    return {"try": "/docs"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
