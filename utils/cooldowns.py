""" --- Docs ---
def cooldown_for_everyone_but_me(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
    if interaction.user.id == 80088516616269824:
        return None
    return app_commands.Cooldown(1, 10.0)

@tree.command()
@app_commands.checks.dynamic_cooldown(cooldown_for_everyone_but_me)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message('Hello')

@test.error
async def on_test_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(str(error), ephemeral=True)
"""
import discord

""" --- Discord Example --- 
class CooldownModified:
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
    
    async def __call__(self, message):
        if message.author is bot owner:
            return None
        else:
            return commands.Cooldown(self.rate, self.per)

#in a command
@commands.dynamic_cooldown(CooldownModified(2, 30), type = commands.BucketType.user)

#another command
@commands.dynamic_cooldown(CooldownModified(3, 180), type = commands.BucketType.channel)
"""

"""
Mapping -> User { num_failures, expiration_time }

Access bot from ctx or itx
self.bot.dynamic_cooldowns[qualified_command_name, ExponentialCooldown]

Don't need to initial actual rate in ExponentialCooldown() unless default cooldown is desired
"""

from dataclasses import dataclass
from discord.ext import commands
from typing import TypeVar, Hashable, Optional, Dict, Protocol
from datetime import datetime, timedelta
import discord


@dataclass
class CooldownMapping:
    count: int = 0
    expires: Optional[datetime] = None

    # this needs to have actual cooldown logic in it
    #  maybe have some fancy __get__ logic to expire cooldowns automatically

    """ --- Cases ---
        - User repeatedly fails
            - Need to know to increase cooldown after current cooldown ends
                - If now() > expires_at, no cooldown
            - When to reset cooldown for user who fails
                - User fails once, then succeeds, reset to 0? Decrement failure_count by amount?
    """



class ExponentialCommandCooldown:
    def __init__(self, rate: float, per: float) -> None:
        self.__rate = rate
        self.__per = per
        self.__mapping: Dict[int, CooldownMapping] = {}

    async def __call__(self, message: discord.Message) -> Optional[commands.Cooldown]:
        # call method doesn't ever directly modify mapping, only checks

        cooldown = self.__mapping.get(message.author.id, CooldownMapping())
