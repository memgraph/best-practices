
# Memgraph Role-Based Access Control (RBAC) Example

This example demonstrates how to configure a **read-only Memgraph user** using Memgraph's Enterprise features via the `gqlalchemy` Python client.


## 🧠 What This Example Does

The script performs the following actions:

1. **Connects to a running Memgraph instance** using `gqlalchemy`.
2. **Creates an `admin` user** — the first user created must be an admin with full privileges.
3. **Creates a `readonly` role** with limited privileges:
   - Only allows `MATCH` queries (read-only).
   - Grants read access on all node labels and edge types.
4. **Creates a `readonly_user`** and assigns them the `readonly` role.
5. **Tests the privileges**:
   - A `MATCH` query is allowed.
   - A `CREATE` query fails due to insufficient permissions.

---

## 🚀 How to Run Memgraph with Docker

To run Memgraph Enterprise using Docker:

```bash
docker run -it --rm -p 7687:7687 -e MEMGRAPH_ORGANIZATION_NAME=<YOUR_ORG_NAME> -e MEMGRAPH_ENTERPRISE_LICENSE=<YOUR_ENTERPRISE_LICENSE> memgraph/memgraph:3.1.1
```

This command launches:
- **Memgraph database** on port `7687`

## 🛠 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` should include:

```
gqlalchemy
```

---

## 🧪 How to Run the Script

Once Memgraph is running:

```bash
python3 creating_read_only_user.py
```

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph v3.1.1**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!

## 🏢 Enterprise or Community?

> 🛑 This example **requires Memgraph Enterprise**.

The **Community Edition** does not support role-based access control (RBAC), or privilege assignment.
