# OraFlux Studio

This project is a lightweight, ephemeral report viewer built with Angular and FastAPI. It allows users to connect to an Oracle 19c database, run ad-hoc `SELECT` queries, view paginated results, and build basic charts—all without persisting any data. When the browser tab is closed, the session is gone.

## Features

- **Ephemeral Sessions**: All state is in-memory on the backend, tied to a session ID. Nothing is stored on disk.
- **Oracle Connection**: Connect to any Oracle 19c database using Service Name or SID.
- **SQL Runner**: Execute `SELECT` statements in a simple editor.
- **Paginated Results**: View query results in a table with server-side pagination.
- **Report Builder**: Generate Bar, Line, Pie, and Histogram charts from query results.
- **Secure by Design**:
    - Enforces `SELECT`-only queries.
    - Uses read-only credentials (user-provided).
    - Implements query timeouts and row caps.
    - Ephemeral nature means no sensitive data is ever stored.

## Tech Stack

- **Frontend**: Angular 17, Angular Material, ngx-echarts
- **Backend**: FastAPI, Python 3.11, `python-oracledb` (Thin Mode)
- **Database**: Oracle 19c
- **Containerization**: Docker & Docker Compose

---

## Project Structure

```
/
├── backend/          # FastAPI application
│   ├── app/          # Main application code
│   ├── tests/        # Unit tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/         # Angular application
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml  # Orchestrates the services
├── vercel.json         # Vercel deployment configuration
└── README.md           # This file
```

---

## Prerequisites

- Docker and Docker Compose
- An accessible Oracle 19c database with a **read-only user**.

### Oracle Read-Only User Setup

You must provide credentials for an Oracle user with, at minimum, `CREATE SESSION` and `SELECT` privileges on the tables you wish to query.

Example grants:
```sql
-- Create a user (as SYS or a privileged user)
CREATE USER readonly_user IDENTIFIED BY YourSecurePassword;

-- Grant basic connect role
GRANT CREATE SESSION TO readonly_user;

-- Grant select on a specific table
GRANT SELECT ON a_schema.a_table TO readonly_user;

-- Or grant select on any table (use with caution)
-- GRANT SELECT ANY TABLE TO readonly_user;
```

---

## How to Run

### 1. Using Docker Compose (Recommended)

This is the simplest way to get both the frontend and backend running locally.

From the project root directory, run:

```bash
docker-compose up --build
```

- The frontend will be accessible at `http://localhost:4200`.
- The backend API will be running at `http://localhost:8000`.

To stop the services, press `Ctrl+C`. To remove the containers, run `docker-compose down`.

### 2. Running Manually

If you prefer to run the services directly without Docker.

#### Backend (FastAPI)

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Run the server:**
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
    The API will be available at `http://localhost:8000`.

#### Frontend (Angular)

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the development server:**
    ```bash
    ng serve
    ```
    The application will be available at `http://localhost:4200`.

---

## How to Use the Application

1.  **Open the App**: Navigate to `http://localhost:4200`. A new session will be started automatically.
2.  **Connect**: Enter the Host, Port, Service Name/SID, and your read-only user credentials. Click **Connect**.
3.  **Run a Query**: If the connection is successful, the SQL Runner will appear. Write a `SELECT` statement and click **Run Query**.
4.  **View Results**: Results are displayed in a paginated table.
5.  **Build a Chart**: If the query is successful, the Report Builder will appear below the results. Select a chart type, columns, and an aggregation function, then click **Generate Chart**.

---

## Running Tests

#### Backend Tests

To run the backend unit tests, navigate to the `backend` directory and run `pytest`:

```bash
cd backend
pytest
```

---

## Notes on Oracle `python-oracledb`

- **Thin Mode**: This project uses the `thin` mode of the `python-oracledb` driver, which does **not** require Oracle Instant Client.
- **SSL/TCPS Connection**: To connect to an Oracle database using SSL/TCPS, check the "Use SSL/TCPS" box. This requires the backend to have access to the Oracle wallet files (`tnsnames.ora`, `sqlnet.ora`, `cwallet.sso`, etc.). For a Docker-based setup, you would need to modify the `backend/Dockerfile` to copy the wallet files into the image and set the `TNS_ADMIN` environment variable.

---
## Deployment to Vercel

The frontend of this project is configured for easy deployment to [Vercel](https://vercel.com).

### Pre-requisite: Deploy Your Backend

Before deploying the frontend to Vercel, your FastAPI backend **must be running on a publicly accessible URL** (e.g., using a service like Render, Heroku, or a cloud provider). Vercel will need to forward API requests from the browser to this live backend URL.

### Vercel Deployment Steps

1.  **Sign up and Log in:** Go to [vercel.com](https://vercel.com) and create an account.
2.  **Create a New Project:** From your Vercel dashboard, click **Add New...** > **Project**.
3.  **Import Git Repository:**
    *   Connect your GitHub account.
    *   Select your `Ashish-Jeevanesan/OraFlux-Studio` repository and click **Import**.
4.  **Configure Project:**
    *   **IMPORTANT:** Vercel will auto-detect the Angular framework. **Do not change the "Root Directory" setting.** Leave it as the default (`/`). The `vercel.json` file in the repository is configured to handle the monorepo structure correctly.
    *   Expand the **Environment Variables** section.
    *   Add the following variable:
        *   **Name:** `BACKEND_API_URL`
        *   **Value:** `https://your-live-backend-url.com` (Replace this with the actual public URL of your deployed FastAPI backend).
5.  **Deploy:** Click the **Deploy** button.

Vercel will now build and deploy your application. The `vercel.json` configuration will automatically handle proxying any API requests from the frontend to your live backend service.
