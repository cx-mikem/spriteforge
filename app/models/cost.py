"""Generation cost tracking model."""

from datetime import datetime
from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class GenerationCost(Base):
    __tablename__ = "generation_costs"

    id = Column(Integer, primary_key=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    cost_usd = Column(DECIMAL(10, 4), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    generation = relationship("Generation", back_populates="costs")

    __table_args__ = (
        Index("idx_generation_cost_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<GenerationCost ${self.cost_usd}>"
