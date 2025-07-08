# Mining Wave Project

## Overview

This project, Mining Wave, provides an API and associated tools for interacting with and managing aspects related to Ergo blockchain mining. It includes features for monitoring miners, calculating bonuses, managing settings, and potentially interacting with the Ergo blockchain via external APIs or nodes.

## Goals

*   Provide a stable API for mining-related operations.
*   Implement logic for bonus calculations (e.g., loyalty bonuses).
*   Monitor miner activity and status.
*   Manage miner configurations and settings.
*   Interact with the Ergo blockchain for relevant data.

*(Add more specific goals as the project evolves)*

## Current Status

*   Initial project structure established.
*   API endpoint foundation (`api.py`, `routes/`).
*   Database interaction layer (`database.py`).
*   Configuration management (`config.py`, `sample.env`).
*   Middleware implementation (`middleware.py`).
*   Scripts for bonus verification, threshold checks, and settings updates exist.
*   Docker setup (`Dockerfile`, `docker-compose.yaml`).
*   Pool information APIs (`routes/pool/`) with public access (no API key required).
*   Pool configuration management via JSON file (`data/pool_config.json`).

*(Update this section after major milestones)*

## Architecture

*(Describe the high-level architecture here - e.g., FastAPI application, database connection, background tasks, external API interactions. Refer to `api.py`, `database.py`, `routes/`, etc.)*

### Components:
*   **API Layer (`api.py`, `routes/`):** Handles incoming HTTP requests.
*   **Database Layer (`database.py`):** Manages interactions with the database.
*   **Configuration (`config.py`):** Loads and provides access to settings.
*   **Middleware (`middleware.py`):** Handles cross-cutting concerns like authentication or logging.
*   **Pool API (`routes/pool/`):** Public API for pool information (no API key required).
*   **Utility Scripts (`scripts/`, `verify_*.py`, etc.):** Perform specific tasks like calculations or checks.
*   **Monitoring (`monitoring/`):** Contains monitoring-related code/configuration.

## Database Schema

*(Document the full database schema here, including tables, columns, types, relationships, and indexes. Refer to `database.py` and any potential model files.)*

**Example Table:**

| Table Name | Column Name | Data Type | Constraints     | Description                       |
| :--------- | :---------- | :-------- | :-------------- | :-------------------------------- |
| `miners`   | `id`        | `INTEGER` | `PRIMARY KEY`   | Unique identifier for the miner |
|            | `address`   | `TEXT`    | `UNIQUE, NOT NULL` | Miner's Ergo address            |
|            | `settings`  | `JSON`    |                 | Miner-specific settings         |
|            | `joined_at` | `TIMESTAMP`| `DEFAULT NOW()` | When the miner first connected  |
| ...        | ...         | ...       | ...             | ...                               |


## Migrations

*(List database migrations here. If using a tool like Alembic, reference the migration files.)*

*   **Initial Schema Setup:** (Describe initial tables created)
*   **Migration 001:** (Description of changes)

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd mining-wave
    ```
2.  **Set up Python environment:** (Recommended: use a virtual environment)
    ```bash
    python -m venv api-env
    source api-env/bin/activate  # On Windows use `api-env\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment:**
    *   Copy `sample.env` to `.env`.
    *   Fill in the required values in `.env` (database credentials, API keys, etc.).
5.  **Database Setup:**
    *(Add instructions for setting up the database, e.g., running migrations)*
6.  **(Optional) Docker Setup:**
    *   Ensure Docker and Docker Compose are installed.
    *   Run `docker-compose up -d`.

## How to Run

*   **Directly:**
    ```bash
    # Ensure environment variables are set or .env file is present
    # Ensure database is running and accessible
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
    ```
*   **With Docker:**
    ```bash
    docker-compose up
    ```
    The API should be accessible at `http://localhost:<configured_port>`.

## API Documentation

API endpoint documentation can be found in `api.md` or potentially via an auto-generated Swagger/OpenAPI interface at `/docs` (if configured in `api.py`).

### Pool Information APIs

The project includes a set of public APIs that provide pool information without requiring API key authentication. These APIs serve information from a configuration file (`data/pool_config.json`) and include:

*   **Pool Information** (`/pool/info`): Complete pool details including location, fees, and software type
*   **Pool API URL** (`/pool/api-url`): The pool's API endpoint for hashrate and miner data
*   **Pool Software** (`/pool/software`): Software type used by the pool
*   **Pool Fee** (`/pool/fee`): Pool fee percentage
*   **Pool Location** (`/pool/location`): Geographical location (currently HELSINKI)
*   **Additional endpoints**: Pool URL, coin information, status, and configuration reload

These endpoints are designed to be consumed by pool listing services and are rate-limited but publicly accessible.

## Future Plans / Roadmap

*(Outline planned features, improvements, or refactoring efforts)*

*   Feature X: ...
*   Improvement Y: ...
*   Refactor Z: ...

## Contribution Guidelines

*(Add guidelines for contributing, code style (e.g., PEP 8), testing requirements, and the pull request process)*

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request. 