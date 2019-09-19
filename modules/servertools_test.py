import sys

import modules.servertools
import pytest

sys.path.append('/home/ark/pyark')


async def test_getservermem():
    assert type(await modules.servertools.getservermem()) is tuple
    assert await modules.servertools.getservermem() is not None
    assert len(await modules.servertools.getservermem()) == 3


"""
def test_isinstanceonline():
    with pytest.raises(TypeError):
        modules.instances.isinstanceonline(None)
        modules.instances.isinstanceonline(1)
        modules.instances.isinstanceonline(['island', 'ragnarok'])
    assert modules.instances.isinstanceonline('ragnarok') is True
    assert type(modules.instances.isinstanceonline('ragnarok')) is bool
"""