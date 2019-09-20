import sys

import pytest
import modules.apihelper


sys.path.append('/home/ark/pyark')


@pytest.mark.last
async def test_asyncsteamapifetcher(testsession):
    assert await modules.apihelper.asyncsteamapifetcher(testsession) is True
