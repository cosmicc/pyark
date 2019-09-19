import sys

import modules.instances
import pytest

sys.path.append('/home/ark/pyark')


def test_isinstanceonline():
    with pytest.raises(TypeError):
        modules.instances.isinstanceup(None)
        modules.instances.isinstanceup(1)
        modules.instances.isinstanceup(['island', 'ragnarok'])
    assert modules.instances.isinstanceup('ragnarok') is True
    assert type(modules.instances.isinstanceup('ragnarok')) is bool


async def test_asyncgetinstancelist():
    assert type(modules.instances.asyncgetinstancelist()) is tuple
    assert modules.instances.asyncgetinstancelist() is not None
    assert len(modules.instances.asyncgetinstancelist()) == 5
