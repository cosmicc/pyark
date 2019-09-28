
from fastapi import FastAPI, Form, HTTPException
from modules.asyncdb import asyncDB
from modules.redis import globalvar, instancestate, instancevar, redis
from modules.servertools import stripansi, asyncglobalbuffer
from starlette.responses import Response

app = FastAPI(openapi_prefix="/api")

db = asyncDB()

'''
async def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'X-API-KEY' in request.headers:
            token = request.headers['X-API-KEY']
        if not token:
            apilog.warning(f'API request without a token')
            return {'message': 'Not Authorized'}, 401
        pkeys = dbquery("SELECT * FROM players WHERE apikey = '%s'" % (token,), fmt='dict', fetch='one')
        if pkeys is None:
            apilog.warning(f'API request invalid token: {token}')
            return {'message': 'Invalid Token'}, 401
        if pkeys['banned'] == 'True':
            apilog.warning(f'API request from banned player: {pkeys[0]} token: {token}')
            return {'message': 'You are Banned'}, 401
        apilog.info(f'API request granted for player: {pkeys["playername"]} steamid: {pkeys["steamid"]}')
        return f(*args, **kwargs)
    return decorated
'''


@app.on_event("startup")
async def startup():
    await db.connect(min=1, max=5, timeout=60)


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.post('/serverchat')
async def server_chat(chatline: str = Form(...)):
    await asyncglobalbuffer(chatline)
    return chatline


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


@app.get("/players/info", status_code=200)
async def players_info(response: Response, steamid=None, playername=None):
    if steamid:
        player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
        if player:
            return {'player_info': player}
        else:
            response.status_code = 400
            return {'message': 'steamid does not exist'}
    elif playername:
        player = await db.fetchone(f"SELECT * FROM players WHERE playername = '{playername}'")
        if player:
            return {'player_info': player}
        else:
            response.status_code = 400
            return {'message': 'playername does not exist'}
    else:
        response.status_code = 400
        return {'message': 'you must specify a steamid or playermame'}


@app.get('/servers/info', status_code=200)
async def servers_info(response: Response, servername=None):
    instances = await globalvar.getlist('allinstances')
    if servername is not None:
        if servername in instances:
            return {'server_info': await db.fetchone(f"SELECT * FROM instances WHERE name = '{servername}'")}
        else:
            response.status_code = 400
            return {'message': 'invalid server name'}
    else:
        response.status_code = 400
        return {'message': 'you must specify a server name'}


@app.get('/servers/states', status_code=200)
async def servers_states(response: Response, servername=None):
    instances = await globalvar.getlist('allinstances')
    if servername is not None:
        if servername in instances:
            return {'server_states': await instancestate.getlist(servername)}
        else:
            response.status_code = 400
            return {'message': 'invalid server name'}
    else:
        response.status_code = 400
        return {'message': 'you must specify a server name'}


@app.get('/servers/vars', status_code=200)
async def servers_vars(response: Response, servername=None):
    instances = await globalvar.getlist('allinstances')
    if servername is not None:
        if servername in instances:
            return {'server_vars': await instancevar.getall(servername)}
        else:
            response.status_code = 400
            return {'message': 'invalid server name'}
    else:
        response.status_code = 400
        return {'message': 'you must specify a server name'}


@app.get('/logs/pyark', status_code=200)
async def logs_pyark(response: Response, lines=1):
    getlines = await redis.zcard('pyarklog')
    if int(lines) > int(getlines):
        lines = int(getlines)
    startlines = int(getlines) - int(lines)
    loglines = await redis.zrange('pyarklog', startlines, int(getlines))
    if loglines:
        return {'pyark_log': stripansi(loglines)}
    else:
        return {'pyark_log': None}


@app.get('/logs/game', status_code=200)
async def logs_game(response: Response, lines=1):
    getlines = await redis.zcard('glhistory')
    if getlines is not None:
        if int(lines) > int(getlines):
            lines = int(getlines)
        startlines = int(getlines) - int(lines)
        loglines = await redis.zrange('glhistory', startlines, int(getlines))
        return {'game_log': stripansi(loglines)}
    else:
        return {'game_log': None}


@app.get('/logs/chat', status_code=200)
async def logs_chat(response: Response, lines=1):
    getlines = await redis.zcard('clhistory')
    if getlines is not None:
        if int(lines) > int(getlines):
            lines = int(getlines)
        startlines = int(getlines) - int(lines)
        loglines = await redis.zrange('clhistory', startlines, int(getlines))
        return {'chat_log': stripansi(loglines)}
    else:
        return {'chat_log': None}


@app.get("/")
def read_root():
    raise HTTPException(status_code=444)
