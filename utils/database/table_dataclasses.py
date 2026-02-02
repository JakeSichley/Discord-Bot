"""
MIT License

Copyright (c) 2019-Present Jake Sichley

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
from typing import Any, Type, Tuple, Union, TypeVar, Optional, get_args, get_origin

from utils.enums.allowed_mentions_proxy import AllowedMentionsProxy

T = TypeVar('T')


def expand_optional_types(field_type: Type[T]) -> Union[Type[T], Tuple[Type[T], ...]]:
    """
    Expands Optional types to their Union form for `isinstance` checks. Ex: Optional[int] -> Union[int, None].

    Parameters:
        field_type (Type): The dataclass field's type.

    Returns:
        (Union[Type, Tuple[Type, ...]]): The resulting deconstructed types, if any.
    """

    if get_origin(field_type) is Union and type(None) in get_args(field_type):
        return get_args(field_type)
    return field_type


@dataclasses.dataclass
class DatabaseDataclass:
    # TODO: Python >= 3.10 -> Convert to Slots
    """
    A `dataclass` used to enforce type-safety for type-specified database retrievals.

    This class has no attributes of its own, and is meant to be subclassed.
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
            if not isinstance(value, expand_optional_types(field.type)):  # type: ignore[arg-type]
                msg = f'Expected {field.name} to be {field.type}, got {type(value)}'
                raise ValueError(msg)

    def unpack(self) -> Tuple[Any, ...]:
        """
        Unpacks the dataclass as a tuple.

        Parameters:
            None.

        Returns:
            (Tuple[Any, ...]): The unpacked dataclass.
        """

        return dataclasses.astuple(self)


@dataclasses.dataclass
class Tag(DatabaseDataclass):
    """
    A dataclass that represents the internal structure of a Tag.

    Attributes:
        name (str): The name of the tag.
        content (str): The tag's content.
        guild_id (int): The guild this tag belongs to.
        owner_id (int): The user that created this tag.
        uses (int): The number of times this tag has been used.
        created (int): The time this tag was created.

    """

    name: str
    content: str
    guild_id: int
    owner_id: int
    uses: int
    created: int
    _allowed_mentions: int

    @property
    def allowed_mentions(self) -> AllowedMentionsProxy:
        """
        Maps the stored `allowed_mentions` int to an AllowedMentionsProxy.

        Parameters:
            None.

        Returns:
            (AllowedMentionsProxy).
        """

        return AllowedMentionsProxy(self._allowed_mentions)


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
        role_id (int): The id of the guild's default role.
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


@dataclasses.dataclass()
class RunescapeAlert(DatabaseDataclass):
    """
    A DatabaseDataclass that stores a Runescape Item Alert.

    Attributes:
        owner_id (int): The alert's owner id.
        created (int): The time the alert was created.
        item_id (int): The item id for this alert.
        current_alerts (int): The current number of times this alert has fired.
        maximum_alerts (Optional[int]): The maximum number of alerts.
        frequency (Optional[int]): The frequency this alert should trigger, in seconds.
        last_alert (Optional[int]): The time of the last alert.
        initial_low (Optional[int]): The item's instant-sell price at the time this alert was created.
        initial_high (Optional[int]): The item's instant-buy price at the time this alert was created.
        target_low (Optional[int]): The target instant-buy price that would trigger this alert.
        target_high (Optional[int]): The target instant-sell price that would trigger this alert.
    """

    owner_id: int
    created: int
    item_id: int
    current_alerts: int
    maximum_alerts: Optional[int]
    last_alert: Optional[int]
    frequency: Optional[int]
    initial_low: Optional[int]
    initial_high: Optional[int]
    target_low: Optional[int]
    target_high: Optional[int]

    def record_alert(self, last_alert_time: int) -> None:
        """
        Updates the last alert time and current alert count.

        Parameters:
            last_alert_time (int) The time the alert was last sent.

        Returns:
            None.
        """

        self.current_alerts += 1
        self.last_alert = last_alert_time


@dataclasses.dataclass
class GuildFeatures(DatabaseDataclass):
    """
    A DatabaseDataclass that stores a guild's feature information.

    Attributes:
        guild_id (int): The id of the guild.
        features (int): The features of the guild.
    """

    guild_id: int
    features: int


@dataclasses.dataclass
class Group(DatabaseDataclass):
    """
    A DatabaseDataclass that stores information about a Group.

    Attributes:
        guild_id (int): The id of the guild.
        owner_id (int): The id of the owner of this group.
        created (int): The time this group was created.
        name (str): The name of this group.
        max_members (Optional[int]): The maximum number of members this group may have, if any.
        current_members (int): The current number of members in this group.
        _ephemeral_updates (Bool): Whether updates to this group are ephemeral.
    """

    guild_id: int
    owner_id: int
    created: int
    name: str
    max_members: Optional[int]
    current_members: int = 0
    _ephemeral_updates: int = 0

    @property
    def key(self) -> str:
        """
        Returns a case-folded key for this group, suitable for comparisons.

        Parameters:
            None.

        Returns:
            (str).
        """

        return self.name.casefold()

    @property
    def is_full(self) -> bool:
        """
        Returns whether this group is at capacity.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return self.max_members is not None and self.current_members >= self.max_members

    @property
    def ephemeral_updates(self) -> bool:
        """
        Returns whether updates to this group should be ephemeral.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return self._ephemeral_updates == 1


@dataclasses.dataclass
class GroupMember(DatabaseDataclass):
    """
    A DatabaseDataclass that stores information about a Group Member.

    Attributes:
        guild_id (int): The id of the guild.
        member_id (int): The id of the member.
        joined (int): The time this member joined the group.
        group_name (str): The name of the group this member belongs to.
    """

    guild_id: int
    member_id: int
    joined: int
    group_name: str

    @property
    def group_key(self) -> str:
        """
        Returns a case-folded key for the group's name, suitable for comparisons.

        Parameters:
            None.

        Returns:
            (str).
        """

        return self.group_name.casefold()
