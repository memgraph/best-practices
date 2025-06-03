# Memgraph HA deployment with Kubernetes and Snapshot Restoration

This example demonstrates how to deploy Memgraph in a high availability mode with Kubernetes (using Minikube) and includes snapshot restoration capabilities. The deployment process follows these steps:

1. Initial deployment with no replication
2. Data injection (1 million nodes)
3. Snapshot creation
4. Recovering the snapshot on a different database
5. Redeployment with full HA configuration

## 🚀 Prerequisites

- Minikube installed and running
- kubectl configured
- Helm v3 installed
- Memgraph Enterprise license
- mgconsole installed

## 🚀 How to Run Memgraph with Kubernetes

1. Run `chmod +x run_memgraph_ha_k8s.sh` to make the script executable
2. Update both `values.yaml` and `values_no_replication.yaml` files with your Memgraph Enterprise details:
   - Replace `<your-license>` with your Memgraph Enterprise license key
   - Replace `<your-organization-name>` with your organization name
3. To deploy Memgraph HA cluster, run:

```bash
./run_memgraph_ha_k8s.sh
```

The script will:
1. Deploy Memgraph using `values_no_replication.yaml`
2. Inject 1 million nodes into the database
3. Create a snapshot of the data
4. Redeploy using `values.yaml` with full HA configuration

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph MAGE v3.2.0**
- **Kubernetes v1.28+**
- **Helm v3.12+**

## 🏢 Enterprise or Community?

> 🛑 This example **requires Memgraph Enterprise**.

## 📝 Notes

- The deployment uses Minikube for local development and testing
- The script sets up a 3-node Memgraph cluster in HA mode
- Snapshot restoration is configured and can be triggered using the provided commands
- All necessary Kubernetes resources (StatefulSets, Services, ConfigMaps) are created automatically
- The `values.yaml` file contains all configuration options for the deployment, including:
  - Resource limits and requests
  - Storage configurations
  - Port settings
  - Affinity rules
  - Probe configurations
  - And more
- The `values_no_replication.yaml` file contains a simplified configuration for the initial data loading phase

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help! 