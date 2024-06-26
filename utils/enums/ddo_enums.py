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

from enum import Enum
from typing import Set, List, Optional

from discord.app_commands import Choice


class PrettyPrintedEnum(Enum):
    """
    An Enum class that does not print the Class.Name when converted to a string.
    """

    def __str__(self) -> str:
        """
        Provides a string representation of this object.

        Parameters:
            None.

        Returns:
            (str).
        """

        # don't use with non-string types
        assert isinstance(self.value, str)

        return self.value


class Server(PrettyPrintedEnum):
    """
    An Enum class that represents DDO Servers.
    """

    Sarlona = 'Sarlona'
    Argonnessen = 'Argonnessen'
    Orien = 'Orien'

    # Argonnessen = 'Argonnessen'
    # Cannith = 'Cannith'
    # Ghallanda = 'Ghallanda'
    # Khyber = 'Khyber'
    # Orien = 'Orien'
    # Sarlona = 'Sarlona'
    # Thelanis = 'Thelanis'
    # Wayfinder = 'Wayfinder'
    # Hardcore = 'Hardcore'


class AdventureType(PrettyPrintedEnum):
    """
    An Enum class that represents DDO Adventure Types.
    """

    Quest = 'Quest'
    Raid = 'Raid'

    @property
    def ddo_audit_value(self) -> str:
        """
        Returns the value DDOAudit uses to represent this adventure type.

        Parameters:
            None.

        Returns:
            (str).
        """

        return _ADVENTURE_TYPE_MAPPING[self]


class Difficulty(PrettyPrintedEnum):
    """
    An Enum class that represents DDO Adventure Difficulties.
    """

    Casual = 'Casual'
    Normal = 'Normal'
    Hard = 'Hard'
    Elite = 'Elite'
    Reaper = 'Reaper'
    EliteReaper = 'Elite or Reaper'

    @property
    def difficulty_set(self) -> Set[str]:
        """
        Returns a set consisting of the represented difficulties. Primarily for `EliteReaper`

        Parameters:
            None.

        Returns:
            (Set[str]).
        """

        return _DIFFICULTY_SET_MAPPING[self]

    @staticmethod
    def choices() -> List[Choice[str]]:
        """
        Returns a list of difficulties as choices. Primarily for `EliteReaper` since discord.py has weird enum support.

        Parameters:
            None.

        Returns:
            (List[Choice[str]]).
        """

        return [Choice(name=x.value, value=x.value) for x in Difficulty]

    @classmethod
    def from_string(cls, value: str) -> Optional['Difficulty']:
        """
        Safely constructs this enum from a string value.

        Parameters:
            value (str): The raw value of the enum to construct.

        Returns:
            (Optional['Difficulty']).
        """

        try:
            return cls(value)
        except ValueError:
            return None


_ADVENTURE_TYPE_MAPPING = {
    AdventureType.Quest: 'Party',
    AdventureType.Raid: 'Raid'
}

_DIFFICULTY_SET_MAPPING = {
    Difficulty.Casual: { Difficulty.Casual.value },
    Difficulty.Normal: { Difficulty.Normal.value },
    Difficulty.Hard: { Difficulty.Hard.value },
    Difficulty.Elite: { Difficulty.Elite.value },
    Difficulty.Reaper: { Difficulty.Reaper.value },
    Difficulty.EliteReaper: { Difficulty.Elite.value, Difficulty.Reaper.value }
}
