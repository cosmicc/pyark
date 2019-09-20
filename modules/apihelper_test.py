import sys

import pytest
import modules.apihelper


sys.path.append('/home/ark/pyark')


@pytest.mark.last
def test_asyncsteamapifetcher(session):
    assert modules.apihelper.asyncsteamapifetcher(session) is True
