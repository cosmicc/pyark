async def zpopmin(self, name, count):
    """
    Remove and return up to ``count`` members with the
    lowest scores from the sorted set ``name``
    """
    return await self.execute_command("ZPOPMIN", name, count)


async def zpopmax(self, name, count):
    """
    Remove and return up to ``count`` members with the
    highest scores from the sorted set ``name``
    """
    return await self.execute_command("ZPOPMAX", name, count)
