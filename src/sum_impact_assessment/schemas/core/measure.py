from pydantic import BaseModel

class Measure(BaseModel):
    """
    Measure schema:
    - id: unique identifier
    - name: name of the push or pull measure
    """
    id: str
    name: str