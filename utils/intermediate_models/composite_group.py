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

from typing import TYPE_CHECKING, Set, Optional
from dataclasses import field, dataclass

if TYPE_CHECKING:
    from utils.database.table_dataclasses import Group


@dataclass
class CompositeGroup:
    """
    A dataclass that joins Groups and the id's of Group Members.

    Attributes:
        group (Group): The raw group.
        members (Set[int]): The ids of the members of the group.
    """

    group: Group
    members: Set[int] = field(default_factory=set, init=False)

    def add_member(self, member_id: int) -> None:
        """
        Adds a member to this group.

        Parameters:
            member_id (int): The id of the member.

        Returns:
            None.
        """

        self.group.current_members += 1
        self.members.add(member_id)

    def remove_member(self, member_id: int) -> None:
        """
        Removes a member from this group.

        Parameters:
            member_id (int): The id of the member.

        Returns:
            None.
        """

        self.group.current_members -= 1
        self.members.discard(member_id)

    @property
    def key(self) -> str:
        """
        Quick access to the group's key.

        Parameters:
            None.

        Returns:
            (str).
        """

        return self.group.key

    @property
    def name(self) -> str:
        """
        Quick access to the group's name.

        Parameters:
            None.

        Returns:
            (str).
        """

        return self.group.name

    @property
    def owner_id(self) -> int:
        """
        Quick access to the group's owner id.

        Parameters:
            None.

        Returns:
            (int).
        """

        return self.group.owner_id

    @property
    def is_full(self) -> bool:
        """
        Quick access to the group's capacity status.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return self.group.is_full

    @property
    def ephemeral_updates(self) -> bool:
        """
        Quick access to the group's ephemeral_updates property.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return self.group.ephemeral_updates

    @property
    def current_members(self) -> int:
        """
        Quick access to the group's current_member property.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return self.group.current_members

    @property
    def max_members(self) -> Optional[int]:
        """
        Quick access to the group's max_members property.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return self.group.max_members
