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

from discord.ext import commands
from typing import Optional
from datetime import datetime, timedelta
from utils.context import Context


class CooldownMapping:
    def __init__(self, max_cooldown: float = 604800) -> None:
        self.count: int = 0
        self.start_time: Optional[datetime] = None
        self.max_cooldown: float = max_cooldown

    def __repr__(self) -> str:
        return f'{self.count=}, {self.start_time=}, {self.max_cooldown=}'

    @property
    def base_duration(self) -> float:
        return min(2 ** (5 + self.count), self.max_cooldown)

    @property
    def remaining_cooldown(self) -> Optional[commands.Cooldown]:
        # don't impose cooldowns for the first two failures
        if self.count < 2:
            return None

        remaining_time = (self.start_time + timedelta(seconds=self.base_duration)) - datetime.now()

        if remaining_time.total_seconds() <= 0:
            return None

        return commands.Cooldown(1, remaining_time.total_seconds())

    def increment_failure_count(self) -> None:
        self.count += 1
        self.start_time = datetime.now()

    def reset(self) -> None:
        self.count = 0
        self.start_time = None


async def cooldown_predicate(ctx: Context) -> bool:
    default_mapping = CooldownMapping()
    cooldown_mapping = ctx.bot.dynamic_cooldowns.get(ctx.command.qualified_name, {}).get(ctx.author.id, default_mapping)

    if cooldown := cooldown_mapping.remaining_cooldown:
        raise commands.CommandOnCooldown(cooldown, cooldown.per, commands.BucketType.user)

    return True


