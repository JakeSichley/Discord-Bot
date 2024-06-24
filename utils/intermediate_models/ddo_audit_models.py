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
    def __init__(self, json: Dict[str, Any]) -> None:
        self.name: str = json['Name']
        self.last_update_time: str = json['LastUpdateTime']
        self.group_count: int = json['GroupCount']
        self.groups = ...

class DDOAuditGroup:
    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: int = json['Id']
        self.comment: str = json['Comment']
        self.difficulty: str = json['Difficulty']
        self.quest: ...
        self.minimum_level: int = json['MinimumLevel']
        self.maximum_level: int = json['MaximumLevel']
        self.adventure_active: int = json['AdventureActive']
        self.leader: ...
        self.members: ...

class DDOAuditQuest:
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

class DDOAuditPlayer:
    def __init__(self, json: Dict[str, Any]) -> None:
        self.name: str = json['Name']
        self.race: str = json['Race']
        self.total_level: int = json['TotalLevel']
        self.classes: List[DDOAuditClass] = [DDOAuditClass(x) for x in json['Classes']]
        self.location: DDOAuditLocation = DDOAuditLocation(json['Location'])
        self.group_id: int = json['GroupId']
        self.guild_name: str = json['Guild']
        self.in_party: bool = json['InParty']
        self.home_server: str = json['HomeServer']

class DDOAuditClass:
    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: int = json['Id']
        self.name: str = json['Name']
        self.level: int = json['Level']

class DDOAuditLocation:
    def __init__(self, json: Dict[str, Any]) -> None:
        self.id: int = json['Id']
        self.name: str = json['Name']
        self.is_public: bool = json['IsPublicSpace']
        self.region_name: str = json['Region']
