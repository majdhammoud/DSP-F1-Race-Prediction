from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)
from sqlalchemy.sql import func

from database.database import Base


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)

    season = Column(Integer, nullable=False)

    round = Column(Integer, nullable=False)

    circuit_id = Column(String(100), nullable=False)

    driver_id = Column(String(100), nullable=False)

    constructor_name = Column(String(100), nullable=False)

    grid = Column(Integer, nullable=False)

    prediction = Column(Boolean, nullable=False)

    source = Column(String(20), nullable=False)

    probability = Column(Float)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class IngestionStat(Base):
    __tablename__ = "ingestion_stats"

    id = Column(Integer, primary_key=True, index=True)

    file_name = Column(String(255), nullable=False)

    ingested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    total_rows = Column(Integer)

    valid_rows = Column(Integer)

    invalid_rows = Column(Integer)

    criticality = Column(String(10))

    null_count = Column(Integer)

    type_error_count = Column(Integer)

    range_count = Column(Integer)

    consistency_count = Column(Integer)

    format_count = Column(Integer)

    duplicate_count = Column(Integer)

    schema_error = Column(Boolean, default=False)
