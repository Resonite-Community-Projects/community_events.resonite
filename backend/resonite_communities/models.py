#from sqlalchemy.exc import IntegrityError
from signal import signal
from typing import Optional, Any

from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session


from sqlmodel import SQLModel, Field

engine = create_engine("sqlite:///my_database.db")
SessionLocale = sessionmaker(bind=engine)

class Signal:

    def __str__(self):
        """
        For some reason SQLModel doesn't render correctly the instance values correctly
        """
        fields = ", ".join(f"{key}={value!r}" for key, value in vars(self).items())
        return f"{self.__class__.__name__}({fields})"

    @classmethod
    def _validate_filter(cls, object: dict):
        """Validate that filter keys exist as attributes on the model."""
        for key in object.keys():
            key = key.split('__')[0]
            if not hasattr(cls, key):
                raise ValueError(f"Invalid filter field '{key}' for model '{cls.__name__}'")

    @classmethod
    def _apply_filter(cls, query, filters: dict[str, Any]):
        for field_operator, value in filters.items():
            field_operator = field_operator.split('__')
            field = field_operator[0]
            operator = 'eq'
            if len(field_operator) > 1:
                operator = field_operator[1]

            if operator == 'eq':
                query = query.where(getattr(cls, field) == value)
            if operator == 'neq':
                query = query.where(getattr(cls, field) != value)
            if operator == 'gtr':
                query = query.where(getattr(cls, field) > value)
            if operator == 'less':
                query = query.where(getattr(cls, field) < value)
            if operator == 'gtr_eq':
                query = query.where(getattr(cls, field) >= value)
            if operator == 'less_eq':
                query = query.where(getattr(cls, field) <= value)
            if operator == 'like':
                query = query.where(getattr(cls, field).like(value))
            #else:
            #    raise ValueError(f"Unsupported operator '{operator}")
        return query

    @classmethod
    def add(cls, **data: Any):
        """

        Examples:
            signal.add(**{'id': 44, 'name': 'aa'})
            signal.add(id=43, name="toto")
        """
        cls._validate_filter(data)
        with Session(engine) as session:
            signal_instance = cls(**data)
            session.add(signal_instance)
            session.commit()
            session.refresh(signal_instance)
        return signal_instance

    @classmethod
    def get(cls, **filters: Any):
        """
        Examples
            signal.get(name='toto')
        """
        cls._validate_filter(filters)
        with Session(engine) as session:
            instances = []
            query = select(cls)
            query = cls._apply_filter(query, filters)
            rows = session.exec(query).all()
            for row in rows:
                instances.append(row[0])
            if len(instances) == 1:
                return instances[0]
            return instances

    @classmethod
    def update(
        cls,
        _filter_field: str,
        _filter_value: Any,
        **fields_to_update: Any
    ):
        """

        Examples
            signal.update(_filter_field='id', _filter_value=44, name='aaa')

            signal.update(_filter_field='name', _filter_value="toto", name='aaa')
        """
        cls._validate_filter(fields_to_update)
        with Session(engine) as session:
            instances = []
            statement = select(cls).where(getattr(cls, _filter_field) == _filter_value)
            rows = session.exec(statement).all()
            for row in rows:
                instance = row[0]
                for key, value in fields_to_update.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                session.expunge(instance)
                instances.append(instance)
            if len(instances) == 1:
                return instances[0]
            return instances

    @classmethod
    def delete(cls, **filters: Optional[dict[str, Any]]):
        cls._validate_filter(filters)
        with Session(engine) as session:
            query = select(cls)
            query = cls._apply_filter(query, filters)
            rows = session.exec(query).all()
            deleted = len(rows)
            for row in rows:
                session.delete(row[0])
                session.commit()
            return deleted


class Event(Signal, SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    community_name: str | None = Field()

class Stream(Signal, SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str | None = Field()