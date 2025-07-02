# Memgraph 3.2.1 to 3.3 Upgrade Demo with Kubernetes

This example demonstrates how to deploy Memgraph 3.2.1 in a high availability mode with Kubernetes (using Minikube), connect the cluster, and then perform a seamless upgrade to Memgraph 3.3 using Helm.

## 🚀 Overview

The upgrade process follows these steps:

1. **Initial Deployment**: Deploy Memgraph 3.2.1 in HA mode with 3 coordinators and 2 data instances
2. **Cluster Connection**: Connect all coordinators and register data instances
3. **Data Injection**: Add sample data to verify replication works
4. **Helm Upgrade**: Perform the upgrade to Memgraph 3.3
5. **Verification**: Confirm data integrity and cluster connectivity after upgrade

## 🚀 Prerequisites

- Minikube installed and running
- kubectl configured
- Helm v3 installed
- Memgraph Enterprise license
- mgconsole installed

## 🚀 How to Run the Upgrade Demo

1. **Make the script executable**:
   ```bash
   chmod +x upgrade_memgraph_3.2.1_to_3.3.sh
   ```

2. **Update the values files** with your Memgraph Enterprise details:
   - Edit `values_3.2.1.yaml` and `values_3.3.yaml`
   - Replace `<your-enterprise-license>` with your Memgraph Enterprise license key
   - Replace `<your-organization-name>` with your organization name

3. **Run the upgrade demo**:
   ```bash
   ./upgrade_memgraph.sh
   ```

## 📋 What the Script Does

### Step 1: Deploy Memgraph 3.2.1
- Starts Minikube if not running
- Loads both Memgraph 3.2.1 and 3.3 images into Minikube
- Deploys Memgraph 3.2.1 using Helm with HA configuration
- Waits for all pods to be ready

### Step 2: Connect the Cluster
- Adds all 3 coordinators to the cluster
- Registers both data instances (main and replica)
- Sets instance_0 as the main instance
- Establishes replication between data instances

### Step 3: Inject Sample Data
- Creates sample Person nodes (Alice, Bob, Charlie)
- Creates relationships between them
- Verifies data replication between main and replica instances

### Step 4: Upgrade to Memgraph 3.3
- Performs Helm upgrade using the 3.3 values file
- Waits for all pods to restart and be ready
- Maintains data persistence through the upgrade

### Step 5: Verify Upgrade
- Checks Memgraph version after upgrade
- Verifies data integrity across all instances
- Tests cluster connectivity
- Confirms replication is working

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph MAGE v3.2.1** → **v3.3.0**
- **Kubernetes v1.28+**
- **Helm v3.12+**

## 🏢 Enterprise or Community?

> 🛑 This example **requires Memgraph Enterprise**.

### Useful Commands

```bash
# Check pod status
kubectl get pods

# View pod logs
kubectl logs <pod-name>

# Check services
kubectl get svc

# Access Minikube
minikube dashboard
```

## 📞 Support

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help! 