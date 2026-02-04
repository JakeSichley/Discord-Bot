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

from typing import Optional
from dataclasses import dataclass


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
        value (Optional[int]): The item's base value.
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
    value: Optional[int] = None
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
        emoji (str): The string representation of this herb's emoji.
        seed_id (int): The seed's internal id.
        clean_weed_id (int): The clean weed's internal id.
        grimy_weed_id (int): The grimy weed's internal id.
    """

    name: str
    emoji: str
    seed_id: int
    clean_weed_id: int
    grimy_weed_id: int


@dataclass
class RunescapeHerbComparison:
    """
    A dataclass that contains profit information related to farming runescape herbs.

    Attributes:
        name (str): The name of the herb.
        emoji (str): The string representation of this herb's emoji.
        cost (int): The cost of growing this herb.
        clean_profit (int): The profit from a harvesting this herb (clean).
        grimy_profit (int): The profit from a harvesting this herb (grimy).
    """

    name: str
    emoji: str
    cost: int
    clean_profit: int
    grimy_profit: int

    @property
    def min(self) -> int:
        """
        Returns the smallest profitable amount (between grimy and clean).

        Parameters:
            None.

        Returns:
            (float).
        """

        return min(self.clean_profit, self.grimy_profit)

    @property
    def max(self) -> int:
        """
        Returns the largest profitable amount (between grimy and clean).

        Parameters:
            None.

        Returns:
            (float).
        """

        return max(self.clean_profit, self.grimy_profit)

    def __lt__(self, other: 'RunescapeHerbComparison') -> bool:
        """
        Less-than comparison operator.

        Parameters:
            other (RunescapeHerbComparison): The other object to compare to.

        Returns:
            (bool).
        """

        return self.min < other.min

    @property
    def clean_profit_display(self) -> str:
        """
        Formats the clean_profit amount for display.

        Parameters:
            None.

        Returns:
            (str).
        """

        if self.clean_profit > self.grimy_profit and self.clean_profit > 0:
            return f'**{self.clean_profit:,}** coins'
        return f'{self.clean_profit:,} coins'

    @property
    def grimy_profit_display(self) -> str:
        """
        Formats the grimy_profit amount for display.

        Parameters:
            None.

        Returns:
            (str).
        """

        if self.grimy_profit > self.clean_profit and self.grimy_profit > 0:
            return f'**{self.grimy_profit:,}** coins'
        return f'{self.grimy_profit:,} coins'
