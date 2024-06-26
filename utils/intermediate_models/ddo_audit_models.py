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

from typing import Dict, Any, List, Optional


class DDOAuditServer:
    """
    A Server model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.name: Optional[str] = json.get('Name')
        self.last_update_time: Optional[str] = json.get('LastUpdateTime')
        self.group_count: Optional[int] = json.get('GroupCount')
        self.groups: List[DDOAuditGroup] = [DDOAuditGroup(x) for x in json.get('Groups', [])]

    def __repr__(self) -> str:
        return str(self.__dict__)


class DDOAuditGroup:
    """
    A Group model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: Optional[int] = json.get('Id')
        self.comment: Optional[str] = json.get('Comment')
        self.guess: Optional[bool] = json.get('Guess')
        self.difficulty: Optional[str] = json.get('Difficulty')
        self.minimum_level: Optional[int] = json.get('MinimumLevel')
        self.maximum_level: Optional[int] = json.get('MaximumLevel')
        self.adventure_active: Optional[int] = json.get('AdventureActive')
        self.quest: Optional[DDOAuditQuest] = DDOAuditQuest(json['Quest']) if json.get('Quest') else None
        self.leader: Optional[DDOAuditPlayer] = DDOAuditPlayer(json['Leader']) if json.get('Leader') else None
        self.members: List[DDOAuditPlayer] = [DDOAuditPlayer(x) for x in json.get('Members', [])]

    def __repr__(self) -> str:
        return str(self.__dict__)


class DDOAuditQuest:
    """
    A Quest model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: Optional[int] = json.get('AreaId')
        self.name: Optional[str] = json.get('Name')
        self.heroic_normal_cr: Optional[int] = json.get('HeroicNormalCR')
        self.epic_normal_cr: Optional[int] = json.get('EpicNormalCR')
        self.heroic_normal_xp: Optional[int] = json.get('HeroicNormalXp')
        self.heroic_hard_xp: Optional[int] = json.get('HeroicHardXp')
        self.heroic_elite_xp: Optional[int] = json.get('HeroicEliteXp')
        self.epic_normal_xp: Optional[int] = json.get('EpicNormalXp')
        self.epic_hard_xp: Optional[int] = json.get('EpicHardXp')
        self.epic_elite_xp: Optional[int] = json.get('EpicEliteXp')
        self.is_free_to_vip: Optional[bool] = json.get('IsFreeToVip')
        self.required_adventure_pack: Optional[str] = json.get('RequiredAdventurePack')
        self.adventure_area: Optional[str] = json.get('AdventureArea')
        self.quest_journal_group: Optional[str] = json.get('QuestJournalGroup')
        self.group_size: Optional[str] = json.get('GroupSize')
        self.patron: Optional[str] = json.get('Patron')
        self.average_time: Optional[float] = json.get('AverageTime')
        self.tip: Optional[str] = json.get('Tip')
        self.alt_id: Optional[int] = json.get('AltId')

    def __repr__(self) -> str:
        return str(self.__dict__)


class DDOAuditPlayer:
    """
    A Player model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.name: Optional[str] = json.get('Name')
        self.race: Optional[str] = json.get('Race')
        self.total_level: Optional[int] = json.get('TotalLevel')
        self.group_id: Optional[int] = json.get('GroupId')
        self.guild_name: Optional[str] = json.get('Guild')
        self.in_party: Optional[bool] = json.get('InParty')
        self.home_server: Optional[str] = json.get('HomeServer')
        self.classes: List[DDOAuditClass] = [DDOAuditClass(x) for x in json.get('Classes', [])]
        self.location: Optional[DDOAuditLocation] = DDOAuditLocation(json['Location']) if json.get('Location') else None

    def __repr__(self) -> str:
        return str(self.__dict__)


class DDOAuditClass:
    """
    A Class model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: Optional[int] = json.get('Id')
        self.name: Optional[str] = json.get('Name')
        self.level: Optional[int] = json.get('Level')

    def __repr__(self) -> str:
        return str(self.__dict__)


class DDOAuditLocation:
    """
    A Location model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: Optional[int] = json.get('Id')
        self.name: Optional[str] = json.get('Name')
        self.is_public: Optional[bool] = json.get('IsPublicSpace')
        self.region_name: Optional[str] = json.get('Region')

    def __repr__(self) -> str:
        return str(self.__dict__)


