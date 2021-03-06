from datetime import time as dt
from datetime import datetime, timedelta
from random import choice

from asyncpg import Record
import asyncio
from loguru import logger as log
from modules.asyncdb import DB as db
from modules.dbhelper import dbquery
from modules.redis import globalvar
from modules.timehelper import Now, datetimeto, elapsedTime, estshift
from numpy.random import randint, seed
from timebetween import is_time_between
from typing import Tuple


def isinlottery():
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False")
    if linfo:
        return True
    else:
        return False


def getlotteryplayers(fmt):
    linfo = dbquery("SELECT playername FROM lotteryplayers", fmt=fmt)
    return linfo


async def asyncisinlottery() -> bool:
    """Return if a lottery is currently running

    Returns:
        bool:
    """
    linfo = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
    if linfo:
        return True
    else:
        return False


async def asyncwritediscord(
    msg: str, tstamp: str, server: str = "generalchat", name: str = "ALERT"
) -> None:
    """Write to discord

    Args:
        msg (str): Description:
        tstamp (str): Description:
        server (str, [Optional]): Description:
        name (str, [Optional]): Description:
    """
    await db.update(
        f"INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('{server}', '{name}', '{msg}', '{tstamp}')"
    )


async def asyncwriteglobal(inst: str, whos: str, msg: str) -> None:
    await db.update(
        f"INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('{inst}', '{whos}', '{msg}', '{Now()}')"
    )


async def asyncgetlastlotteryinfo() -> Record:
    return await db.fetchone(
        f"SELECT * FROM lotteryinfo WHERE completed = True ORDER BY id desc"
    )


async def asyncgetlottowinnings(pname: str) -> Tuple[int, int]:
    """Return lottery winnings for player

    Args:
        pname (str): Description:

    Returns:
        Tuple[int, int]: Description:
    """
    pwins = await db.fetchall(
        f"SELECT payout FROM lotteryinfo WHERE winner = '{pname}'"
    )
    totpoints = 0
    twins = 0
    for weach in iter(pwins):
        totpoints = totpoints + int(weach[0])
        twins += 1
    return twins, totpoints


async def asynctotallotterydeposits(steamid: str) -> int:
    lottoinfo = await db.fetchone(
        f"SELECT points, givetake FROM lotterydeposits where steamid = '{steamid}'"
    )
    tps = 0
    if lottoinfo is not None:
        for each in lottoinfo:
            if each[1] == 1:
                tps += each[0]
            elif each[1] == 0:
                tps -= each[0]
    return tps


async def getlotteryendtime() -> datetime:
    lottoinfo = await db.fetchone(
        f"SELECT startdate, days from lotteryinfo WHERE completed = False"
    )
    return estshift(lottoinfo["startdate"] + timedelta(days=lottoinfo["days"]))


def keywithmaxval(d):
    v = list(d.values())
    k = list(d.keys())
    return k[v.index(max(v))]


