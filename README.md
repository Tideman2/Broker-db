# Broker Backend

A RESTful backend for a brokerage platform built with **FastAPI, Python, MySQL, raw SQL, and JWT-based authentication**.

The application provides the backend infrastructure for user authentication, wallets, deposits, withdrawals, assets, trading transactions, and portfolio management.

## Features

* User registration and authentication
* JWT-based authentication
* Password hashing with bcrypt
* User profile and address management
* Wallet management
* Asset management
* Deposit management
* Withdrawal destination management
* Withdrawal management
* Buy and sell transactions
* Portfolio and holdings management
* Transaction history
* Pagination for large datasets
* Database migrations with version tracking
* MySQL database integration
* Production deployment on Render
* Production MySQL database hosted on Aiven

## Tech Stack

| Technology             | Purpose                     |
| ---------------------- | --------------------------- |
| Python                 | Backend language            |
| FastAPI                | REST API framework          |
| Pydantic               | Request/response validation |
| MySQL                  | Relational database         |
| mysql-connector-python | MySQL database driver       |
| Raw SQL                | Database queries            |
| PyJWT                  | JWT authentication          |
| bcrypt                 | Password hashing            |
| pytest                 | Testing                     |
| Render                 | Backend deployment          |
| Aiven                  | Production MySQL hosting    |

## Architecture

The project intentionally uses **raw SQL instead of an ORM**.

This keeps database interactions explicit and gives the application direct control over:

* SQL queries
* joins
* transactions
* indexes
* pagination
* database migrations
* schema evolution

A simplified project structure:

```text
broker-backend/
├── app/
│   ├── auth/
│   ├── db/
│   │   ├── Migration/
│   │   ├── connection.py
│   │   └── queries/
│   ├── routes/
│   ├── services/
│   ├── schemas/
│   └── ...
├── tests/
├── run.py
├── requirements.txt
└── README.md
```

The exact directory structure may evolve as the application grows.

## Authentication

Authentication is implemented using **JWTs**.

The authentication flow is broadly:

```text
Client
   │
   │ credentials
   ▼
FastAPI
   │
   ├── validate input
   ├── retrieve user
   ├── verify password
   └── issue JWT
           │
           ▼
        Client
           │
           │ authenticated request
           ▼
     Protected endpoint
           │
           ▼
    JWT verification
```

Passwords are never stored directly. Passwords are hashed with `bcrypt` before being persisted.

JWT verification is performed when accessing protected resources.

## Database

The application uses **MySQL** with direct SQL queries.

The schema contains domains such as:

* Users
* Addresses
* Assets
* Instruments
* Transactions
* Holdings
* Payment methods
* Deposits
* Withdrawal destinations
* Crypto destinations
* Bank destinations
* Withdrawals
* Wallet-related data

### Trading Instruments

The application supports different financial instrument categories:

```text
FOREX
CRYPTO
COMMODITY
INDEX
```

Transactions distinguish between:

```text
BUY
SELL
```

This allows the system to maintain transaction history independently from the user's current holdings.

## Database Migrations

Instead of relying on an ORM migration framework, the project contains a custom migration system.

Migrations are versioned and tracked using a `schema_migrations` table.

The general process is:

```text
Application starts
       │
       ▼
Read schema_migrations
       │
       ▼
Find unapplied migrations
       │
       ▼
Execute migrations in order
       │
       ▼
Record applied versions
```

This provides controlled schema evolution across development and production environments.

Migrations are intentionally ordered so that parent tables and required data exist before dependent tables are created.

## Wallet & Deposits

The wallet system supports financial operations such as deposits and withdrawals.

Deposits contain information including:

* User
* Payment method
* Asset
* Amount
* Status
* Creation time

Deposit statuses currently include:

```text
pending
confirmed
rejected
```

Payment methods include categories such as:

```text
CRYPTO
BANK
```

The withdrawal system similarly supports different destination types, including bank and crypto destinations.

## Transactions & Portfolio

Trading transactions are stored independently from holdings.

A transaction records the user's trading activity, while holdings represent the resulting position.

This separation makes it possible to derive portfolio information from the user's trading history while still maintaining an appropriate representation of their current positions.

The portfolio domain is designed to support concepts such as:

* Holdings
* Portfolio value
* Asset allocation
* Risk weighting
* Profit and loss
* Transaction history
* FIFO-based P/L calculations

## Pagination

Endpoints returning potentially large collections use pagination.

The backend uses `LIMIT` and `OFFSET` at the SQL layer rather than retrieving an entire dataset and paginating it in Python.

For example:

```sql
SELECT ...
FROM deposits
WHERE user_id = ?
ORDER BY created_at DESC
LIMIT ? OFFSET ?;
```

The pagination logic has also been abstracted so that it can be reused across different endpoints instead of duplicating pagination handling in every route.

## API Design

The API follows a resource-oriented REST structure.

Examples of resources include:

```text
/auth
/wallet
/assets
/deposits
/withdrawals
/transactions
/portfolio
```

Requests are validated using Pydantic schemas before reaching the relevant application logic.

The application separates responsibilities between routing, validation, database access, and business logic where appropriate.

## Environment Variables

Sensitive configuration is supplied through environment variables rather than committed to the repository.

Typical production configuration includes:

```env
PROD_DB_HOST=
PROD_DB_USER=
PROD_DB_PASSWORD=
PROD_DB_PORT=
PROD_DB_NAME=
CA_CERT=
```

Never commit credentials, private keys, certificates, or other secrets to source control.

## Local Development

### 1. Clone the repository

```bash
git clone <repository-url>
cd broker-backend
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**macOS/Linux**

```bash
source .venv/bin/activate
```

**Windows**

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create the appropriate environment configuration for your local database.

### 5. Run the application

```bash
python run.py
```

Or run FastAPI directly:

```bash
uvicorn app.main:app --reload
```

The API can then be accessed locally through the configured development port.

## Testing

Tests are written using `pytest`.

Run the test suite with:

```bash
pytest
```

## Deployment

The backend is designed to run as a web service on **Render**, with the production MySQL database hosted separately.

The production architecture is approximately:

```text
                    ┌─────────────────┐
                    │    Frontend     │
                    └────────┬────────┘
                             │
                             │ HTTPS
                             ▼
                    ┌─────────────────┐
                    │     Render      │
                    │    FastAPI      │
                    └────────┬────────┘
                             │
                             │ MySQL
                             ▼
                    ┌─────────────────┐
                    │      Aiven      │
                    │      MySQL      │
                    └─────────────────┘
```

Database credentials and certificates are supplied through the deployment environment rather than stored in the repository.

## API Documentation

FastAPI automatically provides interactive API documentation.

When running locally, the documentation is available through the application's configured Swagger/OpenAPI endpoints.

Typically:

```text
/docs
/redoc
```

## Engineering Goals

This project is primarily focused on building a backend that demonstrates practical understanding of:

* REST API design
* Authentication and authorization
* Relational database design
* SQL
* Database transactions
* Schema migrations
* Pagination
* Financial-domain data modelling
* Validation
* Error handling
* Production configuration
* Backend deployment

The project deliberately favors understanding and controlling the underlying systems over hiding database behavior behind an ORM.

## Status

🚧 **Active development**

The brokerage platform is being developed incrementally, with additional trading, portfolio, financial-operation, and infrastructure features planned as the system evolves.
