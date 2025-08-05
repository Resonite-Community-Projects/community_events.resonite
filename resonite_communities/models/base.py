from typing import ClassVar
from datetime import datetime, timezone

from typing import Optional, Any

from sqlalchemy import select, create_engine, inspect, desc, asc, ClauseElement
from sqlalchemy.dialects.postgresql import insert as dialects_insert
from sqlalchemy.orm import RelationshipProperty, joinedload
from sqlmodel import Session, SQLModel


from resonite_communities.utils.logger import get_logger

from resonite_communities.utils.config import ConfigManager

Config = ConfigManager().config()

engine = create_engine(Config.DATABASE_URL, echo=False)


class BaseModel(SQLModel):
    insert_only_fields: ClassVar[list[str]]= ['created_at']
    update_only_fields: ClassVar[list[str]] = ['updated_at']

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
                case 'in':
                    query = query.where(getattr(cls, field).in_(filter_value))
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

        if isinstance(custom_filter, ClauseElement):
            query = query.where(custom_filter)

        return query

    @classmethod
    def set_insert_fields(cls, fields_to_update: dict):
        """Set fields that should only be set during insert.
        """
        if 'created_at' not in fields_to_update:
            fields_to_update['created_at'] = datetime.now(timezone.utc)
        return fields_to_update

    @classmethod
    def set_update_fields(cls, fields_to_update: dict):
        """Set fields that should only be set during insert.
        """
        if 'updated_at' not in fields_to_update:
            fields_to_update['updated_at'] = datetime.now(timezone.utc)
        return fields_to_update

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

            rows = session.exec(query).unique().all()
            for row in rows:
                instances.append(row[0])
            return instances

    @classmethod
    def update(
        cls,
        filters: ClauseElement,
        **fields_to_update: Any
    ):
        """ Generic update method for updating database records with a custom filter.

        Parameters:
            custom_filter (ClauseElement): A SQLAlchemy filter expression to select the rows to update.
            fields_to_update (Any): Fields to update, provided as keyword arguments. Example: name="John".

        Examples:
            # Update with a custom filter
            MyModel.update(
                custom_filter=MyModel.age > 30,
                name="John Doe",
                status="active"
            )
        """
        # TODO: this would be interesting to let the user use the _apply_*_filter with like a Filter object instead

        fields_to_update['updated_at'] = datetime.utcnow()
        cls._validate_filter(fields_to_update)
        with Session(engine) as session:
            instances = []

            query = select(cls).where(filters)

            rows = session.exec(query).all()
            for row in rows:
                instance = row[0]
                for key, value in fields_to_update.items():
                    print(f"Setting {key} = {value} (type: {type(value)})")
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

        if not isinstance(_filter_field, list):
            _filter_field = [_filter_field]
        if not isinstance(_filter_value, list):
            _filter_value = [_filter_value]
        if len(_filter_field) != len(_filter_value):
            raise ValueError("There should be the same amount of fields and values")

        insert_data = {key: value for key, value in fields_to_update.items() if key not in cls.update_only_fields}
        insert_data = cls.set_insert_fields(insert_data)

        update_data = {key: value for key, value in fields_to_update.items() if key not in cls.insert_only_fields}
        update_data = cls.set_update_fields(update_data)

        stmt = dialects_insert(cls).values(**insert_data)

        stmt = stmt.on_conflict_do_update(
            index_elements=_filter_field,
            set_=update_data
        ).returning(cls)

        with Session(engine) as session:
            result = session.execute(stmt)
            session.commit()
            row = result.first()
            if row is None:
                return
            instance = row[0]
            session.refresh(instance)
            return instance



    @classmethod
    def delete(cls, **filters: Optional[dict[str, Any]]):
        cls._validate_filter(filters)
        with Session(engine) as session:
            query = select(cls)
            query = cls._apply_simple_filter(query, filters)
            query = cls._apply_operator_filter(query, filters)
            query = cls._apply_special_directive(query, filters)
            rows = session.exec(query).all()
            deleted = len(rows)
            for row in rows:
                session.delete(row[0])
                session.commit()
            return deleted