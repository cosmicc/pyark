import sys

import pytest
import modules.masterwatchdog

sys.path.append('/home/ark/pyark')


async def test_pinghost():
    assert type(await modules.masterwatchdog.pinghost('172.31.250.115')) is float
    assert await modules.masterwatchdog.pinghost('172.31.250.115') < 1


async def test_checkhosts():
    assert await modules.masterwatchdog.checkhosts() == 0
