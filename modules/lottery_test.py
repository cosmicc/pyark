import sys
from asyncpg import Record

import modules.lottery
import pytest

sys.path.append('/home/ark/pyark')


def test_asyncgetlastlotteryinfo():
    assert type(modules.lottery.asyncgetlastlotteryinfo('admin')) is Record
