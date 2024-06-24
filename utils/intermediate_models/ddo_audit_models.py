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

    def __repr__(self):
        return str(self.__dict__)

class DDOAuditGroup:
    """
    A Group model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: Optional[int] = json.get('Id')
        self.comment: Optional[str] = json.get('Comment')
        self.difficulty: Optional[str] = json.get('Difficulty')
        self.minimum_level: Optional[int] = json.get('MinimumLevel')
        self.maximum_level: Optional[int] = json.get('MaximumLevel')
        self.adventure_active: Optional[int] = json.get('AdventureActive')
        self.quest: Optional[DDOAuditQuest] = DDOAuditQuest(json['Quest']) if json.get('Quest') else None
        self.leader: Optional[DDOAuditPlayer] = DDOAuditPlayer(json['Leader']) if json.get('Leader') else None
        self.members: List[DDOAuditPlayer] = [DDOAuditPlayer(x) for x in json.get('Members', [])]

    def __repr__(self):
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

    def __repr__(self):
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

    def __repr__(self):
        return str(self.__dict__)

class DDOAuditClass:
    """
    A Class model for DDOAudit APIs.
    """

    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: Optional[int] = json.get('Id')
        self.name: Optional[str] = json.get('Name')
        self.level: Optional[int] = json.get('Level')

    def __repr__(self):
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

    def __repr__(self):
        return str(self.__dict__)