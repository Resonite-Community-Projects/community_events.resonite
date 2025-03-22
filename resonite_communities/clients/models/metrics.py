from sqlalchemy import Column, BigInteger, String, DateTime, Enum as SQLAlchemyEnum
from resonite_communities.auth.db import BaseModel
from enum import Enum

class ClientType(str, Enum):
    BOT = 'BOT'
    NEOS = 'NEOS'
    RESONITE = 'RESONITE'
    TOOL = 'TOOL'
    BROWSER_MOBILE = 'BROWSER_MOBILE'
    BROWSER_DESKTOP = 'BROWSER_DESKTOP'

    @classmethod
    def valid_values(cls):
        return '\n- '.join([''] + [f"{cls.__name__}.{member.name}: '{cls.__name__}.{member.value}'" for member in cls])

class Metrics(BaseModel):
    __tablename__ = "metrics"

    id = Column(BigInteger, primary_key=True, index=True)
    endpoint = Column(String, index=True)
    domain = Column(String, index=True)
    hashed_ip = Column(String, index=True)
    country = Column(String, index=True)
    version = Column(String, index=True)
    client = Column(SQLAlchemyEnum(ClientType), index=True)
    user_agent = Column(String, index=True)
    timestamp = Column(DateTime)