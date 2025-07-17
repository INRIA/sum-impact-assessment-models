from enum import Enum


class KPIValueType(str, Enum):
    percentage = "percentage"
    ratio = "ratio"
    custom_unit = "custom_unit"
    score = "score"