class DDOAdventureEmbed:
    """
    A model with required fields for the `LFM` command response.
    """

    def __init__(
            self,
            title: str,
            difficulty: str,
            current_members: int,
            max_members: int,
            minimum_level: int,
            maximum_level: int
    ) -> None:
        self.title: str = title
        self.difficulty: str = difficulty
        self.current_members: int = current_members
        self.max_members: int = max_members
        self.minimum_level: int = minimum_level
        self.maximum_level: int = maximum_level

    @property
    def members_description(self) -> str:
        """
        Builds the description of the current party occupancy.

        Parameters:
            None.

        Returns:
            (str).
        """

        return f'{self.current_members}/{self.max_members}'

    @property
    def level_description(self) -> str:
        """
        Builds the description of the group's allowable level range.

        Parameters:
            None.

        Returns:
            (str).
        """

        return f'{self.minimum_level}~{self.maximum_level}'

    def full_description(self, title_padding: int, difficulty_padding: int, members_padding: int) -> str:
        """
        Builds the full display string for the group.

        Parameters:
            title_padding (int): The total length the title description should occupy.
            difficulty_padding (int): The total length the difficulty description should occupy.
            members_padding (int): The total length the members description should occupy.

        Returns:
            (str).
        """

        return (f'{self.title:{title_padding}}  -  '
                f'{self.difficulty:{difficulty_padding}}  -  '
                f'{self.members_description:{members_padding}} Members  -  '
                f'Level {self.level_description}')

    @classmethod
    def from_group(cls, group: DDOAuditGroup) -> Optional['DDOAdventureEmbed']:
        """
        Synthesizes a DDOAdventureEmbed from an existing DDOAuditGroup, handling optionals.

        Parameters:
            group (DDOAuditGroup): The source group.

        Returns:
            (Optional[DDOAdventureEmbed]).
        """

        try:
            name = group.quest.name  # type: ignore[union-attr]

            if name is not None and ':' in name:
                name = name.split(': ')[1]

            quest_type = group.quest.group_size if group.quest else None
            if quest_type:
                max_group_size = 6 if quest_type == 'Party' else 12
            else:
                max_group_size = 12 if len(group.members) + 1 > 6 else 6

            group_size = len(group.members) + 1
            difficulty = group.difficulty
            minimum_level = group.minimum_level
            maximum_level = group.maximum_level

            _cls = cls(
                name, difficulty, group_size, max_group_size, minimum_level, maximum_level  # type: ignore[arg-type]
            )

            if any(True for value in _cls.__dict__.values() if value is None):
                return None
            else:
                return _cls
        except (AttributeError, ValueError):
            return None


class DDOPartyEmbed(DDOAdventureEmbed):
    """
    A model with required fields for the `LFM` command response.
    """

    def __init__(
            self,
            title: str,
            current_members: int,
            max_members: int,
            minimum_level: int,
            maximum_level: int
    ) -> None:
        super().__init__(title, "N/A", current_members, max_members, minimum_level, maximum_level)

    def full_description(self, title_padding: int, difficulty_padding: int, members_padding: int) -> str:
        """
        Builds the full display string for the group.

        Parameters:
            title_padding (int): The total length the title description should occupy.
            difficulty_padding (int): The total length the difficulty description should occupy.
            members_padding (int): The total length the members description should occupy.

        Returns:
            (str).
        """

        return (f'{self.title:{title_padding}}  -  '
                f'{self.members_description:{members_padding}} Members  -  '
                f'Level {self.level_description}')

    @classmethod
    def from_group(cls, group: DDOAuditGroup) -> Optional['DDOPartyEmbed']:
        """
        Synthesizes a DDOPartyEmbed from an existing DDOAuditGroup, handling optionals.

        Parameters:
            group (DDOAuditGroup): The source group.

        Returns:
            (Optional[DDOPartyEmbed]).
        """

        try:
            quest_type = group.quest.group_size if group.quest else None
            if quest_type:
                max_group_size = 6 if quest_type == 'Party' else 12
            else:
                max_group_size = 12 if len(group.members) + 1 > 6 else 6

            title = group.comment.strip()  # type: ignore[union-attr]
            group_size = len(group.members) + 1
            minimum_level = group.minimum_level
            maximum_level = group.maximum_level

            _cls = cls(
                title, group_size, max_group_size, minimum_level, maximum_level  # type: ignore[arg-type]
            )

            if any(True for value in _cls.__dict__.values() if value is None):
                return None
            else:
                return _cls
        except AttributeError:
            return None
