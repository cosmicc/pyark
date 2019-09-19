import sys

import modules.instances
import pytest

sys.path.append('/home/ark/pyark')


def test_isinstanceonline():
    with pytest.raises(TypeError):
        modules.instances.isinstanceonline(None)
        modules.instances.isinstanceonline(1)
        modules.instances.isinstanceonline(['island', 'ragnarok'])
    assert modules.instances.isinstanceonline('ragnarok') is True
    assert type(modules.instances.isinstanceonline('ragnarok')) is bool


async def test_asyncgetinstancelist():
    assert type(await modules.instances.asyncgetinstancelist()) is tuple
    assert await modules.instances.asyncgetinstancelist() is not None
    assert len(await modules.instances.asyncgetinstancelist()) == 5


async def test_asyncisinstanceenabled():
    with pytest.raises(TypeError):
        await modules.instances.asyncisinstanceenabled(None)
        await modules.instances.asyncisinstanceenabled(1)
        await modules.instances.asyncisinstanceenabled(['island', 'ragnarok'])
    assert await modules.instances.asyncisinstanceenabled('ragnarok') is True
    assert type(await modules.instances.asyncisinstanceenabled('ragnarok')) is bool


async def test_asyncgetlastwipe():
    with pytest.raises(TypeError):
        await modules.instances.asyncgetlastwipe(None)
        await modules.instances.asyncgetlastwipe(1)
        await modules.instances.asyncgetlastwipe(['island', 'ragnarok'])
    assert await modules.instances.asyncgetlastwipe('ragnarok') is not None
    assert type(await modules.instances.asyncgetlastwipe('ragnarok')) is int
    assert type(await modules.instances.asyncgetlastwipe('ragnarok')) > 100000


async def test_asyncgetlastvote():
    with pytest.raises(TypeError):
        await modules.instances.asyncgetlastvote(None)
        await modules.instances.asyncgetlastvote(1)
        await modules.instances.asyncgetlastvote(['island', 'ragnarok'])
    assert await modules.instances.asyncgetlastvote('ragnarok') is not None
    assert type(await modules.instances.asyncgetlastvote('ragnarok')) is int
    assert type(await modules.instances.asyncgetlastwipe('ragnarok')) > 100000
