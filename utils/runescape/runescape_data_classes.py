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

from dataclasses import dataclass
from typing import Optional


@dataclass
class AlertEmbedFragment:
    """
    A dataclass that represents the components necessary for alert notifications.

    Attributes:
        owner_id (int): The alert's owner id.
        item_id (int): The item's internal id.
        name (str): The item's name.
        current_price (int): The item's current price.
        target_price (int): The alert's target item price.
    """

    owner_id: int
    item_id: int
    name: str
    current_price: int
    target_price: int


@dataclass
class ItemMarketData:
    """
    A dataclass that represents the market data associated with an Old School Runescape Item.

    Attributes:
        high (Optional[int]): The item's most recent "instant-buy" price.
        highTime (Optional[int]): The time the item's most recent "instant-buy" transaction occurred.
        low (Optional[int]): The item's most recent "instant-sell" price.
        lowTime (Optional[int]): The time the item's most recent "instant-sell" transaction occurred.
    """

    high: Optional[int] = None
    highTime: Optional[int] = None
    low: Optional[int] = None
    lowTime: Optional[int] = None


@dataclass
class RunescapeItem:
    """
    A dataclass that represents the raw components of an Old School Runescape Item.

    Attributes:
        id (int): The item's internal id.
        name (str): The item's name.
        examine (str): The item's description.
        icon (str): The item's icon name on the Old School Wiki.
        members (bool): Whether the item is members-only.
        value (int): The item's base value.
        limit (Optional[int]): The item's Grand Exchange limit, if any.
        lowalch (Optional[int]): The item's low alchemy value, if any.
        highalch (Optional[int]): The item's high alchemy value, if any.
        high (Optional[int]): The item's most recent "instant-buy" price.
        highTime (Optional[int]): The time the item's most recent "instant-buy" transaction occurred.
        low (Optional[int]): The item's most recent "instant-sell" price.
        lowTime (Optional[int]): The time the item's most recent "instant-sell" transaction occurred.
    """

    id: int
    name: str
    examine: str
    icon: str
    members: bool
    value: int
    limit: Optional[int] = None
    lowalch: Optional[int] = None
    highalch: Optional[int] = None
    high: Optional[int] = None
    highTime: Optional[int] = None
    low: Optional[int] = None
    lowTime: Optional[int] = None

    def update_with_mapping_fragment(self, fragment: 'RunescapeItem') -> None:
        """
        A method that updates the item's internal data.

        Parameters:
            fragment (RunescapeItem): The RunescapeItem fragment to update the item with.

        Returns:
            None.
        """

        self.id = fragment.id
        self.name = fragment.name
        self.examine = fragment.examine
        self.icon = fragment.icon
        self.members = fragment.members
        self.value = fragment.value
        self.limit = fragment.limit
        self.lowalch = fragment.lowalch
        self.highalch = fragment.highalch

    def update_with_market_fragment(self, fragment: ItemMarketData) -> None:
        """
        A method that updates the item's market data.

        Parameters:
            fragment (ItemMarketData): The ItemMarketData fragment to update the item with.

        Returns:
            None.
        """

        self.high = fragment.high
        self.highTime = fragment.highTime
        self.low = fragment.low
        self.lowTime = fragment.lowTime


@dataclass
class RunescapeHerb:
    """
    A dataclass that contains information about a runescape herb (seed, grimy weed, clean weed).

    Attributes:
        name (str): The name of the herb.
        seed_id (int): The seed's internal id.
        clean_weed_id (int): The clean weed's internal id.
        grimy_weed_id (int): The grimy weed's internal id.
    """

    name: str
    seed_id: int
    clean_weed_id: int
    grimy_weed_id: int

ALL_HERBS = [
    RunescapeHerb('Toadflax', 5296, 2998, 3049),
    RunescapeHerb('Kwuarm', 5299, 263, 213),
    RunescapeHerb('Avantoe', 5298, 261, 211),
    RunescapeHerb('Ranarr', 5295, 265, 207),
    RunescapeHerb('Cadantine', 5301, 3000, 215),
    RunescapeHerb('Snapdragon', 5300, 269, 3051),
    RunescapeHerb('Torstol', 5304, 267, 219),
    RunescapeHerb('Dwarf weed', 5303, 2481, 217),
    RunescapeHerb('Lantadyme', 5302, 255, 2485),
    RunescapeHerb('Irit', 5297, 253, 209),
    RunescapeHerb('Harralander', 5294, 251, 205),
]