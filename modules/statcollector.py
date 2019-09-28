from datetime import time as dt
from datetime import datetime

from modules.asyncdb import DB as db
from loguru import logger as log
from modules.players import asyncgetactiveplayers, asyncgethitnruns, asyncgetnewplayers
from modules.redis import globalvar, instancevar
from modules.timehelper import Now, Secs
from timebetween import is_time_between


async def addvalue(inst, value):
    await db.update(
        f"INSERT INTO {inst.lower()}_stats (date, value) VALUES ('{datetime.now().replace(microsecond=0)}', {value})"
    )


@log.catch
async def asyncstatcollector():
    t, s, e = datetime.now(), dt(9, 0), dt(9, 5)  # 9:00am GMT (5:00AM EST)
    dailycollect = is_time_between(t, s, e)
    if dailycollect:
        await db.update(
            "INSERT INTO clusterstats (timestamp, dailyactive, weeklyactive, monthlyactive, dailyhnr, dailynew) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')"
            % (
                Now(fmt="dt"),
                len(await asyncgetactiveplayers(Secs["day"])),
                len(await asyncgetactiveplayers(Secs["week"])),
                len(await asyncgetactiveplayers(Secs["month"])),
                len(await asyncgethitnruns(Secs["day"])),
                len(await asyncgetnewplayers(Secs["day"])),
            )
        )
    for inst in await globalvar.getlist("allinstances"):
        await addvalue(inst, await instancevar.getint(inst, "playersonline"))
