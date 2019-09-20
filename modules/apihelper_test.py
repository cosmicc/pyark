import sys

import pytest
import modules.apihelper


sys.path.append('/home/ark/pyark')


@pytest.mark.last
def test_asyncsteamapifetcher(testsession):
    assert modules.apihelper.asyncsteamapifetcher(testsession) is True
