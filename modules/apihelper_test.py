import sys

import pytest
import modules.apihelper


sys.path.append('/home/ark/pyark')


@pytest.mark.last
async def test_getsteaminfo(testsession):
    assert await modules.apihelper.getsteaminfo('76561198408657294', 'admin', testsession) is True
