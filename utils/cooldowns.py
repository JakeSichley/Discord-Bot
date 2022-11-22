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
from discord.ext.commands import Cooldown
from typing import TypeVar, Hashable, Optional, Dict
from datetime import datetime, timedelta

T = TypeVar('T', bound=Hashable)




@dataclass
class CooldownMapping:
    # key: T
    count: int = 0
    expires: Optional[datetime] = None



class ExponentialCooldown:
    def __init__(self, rate: float, per: float) -> None:
        self.rate = rate
        self.per = per
        self.mapping: Dict[T, CooldownMapping] = {}

