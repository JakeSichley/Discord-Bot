"""
MIT License

Copyright (c) 2019-2022 Jake Sichley

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from asyncio import sleep, wait_for, TimeoutError
from functools import reduce
from json.decoder import JSONDecodeError
from random import seed, shuffle, randrange
from re import search, findall
from time import time
from typing import List, no_type_check, Optional, Dict, Any

from aiohttp import ClientError
from bs4 import BeautifulSoup
from discord import Embed
from discord.ext import commands, tasks

from dreambot import DreamBot
from utils.context import Context
from utils.logging_formatter import bot_logger
from utils.network_utils import network_request, NetworkReturnType, ExponentialBackoff
from dataclasses import dataclass


@dataclass
class RunescapeItem:
    """
    A dataclass that represents the raw components of an Old School Runescape Item.

    Attributes:
        id (int): The item's internal id.
        name (str): The item's name.
        examine (str): The item's description.
        icon (str): The item's icon name on the Old School Wiki.
        members (bool): Whether the item is members-only.
        value (int): The item's base value.
        limit (Optional[int]): The item's Grand Exchange limit, if any.
        lowalch (Optional[int]): The item's low alchemy value, if any.
        highalch (Optional[int]): The item's high alchemy value, if any.
    """

    id: int
    name: str
    examine: str
    icon: str
    members: bool
    value: int
    limit: Optional[int] = None
    lowalch: Optional[int] = None
    highalch: Optional[int] = None


class Runescape(commands.Cog):
    """
    A Cogs class that contains Old School Runescape commands.

    Constants:
        MAPPING_QUERY_INTERVAL (int): How frequently API data from DDOAudit should be queried.

    Attributes:
        bot (DreamBot): The Discord bot.
        item_data.
        query_ddo_audit (ext.tasks): Stores the task that queries DDOAudit every {QUERY_INTERVAL} seconds.
        backoff (ExponentialBackoff): Exponential Backoff calculator for network requests.
    """

    MAPPING_QUERY_INTERVAL = 60 * 60  # 1 hour

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Runescape class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.item_data: Dict[str, RunescapeItem] = {}
        self.backoff = ExponentialBackoff(3600 * 4)
        self.query_mapping_data.start()

    @commands.is_owner()
    @commands.command('rs')
    async def rs_item(self, ctx, *, name: str):
        await ctx.send(self.item_data[name] if name in self.item_data else 'Item Not Found')

    @tasks.loop(seconds=MAPPING_QUERY_INTERVAL)
    async def query_mapping_data(self) -> None:
        """
        A discord.ext.tasks loop that queries the OSRS Wiki API for item information.
        Executes every {MAPPING_QUERY_INTERVAL} seconds.

        Parameters:
            None.

        Returns:
            None.
        """

        try:
            mapping_response = await network_request(
                self.bot.session,
                'https://prices.runescape.wiki/api/v1/osrs/mapping',
                return_type=NetworkReturnType.JSON, ssl=False
            )

            self.item_data = {item['name']: RunescapeItem(**item) for item in mapping_response if 'name' in item}

        except ClientError:
            pass

        except TypeError as e:
            bot_logger.warning(f'OSRS RunescapeItem Init Error: {e}')

        except (JSONDecodeError, UnicodeError) as e:
            bot_logger.warning(f'OSRS Mapping Query Error: {type(e)} - {e}')

        except Exception as e:
            bot_logger.error(f'OSRS Mapping Query Unhandled Exception: {type(e)} - {e}')
            await self.bot.report_exception(e)

    async def cog_unload(self) -> None:
        """
        A method detailing custom extension unloading procedures.
        Clears internal caches and immediately and forcefully exits any discord.ext.tasks.

        Parameters:
            None.

        Returns:
            None.
        """

        self.query_mapping_data.cancel()
        self.item_data = dict()

        bot_logger.info('Completed Unload for Cog: Runescape')


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Runescape(bot))
    bot_logger.info('Completed Setup for Cog: Runescape')