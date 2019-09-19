import sys

import asyncio
import modules.instances
import pytest

sys.path.append('/home/ark/pyark')


@pytest.yield_fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


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


@pytest.mark.asyncio
async def test_asyncisinstanceenabled(db):
    with pytest.raises(TypeError):
        await modules.instances.asyncisinstanceenabled(None)
        await modules.instances.asyncisinstanceenabled(1)
        await modules.instances.asyncisinstanceenabled(['island', 'ragnarok'])
    assert await modules.instances.asyncisinstanceenabled('ragnarok', db) is True
    assert type(await modules.instances.asyncisinstanceenabled('ragnarok', db)) is bool


@pytest.mark.asyncio
async def test_asyncgetlastwipe(db):
    with pytest.raises(TypeError):
        await modules.instances.asyncgetlastwipe(None)
        await modules.instances.asyncgetlastwipe(1)
        await modules.instances.asyncgetlastwipe(['island', 'ragnarok'])
    assert await modules.instances.asyncgetlastwipe('ragnarok', db) is not None
    assert type(await modules.instances.asyncgetlastwipe('ragnarok', db)) is int
