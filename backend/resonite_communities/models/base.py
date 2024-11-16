from datetime import datetime

from typing import Optional, Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, create_engine, inspect, desc, asc, BinaryExpression
from sqlalchemy.orm import sessionmaker, RelationshipProperty, joinedload
from sqlmodel import Session, SQLModel


from resonite_communities.utils.logger import get_logger

engine = create_engine("sqlite:///my_database.db")
SessionLocale = sessionmaker(bind=engine)

class BaseModel(SQLModel):

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
            if isinstance(key, str) and key.startswith("__"):
                continue
            key = key.split('__')[0]
            if not hasattr(cls, key):
                raise ValueError(f"Invalid filter field '{key}' for model '{cls.__name__}'")

    @classmethod
    def _apply_simple_filter(cls, query, filters: dict[str, Any]):
        for filter_name, filter_value in list(filters.items()):
            if "__" in filter_name or filter_name.startswith("__"):
                continue

            column = getattr(cls, filter_name, None)
            query = query.filter(column == filter_value)
            filters.pop(filter_name)
        return query

    @classmethod
    def _apply_operator_filter(cls, query, filters: dict[str, Any]):
        for filter_name, filter_value in list(filters.items()):
            if "__" not in filter_name or filter_name.startswith("__"):
                continue

            field, operator = filter_name.split('__', 1)

            match operator:
                case 'eq':
                    query = query.where(getattr(cls, field) == filter_value)
                case 'neq':
                    query = query.where(getattr(cls, field) != filter_value)
                case 'gtr':
                    query = query.where(getattr(cls, field) > filter_value)
                case 'less':
                    query = query.where(getattr(cls, field) < filter_value)
                case 'gtr_eq':
                    query = query.where(getattr(cls, field) >= filter_value)
                case 'less_eq':
                    query = query.where(getattr(cls, field) <= filter_value)
                case 'like':
                    query = query.where(getattr(cls, field).like(filter_value))
            #else:
            #    raise ValueError(f"Unsupported operator '{operator}")
            filters.pop(filter_name)
        return query

    @classmethod
    def _apply_special_directive(cls, query, filters: dict[str, Any]):
        order_by = filters.pop('__order_by', None)
        custom_filter = filters.pop('__custom_filter', None)

        if order_by:
            for field in order_by:
                is_descending = field.startswith('-')
                field_name = field[1:] if is_descending else field
                if hasattr(cls, field_name):
                    query = query.order_by(
                        desc(getattr(cls, field_name)) if is_descending else asc(getattr(cls, field_name)))

        if isinstance(custom_filter, BinaryExpression):
            query = query.where(custom_filter)

        return query


    @classmethod
    def add(cls, **data: Any):
        """

        Examples:
            signal.add(**{'id': 44, 'name': 'aa'})
            signal.add(id=43, name="toto")
        """
        data['created_at'] = datetime.utcnow()
        cls._validate_filter(data)
        with Session(engine) as session:
            signal_instance = cls(**data)
            session.add(signal_instance)
            session.commit()
            session.refresh(signal_instance)
        return signal_instance

    @classmethod
    def find(cls, **filters: Any):
        """
        Generic find method for querying the database with flexible filters.
        Filters can be:
        - Simple match: {"field_name": value}
        - Operator-based: {"field_name__operator": value}
        - Special directives: {"__order_by": ["field1", "-field2"]}
        - Custom filter: {"__custom_filter": <sqlalchemy.sql.expression>}

        Examples
            signal.find(name='Fluffy event')  # Simple match
            signal.find(start_time__gtr_eq=datetime.now())  # Operator based match
            signal.find(__order_by = "start_time")  # Special directive match
            signal.find(__custom_filter = case(...)  # Custom filter match
        """
        cls._validate_filter(filters)
        with Session(engine) as session:
            instances = []
            query = select(cls)

            # Include other model
            for rel_name, rel_attr in inspect(cls).relationships.items():
                if isinstance(rel_attr, RelationshipProperty):
                    query = query.options(joinedload(rel_attr))

            query = cls._apply_simple_filter(query, filters)
            query = cls._apply_operator_filter(query, filters)
            query = cls._apply_special_directive(query, filters)

            rows = session.exec(query).all()
            for row in rows:
                instances.append(row[0])
            return instances

    @classmethod
    def update(
        cls,
        _filter_field: str | list[str],
        _filter_value: Any | list[Any],
        **fields_to_update: Any
    ):
        """

        Examples
            signal.update(_filter_field='id', _filter_value=44, name='aaa')

            signal.update(_filter_field='name', _filter_value="toto", name='aaa')
        """
        # TODO: this would be interesting to let the user use the _apply_filter with like a Filter object instead
        fields_to_update['updated_at'] = datetime.utcnow()
        cls._validate_filter(fields_to_update)
        with Session(engine) as session:
            instances = []
            if not isinstance(_filter_field, list):
                _filter_field = [_filter_field]
            if not isinstance(_filter_value, list):
                _filter_value = [_filter_value]
            if len(_filter_value) != len(_filter_value):
                raise ValueError('Their should be the same amount of fields and values.')
            filters = []
            for pos in range(0, len(_filter_field)):
                filters.append(getattr(cls, _filter_field[pos]) == _filter_value[pos])
            statement = select(cls).where(*filters)
            rows = session.exec(statement).all()
            for row in rows:
                instance = row[0]
                for key, value in fields_to_update.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                session.expunge(instance)
                instances.append(instance)
            return instances

    @classmethod
    def upsert(
        cls,
        _filter_field: str | list[str],
        _filter_value: Any | list[Any],
        **fields_to_update: Any
    ):
        cls._validate_filter(fields_to_update)
        # TODO: This will need to use the on_conflict_do_update sql method
        # But this is not available yet in SQLModel
        # See https://github.com/fastapi/sqlmodel/issues/59
        try:
            cls.add(**fields_to_update)
        except IntegrityError as exc:
            if not isinstance(_filter_field, list):
                _filter_field = [_filter_field]
            constraints_ = [f"{cls.__name__.lower()}.{field}" for field in _filter_field]
            if f'UNIQUE constraint failed: {", ".join(constraints_)}' not in str(exc):
                get_logger(cls.__name__).error(exc)
            else:
                cls.update(_filter_field, _filter_value, **fields_to_update)



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