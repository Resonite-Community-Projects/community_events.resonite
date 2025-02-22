from sqlalchemy import Column, BigInteger, String, DateTime
from resonite_communities.auth.db import BaseModel

class Metrics(BaseModel):
    __tablename__ = "metrics"

    id = Column(BigInteger, primary_key=True, index=True)
    endpoint = Column(String, index=True)
    domain = Column(String, index=True)
    hashed_ip = Column(String, index=True)
    country = Column(String, index=True)
    timestamp = Column(DateTime)