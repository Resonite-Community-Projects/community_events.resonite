FROM python:3.12

WORKDIR /app

RUN pip install poetry

COPY poetry.lock poetry.lock

COPY pyproject.toml pyproject.toml

COPY resonite_communities resonite_communities

RUN poetry install

COPY . .