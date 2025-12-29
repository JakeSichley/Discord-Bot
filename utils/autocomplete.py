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

from dataclasses import dataclass, field
from typing import Generic, TypeVar, Union, Any, Tuple, List, Iterable

from discord.app_commands import Choice
from rapidfuzz import fuzz

ChoiceT = TypeVar('ChoiceT', str, int, float, Union[str, int, float])


class AutocompleteFitness:
    """
    A class that represents the fitness measurement of a fuzzy string search.

    Notes:
        Levenshtein distance already incorporates string length delta as a metric, however, for our purposes
        we want to be able to sort resulting matches (with equal fitness) based on their distance,
        where matches of similar length receive higher priority.

    Attributes:
        fuzz_ratio (float): The fuzzy string search ratio. Bound to [0.0, 200.0].
        length_ratio (float): A ratio representing how close the current term is to search term. Bound to (0.0, 1.0].
    """

    __slots__ = ('fuzz_ratio', 'length_ratio')

    def __init__(self, fuzz_ratio: float, length_ratio: float) -> None:
        """
        The constructor for the AutocompleteFitness class.

        Parameters:
        fuzz_ratio (float): The fuzzy string search ratio.
        length_ratio (float): A ratio representing how close the current term is to search term.

        Returns:
            None.
        """

        self.fuzz_ratio = fuzz_ratio
        self.length_ratio = length_ratio

    @property
    def _key(self) -> Tuple[float, float]:
        """
        Helper function to generate a key for comparison.

        Parameters:
            None.

        Returns:
            (Tuple[float, float]): (fuzz_ratio, length_ratio).
        """

        return self.fuzz_ratio, self.length_ratio

    def __lt__(self, other: Any) -> bool:
        """
        Less than comparator.

        Parameters:
            other (Any): The other parameter to compare to.

        Returns:
            (bool).
        """

        if not isinstance(other, AutocompleteFitness):
            return NotImplemented

        return self._key < other._key

    def __le__(self, other: Any) -> bool:
        """
        Less than or equal to comparator.

        Parameters:
            other (Any): The other parameter to compare to.

        Returns:
            (bool).
        """

        if not isinstance(other, AutocompleteFitness):
            return NotImplemented

        return self._key <= other._key

    def __eq__(self, other: Any) -> bool:
        """
        Equal comparator.

        Parameters:
            other (Any): The other parameter to compare to.

        Returns:
            (bool).
        """

        if not isinstance(other, AutocompleteFitness):
            return False

        return self._key == other._key

    def __ne__(self, other: Any) -> bool:
        """
        Not equal comparator.

        Parameters:
            other (Any): The other parameter to compare to.

        Returns:
            (bool).
        """

        return not self.__eq__(other)

    def __gt__(self, other: Any) -> bool:
        """
        Greater than comparator.

        Parameters:
            other (Any): The other parameter to compare to.

        Returns:
            (bool).
        """

        if not isinstance(other, AutocompleteFitness):
            return NotImplemented

        return other < self

    def __ge__(self, other: Any) -> bool:
        """
        Greater than or equal to comparator.

        Parameters:
            other (Any): The other parameter to compare to.

        Returns:
            (bool).
        """

        if not isinstance(other, AutocompleteFitness):
            return NotImplemented

        return other <= self

    def __repr__(self) -> str:
        """
        Provides a string representation of this object.

        Parameters:
            None.

        Returns:
            (str).
        """

        return f"AutocompleteFitness({self.fuzz_ratio=}, {self.length_ratio=})"


@dataclass
class AutocompleteModel(Generic[ChoiceT]):
    """
    A Dataclass that encapsulates `app_commands.Choice` and a fuzzy search ratio.

    Attributes:
        name (str): The name of the choice.
        value (ChoiceT): The value of the choice.
        current (str): The current input.
        score_cutoff (float): The score cutoff to use. Default: 0.0.
        fitness (AutocompleteFitness): The similarity ratio between this model's name and the current input.
    """

    current: str
    name: str
    value: ChoiceT
    score_cutoff: float = 0.0
    fitness: AutocompleteFitness = field(init=False)

    def __post_init__(self) -> None:
        """
        Calculates the similarity ratio after initialization.

        Parameters:
            None.

        Returns:
            None.
        """

        self.fitness = self.__generate_autocomplete_fitness()

    def __generate_autocomplete_fitness(self) -> AutocompleteFitness:
        """
        Computes the AutocompleteFitness model for this choice.

        Parameters:
            None.

        Returns:
            (AutocompleteFitness).
        """

        casefolded_name = self.name.casefold()
        casefolded_current = self.current.casefold()

        length_difference = len(casefolded_current) - len(casefolded_name)
        length_ratio = 1 / abs(length_difference) if length_difference != 0 else 1

        if fuzz.token_set_ratio(casefolded_name, casefolded_current, score_cutoff=self.score_cutoff) >= 100.0:
            return AutocompleteFitness(200.0, length_ratio)

        if fuzz.partial_token_sort_ratio(casefolded_name, casefolded_current, score_cutoff=self.score_cutoff) >= 100.0:
            return AutocompleteFitness(100.0, length_ratio)

        return AutocompleteFitness(
            fuzz.QRatio(casefolded_name, casefolded_current, score_cutoff=self.score_cutoff),
            length_ratio
        )

    def to_choice(self) -> Choice[ChoiceT]:
        """
        Returns this model as an `app_commands.Choice` model.

        Parameters:
            None.

        Returns:
            (Choice): The `app_commands.Choice` model.
        """

        return Choice(name=self.name, value=self.value)

    def __lt__(self, other: 'AutocompleteModel[ChoiceT]') -> bool:
        """
        Returns whether this model is less-than (<) another model.

        Parameters:
            other (AutocompleteModel): The other model.

        Returns:
            (bool): self < other.
        """

        return self.fitness < other.fitness

    def __le__(self, other: 'AutocompleteModel[ChoiceT]') -> bool:
        """
        Returns whether this model is less-than-or-equal-to (<=) another model.

        Parameters:
            other (AutocompleteModel): The other model.

        Returns:
            (bool): self <= other.
        """

        return self.fitness <= other.fitness


def generate_autocomplete_choices(
        current: str,
        items: Iterable[Tuple[str, ChoiceT]],
        *,
        limit: int = 25,
        minimum_threshold: float = 0.0
) -> List[Choice[ChoiceT]]:
    """
    Generator that yields pairs of items in a sequence

    Parameters:
        current (str): The current autocomplete input.
        items (Iterable[Tuple[str, ChoiceT]]): An iterable of objects to convert to AutocompleteModels.
        limit (int): The maximum number of Choices to return.
        minimum_threshold (float): The minimum ratio for a Choice to be valid.
            200.0: Full token-set match.
            100.0: Full partial token-sort match.
            <=100.0: Q-ratio.

    Returns:
        (List[Choice[T]]): A list of converted and sorted Choices.
    """

    limit = max(1, min(25, limit))  # clamp to [1, 25]
    minimum_threshold = max(0.0, min(200.0, minimum_threshold))  # clamp to [0.0, 200.0]

    autocomplete_models = [AutocompleteModel(current, name, value, minimum_threshold) for name, value in items]
    sorted_models = sorted(autocomplete_models, reverse=True)

    return [x.to_choice() for x in sorted_models[:limit]]
