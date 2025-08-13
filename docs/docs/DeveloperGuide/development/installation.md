---
title: Installation
prev: DeveloperGuide/development/setup.md
next: DeveloperGuide/development/usage.md
---

This section only cover **our** stacks, including the developement instance as well as the production instance.

There is also a stack who represent the **official** Resonite instance. The goal is during development and testing we can have a system that is more near to the production system. If you want to know more about the official Resonite instance, please look on the official GitHub fork.

## Docker stacks

We use Docker stacks file to deploy and locally develop the system. Using docker stacks is not mandatory but is not the recommanded way. See the dedicated section that explain how to use the system without the Docker stacks.

### Stacks Architecture

First we define 3 different environments:

- **local**
- **development**
- **production**

!!! note

    While the production environment is sliglty different, the local one and development one are the same aside that the development one is running on a VPS.

Each environment, aside the production one have a set of stacks:

- **community** stack which define what **we** are running on our server.
- **official** stack which define what **they** are running (the official Resonite team).
- **router** stack which will handle the routing from different domains to the different endpoints on the different stacks.

!!! note

    We use the "official" stack as a "simulation". This is mainly use for the collector and transmitter of events between the two instances. This is not mandatory so unless you need to work on that you can ignore the "official" stack.

In any case you need to first run the "router" stack then one or both of the other stack.

The start order of the stacks are as follow: "router" first and then "community" or "official". The "router" is required to start any other stack but not two other stack can be run independently from each other.

To run the router stack

```
docker compose -f stacks/local/router.docker-compose.yml -p local_community_eventsresonite --profile "*" up

```

To run the community stack

```
docker compose -f stacks/local/community.docker-compose.yml -p local_community_eventsresonite --profile "*" up
```

To run the official stack

```
docker compose -f stacks/local/official.docker-compose.yml -p local_community_eventsresonite --profile "*" up
```

## Project Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Resonite-Community-Projects/community_events.resonite.git
    cd community_events.resonite
    ```



## Environment variables

We use environment variables to store information related to the infrastructure. We use `.env` files for local instance and GitHub environment variable in the CI/CD setup.

### GitHub Actions Setup

Be careful to set the environment as a secret when needed.

### Locally use the environments variables

For local development, we split the environment variables into different environment and stacks. All are splitted in `.envrc.d` folder.

!!! construction

    Explain a bit more here

## Local development without Docker stack

While we usually recommend to stick to using Docker you can only start the database and run everything else manually. You could also simply choose to not even use Docker even for the database.

- poetry install
- ??

2.  **Install Python dependencies**:
    ```bash
    poetry install
    ```
4.  **Activate the virtual environment**:
    ```bash
    poetry shell
    ```
5.  **Apply database migrations**:
    ```bash
    alembic upgrade head
    ```

### Running the Application

Once all dependencies are installed and configured, you can run the individual components of the application:

*   **Signals Manager**:
    ```bash
    poetry run signals_manager
    ```
*   **HTTP API**:
    ```bash
    poetry run api_client
    ```
*   **Web Client**:
    ```bash
    poetry run web_client
    ```
*   **Documentation Server**:
    ```bash
    poetry run docs serve
    ```

Remember to set the appropriate environment variables (as described in the "Environment variables" section) before running these commands.