async def asyncdeterminewinner(lottoinfo):
    log.debug("Lottery time has ended. Determining winner.")
    winners = {}
    lottoers = await db.fetchall("SELECT * FROM lotteryplayers")
    if len(lottoers) >= 3:
        try:
            seed(randint(99))
            for each in lottoers:
                roll = randint(100)
                lwins = await db.fetchone(f"SELECT lottowins FROM players WHERE steamid = '{each[0]}'")
                if int(lwins['lottowins']) == 0:
                    roll = roll + 20
                elif int(lwins['lottowins']) >= 5:
                    roll = roll - 20
                elif int(lwins['lottowins']) >= 3:
                    roll = roll - 10
                winners.update({each[0]: roll})
            winnersid = keywithmaxval(winners)
            lwinner = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{winnersid}'")
            await db.update(f"UPDATE lotteryinfo SET winner = '{lwinner[1]}', completed = True WHERE id = '{lottoinfo['id']}'")
            log.debug(winners)
            log.log("LOTTO", f'Lottery ended, winner is: {lwinner[1].upper()} with {lottoinfo["payout"]} points, win #{lwinner[18]+1}')
            del winners[winnersid]
            log.debug(f"queuing up lottery deposits for {winners}")
            for key, value in winners.items():
                kk = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{key}'")
                await db.update(
                    f"INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES ('{kk[0]}', '{kk[1]}', '{Now()}', 10, 0)"
                )
            bcast = f"""<RichColor Color="0,1,0,1"> </>\n<RichColor Color="0,1,0,1">                The current lottery has ended, and the winner is...</>\n<RichColor Color="1,1,0,1">                                  {lwinner[1].upper()}!</>\n                      {lwinner[1].capitalize()} has won {lottoinfo["payout"]} Reward Points!\n\n                         Next lottery begins in 1 hour."""
            await asyncwriteglobal("ALERT", "LOTTERY", bcast)
            await asyncwritediscord(
                f"{lwinner[1].title()}",
                Now(),
                name=f'{lottoinfo["payout"]}',
                server="LOTTOEND",
            )
            await db.update(
                f"INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES ('{lwinner[0]}', '{lwinner[1]}', '{Now()}', '{lottoinfo['payout']}', 1)"
            )
            if lwinner[19] is None:
                lwin = 0
            else:
                lwin = int(lwinner[19])
            nlw = lwin + int(lottoinfo["payout"])
            await db.update(
                f"UPDATE players SET lottowins = {int(lwinner[18]) + 1}, lotterywinnings = {nlw} WHERE steamid = '{lwinner[0]}'"
            )
        except:
            log.exception("Critical Error Lottery Winner determination!")
    else:
        log.log("LOTTO", f"Lottery has ended. Not enough players: ({len(lottoers)}/3)")
        await db.update(
            f"UPDATE lotteryinfo SET winner = 'None', completed = True WHERE id = {lottoinfo['id']}"
        )
        msg = f"Lottery has ended. Not enough players have participated.  Requires at least 3 players.\nNo points will be withdrawn from any participants.\nNext lottery begins in 1 hour."
        await asyncwritediscord(
            f"NONE", Now(), name=f"{len(lottoers)}", server="LOTTOEND"
        )
        await asyncwriteglobal("ALERT", "ALERT", msg)


async def asynclotteryloop(lottoinfo):
    if lottoinfo["announced"] is False:
        log.debug("clearing lotteryplayers table")
        await db.update("DELETE FROM lotteryplayers")
    await globalvar.set("inlottery", 1)
    if await globalvar.getbool("inlottery"):
        tdy = lottoinfo["startdate"] + timedelta(hours=lottoinfo["days"])
        # tdy = lottoinfo['startdate'] + timedelta(minutes=5)  # quick 5 min for testing
        if Now(fmt="dt") >= tdy:
            await asyncdeterminewinner(lottoinfo)
            await globalvar.set("inlottery", 0)


async def asyncstartlottery(lottoinfo):
    lend = elapsedTime(
        datetimeto(
            lottoinfo["startdate"] + timedelta(hours=lottoinfo["days"]), fmt="epoch"
        ),
        Now(),
    )
    if lottoinfo["announced"] is False:
        log.log(
            "LOTTO",
            f'New lottery has started. Buyin: {lottoinfo["buyin"]} Starting: {lottoinfo["payout"]} Length: {lottoinfo["days"]}',
        )
        bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="0,1,0,1">       A new points lottery has started! {lottoinfo['buyin']} points to enter in this lottery </>\n\n<RichColor Color="1,1,0,1">             Starting pot {lottoinfo['payout']} points and grows as players enter </>\n                   Lottery Ends in {lend}\n\n             Type !lotto for more info or !lotto enter to join"""

        await asyncwriteglobal("ALERT", "LOTTERY", bcast)
        await asyncwritediscord(
            f'{lottoinfo["payout"]}', Now(), name=f"{lend}", server="LOTTOSTART"
        )
        await db.update(
            f"UPDATE lotteryinfo SET announced = True WHERE id = {lottoinfo['id']}"
        )
    asyncio.create_task(asynclotteryloop(lottoinfo))


async def asyncgeneratelottery():
    log.trace("Generate new lottery check")
    lottodata = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
    if not lottodata:
        t, s, e = (
            datetime.now(),
            dt(21, 0),
            dt(21, 10),
        )  # Automatic Lottery 9:00pm GMT (5:00PM EST)
        lottotime = is_time_between(t, s, e)
        if lottotime:
            buyins = [25, 30, 20, 35]
            length = 23
            buyin = choice(buyins)
            litm = buyin * 25
            await db.update(
                f"""INSERT INTO lotteryinfo (payout,startdate,buyin,days,players,winner,announced,completed) VALUES ('{litm}','{Now(fmt="dt")}','{buyin}','{length}',0,'Incomplete',False,False)"""
            )


async def asynccheckforlottery():
    log.trace("Running lottery check")
    lottoinfo = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
    if lottoinfo:
        await asyncstartlottery(lottoinfo)


async def asynclotterywatcher():
    await asyncgeneratelottery()
    await asynccheckforlottery()
