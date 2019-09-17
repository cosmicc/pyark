from fastapi import FastAPI
from modules.asyncdb import asyncDB
from modules.redis import instancevar, globalvar, instancestate

app = FastAPI()

db = asyncDB()


@app.on_event("startup")
async def startup():
    db = asyncDB()
    await db.connect(min=1, max=5, timeout=60)


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.get('/servers/status')
async def servers_status():
    instances = await globalvar.getlist('allinstances')
    statuslist = ()
    for inst in instances:
        if instancevar.getint(inst, 'islistening') == 1:
            if instancestate.check(inst, 'restartwaiting'):
                status = 'restarting'
            else:
                status = 'online'
        else:
            status = 'offline'
        statuslist = statuslist + ((status,))


@app.get("/players/online")
async def players_online():
    return await db.fetchone(f"SELECT COUNT(*) FROM players WHERE online = True")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
