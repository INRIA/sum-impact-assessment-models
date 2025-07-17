from ..core import Measure


class MeasureImpactCoefficient(Measure):
    """
    Extends Measure to include impact coefficient and mean squared error (msq).
    - coefficient (float): Estimated impact coefficient.
    - msq (float): Mean Squared Error of the estimation.
    """
    coefficient: float
    msq: float
    #add any more relevant information...
