# Power BI Service (Web — any OS)

Two ways to get Memgraph data into Power BI Service without needing Windows. Make sure you've completed the [Quick Start](README.md#quick-start) first.

---

## Approach 1: Push Dataset (recommended for Linux)

Push data directly from a Python script to a Power BI dataset via the REST API. No Gateway, no Windows machine needed. Works from any OS.

### Azure AD setup (one-time)

1. Go to [Azure Portal](https://portal.azure.com) > **App registrations** > **New registration**
2. Name it (e.g. `memgraph-powerbi-push`)
3. Under **API permissions**, add: **Power BI Service > Dataset.ReadWrite.All** (Application)
4. Grant admin consent
5. Under **Certificates & secrets**, create a new client secret
6. Note down:
   - **Tenant ID** (from Overview)
   - **Client ID** (from Overview)
   - **Client secret** (from Certificates & secrets)

### Steps

```bash
# 1. Set Azure credentials
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# 2. (Optional) Target a specific workspace
export POWERBI_WORKSPACE_ID="your-workspace-id"

# 3. Push Memgraph data to Power BI
python push_to_powerbi.py
```

The script will:
- Authenticate with Azure AD
- Create a Push Dataset called "Memgraph Data" (or reuse an existing one)
- Query Memgraph for person purchases and company employees
- Push the data to Power BI

4. Open [Power BI Service](https://app.powerbi.com)
5. Find the **Memgraph Data** dataset in your workspace
6. Click **Create report** and build your visualizations

### Scheduled refresh

Since this is a push model, schedule the script with cron:

```bash
# Push fresh data every hour
0 * * * * cd /path/to/powerbi_integration && .venv/bin/python push_to_powerbi.py
```

No Power BI Gateway needed.

---

## Approach 2: REST API + Dataflow

Use Power BI Dataflows to pull data from the FastAPI service. The API must be reachable from the internet.

### Steps

1. Start the REST API and make it publicly accessible (see [README.md](README.md#rest-api))
   - For testing: use a tunnel like ngrok (`ngrok http 8000`)
   - For production: deploy behind a reverse proxy with HTTPS
2. In Power BI Service, go to your workspace
3. Click **New > Dataflow**
4. Choose **Define new tables**
5. Select **Web** as the data source
6. Enter the API URL: `https://your-api-host:8000/person-purchases`
7. Power BI will preview the JSON data — click **Transform data** if needed
8. Save the dataflow
9. Repeat for other endpoints (`/nodes`, `/edges`, `/company-employees`)
10. Set a refresh schedule for the dataflow (e.g. daily)
11. Create a report from the dataflow tables

### Scheduled refresh

Dataflows refresh on their own schedule (configured in Power BI Service). No Gateway needed as long as the API is publicly accessible.

---

## Approach 3: ODBC via Gateway

If you have access to a Windows machine, you can set up a Power BI Gateway with an ODBC driver. See [DESKTOP.md](DESKTOP.md#approach-3-odbc) for driver setup, then configure the Gateway to use that DSN.

This is the least practical option for Linux-only environments.

---

## Comparison

| | Push Dataset | REST API + Dataflow | ODBC + Gateway |
|---|---|---|---|
| Works on Linux | Yes | Yes | No (Gateway is Windows) |
| Gateway needed | No | No (if API is public) | Yes |
| Cost | Free | Free | Paid (driver + Gateway) |
| Refresh model | Push (cron) | Pull (Dataflow schedule) | Pull (Gateway schedule) |
| Setup effort | Medium (Azure AD app) | Medium (public API) | High |
