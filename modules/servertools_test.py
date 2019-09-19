import sys

import modules.servertools

sys.path.append('/home/ark/pyark')


async def test_getservermem():
    assert type(await modules.servertools.getservermem()) is tuple
    assert await modules.servertools.getservermem() is not None
    assert len(await modules.servertools.getservermem()) == 3
    results = await modules.servertools.getservermem()
    assert type(results[0]) is int and type(results[1]) is int and type(results[2]) is int


async def test_getcpuload():
    assert type(await modules.servertools.getcpuload()) is tuple
    assert await modules.servertools.getcpuload() is not None
    assert len(await modules.servertools.getcpuload()) == 5
    results = await modules.servertools.getcpuload()
    assert type(results[0]) is int and type(results[1]) is float and type(results[2]) is float and type(results[3]) is float and type(results[4]) is float


async def test_getopenfiles():
    assert type(await modules.servertools.getopenfiles()) is tuple
    assert await modules.servertools.getopenfiles() is not None
    assert len(await modules.servertools.getopenfiles()) == 2
    results = await modules.servertools.getopenfiles()
    assert type(results[0]) is int and type(results[1]) is int


async def test_getidlepercent():
    assert type(await modules.servertools.getidlepercent()) is float
    assert await modules.servertools.getidlepercent() is not None
    result = await modules.servertools.getidlepercent()
    assert len(str(result).split('.')[1]) == 1


"""
def test_isinstanceonline():
    with pytest.raises(TypeError):
        modules.instances.isinstanceonline(None)
        modules.instances.isinstanceonline(1)
        modules.instances.isinstanceonline(['island', 'ragnarok'])
    assert modules.instances.isinstanceonline('ragnarok') is True
    assert type(modules.instances.isinstanceonline('ragnarok')) is bool
"""
