"""
SQLAlchemy model for KPI results.
"""
from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from ..connection import Base


class KpiResult(Base):
    """
    Represents a KPI result measurement in the database.

    Attributes:
        id: Unique identifier for the KPI result (auto-increment)
        kpidefinition_id: Foreign key to kpidefinitions table
        living_lab_id: Foreign key to labs table
        transport_mode_id: Foreign key to transport_mode table (nullable for non-modal KPIs)
        value: The measured KPI value
        date: Date when the KPI was measured
    """
    __tablename__ = "kpiresults"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kpidefinition_id = Column(Integer, nullable=False)
    living_lab_id = Column(Integer, nullable=False)
    transport_mode_id = Column(Integer, nullable=True)
    value = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    def __repr__(self):
        return f"<KpiResult(id={self.id}, kpidefinition_id={self.kpidefinition_id}, living_lab_id={self.living_lab_id}, transport_mode_id={self.transport_mode_id}, value={self.value}, date={self.date})>"