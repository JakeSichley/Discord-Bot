"""
MIT License

Copyright (c) 2019-2023 Jake Sichley

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

from enum import IntEnum
from discord import AllowedMentions
from discord.app_commands import Choice
from typing import List


class AllowedMentionsProxy(IntEnum):
    """
    An Enum class provides a proxy mapping between an app_command.Choice and AllowedMentions.
    """

    NONE = 0
    EVERYONE = 1
    ROLES = 2
    USERS = 3
    ROLES_AND_USERS = 4
    EVERYONE_AND_ROLES = 5
    EVERYONE_AND_USERS = 6
    ALL = 7

    @staticmethod
    def app_command_choices() -> List[Choice]:
        """
        Returns a list of choices representing proxy options.

        Parameters:
            None.

        Returns:
            (List[Choice]).
        """

        return _ALLOWED_MENTION_PROXY_CHOICES

    @staticmethod
    def mapping(proxy_type: 'AllowedMentionsProxy') -> AllowedMentions:
        """
        Checks whether the feature is active for this guild.

        Parameters:
            proxy_type (AllowedMentionsProxy): The proxy to convert.

        Returns:
            (AllowedMentions).
        """

        return _ALLOWED_MENTION_PROXY_MAPPING.get(proxy_type, AllowedMentions.none())


_ALLOWED_MENTION_PROXY_CHOICES = [
    Choice(name='No Mentions', value=AllowedMentionsProxy.NONE.value),
    Choice(name='@Everyone and @Here', value=AllowedMentionsProxy.EVERYONE.value),
    Choice(name='@Roles', value=AllowedMentionsProxy.ROLES.value),
    Choice(name='@Users', value=AllowedMentionsProxy.USERS.value),
    Choice(name='@Roles, @Users', value=AllowedMentionsProxy.ROLES_AND_USERS.value),
    Choice(name='@Everyone and @Here, @Roles', value=AllowedMentionsProxy.EVERYONE_AND_ROLES.value),
    Choice(name='@Everyone and @Here, @Users', value=AllowedMentionsProxy.EVERYONE_AND_USERS.value),
    Choice(name='All Mentions', value=AllowedMentionsProxy.ALL.value),
]

_ALLOWED_MENTION_PROXY_MAPPING = {
    AllowedMentionsProxy.NONE: AllowedMentions.none(),
    AllowedMentionsProxy.EVERYONE: AllowedMentions(everyone=True, roles=False, users=False),
    AllowedMentionsProxy.ROLES: AllowedMentions(everyone=False, roles=True, users=False),
    AllowedMentionsProxy.USERS: AllowedMentions(everyone=False, roles=False, users=True),
    AllowedMentionsProxy.ROLES_AND_USERS: AllowedMentions(everyone=False, roles=True, users=True),
    AllowedMentionsProxy.EVERYONE_AND_ROLES: AllowedMentions(everyone=False, roles=False, users=False),
    AllowedMentionsProxy.EVERYONE_AND_USERS: AllowedMentions(everyone=False, roles=False, users=False),
    AllowedMentionsProxy.ALL: AllowedMentions.all()
}
