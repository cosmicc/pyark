import sys
from asyncpg import Record

import modules.lottery
import pytest

sys.path.append('/home/ark/pyark')


async def test_asyncgetlastlotteryinfo():
    assert type(await modules.lottery.asyncgetlastlotteryinfo()) is Record
