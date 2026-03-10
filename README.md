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
## Deployment

This project is designed to be deployed in two parts: a live backend service and a frontend hosted on a static hosting provider like Vercel.

### 1. Backend (FastAPI on Render)

The stateful FastAPI backend cannot be hosted on a serverless platform like Vercel. A platform designed for long-running services is required. We recommend **Render** for its simplicity and Docker support.

1.  **Sign up:** Go to [render.com](https://render.com) and create an account (you can sign up with GitHub).
2.  **New Web Service:** From the dashboard, click **New +** > **Web Service**.
3.  **Import Repository:** Connect your GitHub and select the `Ashish-Jeevanesan/OraFlux-Studio` repository.
4.  **Configure Service:**
    *   Give your service a unique **Name** (e.g., `oraflux-studio-backend`).
    *   Set the **Root Directory** to `./backend`.
    *   Set the **Environment** to `Docker`.
    *   Choose an **Instance Type** (the free tier is sufficient).
5.  **Create Service:** Click **Create Web Service**.

Render will build the `Dockerfile` from the `/backend` directory and deploy your API. Once complete, Render will provide a public URL for your service (e.g., `https://oraflux-studio-backend.onrender.com`). **Copy this URL.**

### 2. Frontend (Angular on Vercel)

1.  **Sign up and Log in:** Go to [vercel.com](https://vercel.com) and create an account.
2.  **New Project:** From your dashboard, click **Add New...** > **Project**.
3.  **Import Repository:** Connect your GitHub and select the `Ashish-Jeevanesan/OraFlux-Studio` repository.
4.  **Configure Project:**
    *   Vercel should auto-detect the Angular framework.
    *   **IMPORTANT:** Set the **Root Directory** to `frontend`. This tells Vercel to run the build from within your Angular project folder, where the now-corrected `vercel.json` lives.
    *   Expand the **Environment Variables** section.
    *   Add the following variable, pasting the URL you copied from Render:
        *   **Name:** `BACKEND_API_URL`
        *   **Value:** `http://localhost:8000`
    *   **Note:** By using `localhost` as the backend URL, your deployed Vercel frontend will only work when you are also running the backend server locally on your own machine. This is ideal for development and testing. To share the app with others, you would first need to deploy the backend to a public service like Render and use that public URL here instead.
5.  **Deploy:** Click the **Deploy** button.

Your OraFlux Studio is now live. The Vercel-hosted frontend will automatically find the `vercel.json` file and proxy all API requests to your live backend service.
