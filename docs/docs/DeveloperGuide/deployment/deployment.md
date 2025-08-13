---
title: Deployment
next: DeveloperGuide/deployment/requirements.md
---

This section provides a guide for deploying your own instance of the Resonite Community Events system. While the specific deployment method can vary based on your infrastructure and preferences, this guide focuses on using Docker and Docker Compose stacks.

## Overview of the Deployment Process

The deployment process generally involves three main stages:

1.  **Server Installation**: Setting up the necessary software and infrastructure on your machine, primarily Docker and Docker Compose. This includes understanding our pre-configured Docker stacks.
2.  **Server Configuration**: Customizing the application's settings, including environment variables for sensitive data and database configurations. This is where you'll link your domain names and set up external services.
3.  **Running the Services**: Starting and managing the various components of the Resonite Community Events system, such as the database, signal manager, and client applications.

## Key Considerations

*   **Domain Names**: You will need one or more registered domain names (e.g., `example.com`, `private.example.com`) and access to their DNS settings to properly route traffic to your deployed services.
*   **Server Resources**: Ensure your server meets the [requirements](requirements.md) for running the application effectively.
