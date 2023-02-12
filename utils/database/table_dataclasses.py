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

import dataclasses
from typing import Tuple, Optional, Union, Type, get_args, get_origin


def expand_optional_types(field_type: Type) -> Union[Type, Tuple[Type, ...]]:
    """
    Expands Optional types to their Union form for `isinstance` checks. Ex: Optional[int] -> Union[int, None].

    Parameters:
        field_type (Type): The dataclass field's type.

    Returns:
        (Union[Type, Tuple[Type, ...]]): The resulting deconstructed types, if any.
    """

    if get_origin(field_type) is Union and type(None) in get_args(field_type):
        return get_args(field_type)
    else:
        return field_type


@dataclasses.dataclass
class DatabaseDataclass:
    """
    A `dataclass` used to enforce type-safety for type-specified database retrievals.

    This class no attributes of its own, and is meant to be subclassed.
    """

    def __post_init__(self) -> None:
        """
        A method called after the initialization of a `dataclass`.
        Using the built-in fields attribute, we can check the actual fields vs the intended fields, and raise
        an exception if they don't match.

        Parameters:
            None.

        Raises:
            ValueError.

        Returns:
            None.
        """

        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, expand_optional_types(field.type)):
                raise ValueError(f'Expected {field.name} to be {field.type}, got {type(value)}')


@dataclasses.dataclass
class PartialLoggingAction(DatabaseDataclass):
    """
    A DatabaseDataclass that stores the logging channel_id and bits for a guild.

    Attributes:
        channel_id (int): The logging channel id for the guild.
        bits (int): The logging bits for the guild.
    """

    channel_id: int
    bits: int


@dataclasses.dataclass
class VoiceRole(DatabaseDataclass):
    """
    A DatabaseDataclass that stores the guild_id, channel_id, and role_id of a VoiceRole.

    Attributes:
        guild_id (int): The guild id associated with the voice role.
        channel_id (int): The channel id associated with the voice role.
        role_id (int): The role id associated with the voice role.
    """

    guild_id: int
    channel_id: int
    role_id: int


@dataclasses.dataclass
class Prefix(DatabaseDataclass):
    """
    A DatabaseDataclass that stores a guild's prefix information.

    Attributes:
        guild_id (int): The id of the guild.
        prefix (str): A prefix of the guild.
    """

    guild_id: int
    prefix: str


@dataclasses.dataclass
class DefaultRole(DatabaseDataclass):
    """
    A DatabaseDataclass that stores a guild's prefix information.

    Attributes:
        guild_id (int): The id of the guild.
        role_id (int): A id of the guild's default role..
    """

    guild_id: int
    role_id: int


@dataclasses.dataclass
class ReactionRole(DatabaseDataclass):
    """
    A DatabaseDataclass that stores the reaction, role_id, and channel_id of a ReactionRole.

    Attributes:
        guild_id (int): The guild id associated with the reaction role.
        channel_id (int): The channel id associated with the reaction role.
        message_id (int): The message id associated with the reaction role.
        reaction (str): The reaction associated with the reaction role.
        role_id (int): The role id associated with the reaction role.
    """

    guild_id: int
    channel_id: int
    message_id: int
    reaction: str
    role_id: int

    @property
    def jump_url(self) -> str:
        """
        Generates a Discord 'jump url' for this reaction role's message.

        Parameters:
            None.

        Returns:
            (str).
        """

        return f'https://discordapp.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}'

    @property
    def primary_key(self) -> Tuple[int, str]:
        """
        Returns the primary key representation of this Reaction Role.

        Parameters:
            None.

        Returns:
            (Tuple[int, str]).
        """

        return self.message_id, self.reaction


@dataclasses.dataclass
class RunescapeAlert(DatabaseDataclass):
    """
    A DatabaseDataclass that stores a Runescape Item Alert.

    Attributes:
        owner_id (int): The alert's owner id.
        created (int): The time the alert was created.
        item_id (int): The item id for this alert.
        initial_low (Optional[int]): The item's instant-sell price at the time this alert was created.
        initial_high (Optional[int]): The item's instant-buy price at the time this alert was created.
        target_low (Optional[int]): The target instant-buy price that would trigger this alert.
        target_high (Optional[int]): The target instant-sell price that would trigger this alert.
        frequency (Optional[int]): The frequency this alert should trigger, in seconds.
        maximum_alerts (Optional[int]): The maximum number of alerts.
        last_alert (Optional[int]): The time of the last alert.
    """

    owner_id: int
    created: int
    item_id: int
    initial_low: Optional[int]
    initial_high: Optional[int]
    target_low: Optional[int]
    target_high: Optional[int]
    frequency: Optional[int]
    maximum_alerts: Optional[int]
    last_alert: Optional[int]
