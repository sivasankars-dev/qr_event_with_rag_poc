from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base
from pgvector.sqlalchemy import Vector

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, index=True, nullable=False)

    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    summary = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

class SubmissionEmbedding(Base):
    __tablename__ = "submission_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    submission_id = Column(
        Integer,
        ForeignKey("submissions.id"),
        nullable=False,
        index=True
    )
    embedding = Column(Vector(1536), nullable=False)  
    summary = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )