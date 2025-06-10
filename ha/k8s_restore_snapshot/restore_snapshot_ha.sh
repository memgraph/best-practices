#!/bin/bash

# Exit on error
set -e

# Configuration
RELEASE_NAME="memgraph-ha"

# Check if Minikube is running
if ! minikube status | grep -q "Running"; then
    echo "Starting Minikube..."
    minikube start --cpus 4 --memory 8192
fi

# Load the Memgraph image
minikube image load memgraph/memgraph-mage:3.3.0_pr608_f85b660-memgraph-3.3.0_pr3031_da16b9da830d-relwithdebinfo

# Add Memgraph Helm repository if not already added
if ! helm repo list | grep -q "memgraph"; then
    echo "Adding Memgraph Helm repository..."
    helm repo add memgraph https://memgraph.github.io/helm-charts
    helm repo update
fi

# Step 1: Deploy Memgraph with replication enabled
echo "Step 1: Deploying Memgraph with replication enabled..."
helm upgrade --install $RELEASE_NAME memgraph/memgraph-high-availability \
    --values values.yaml \
    --wait

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l role=data --timeout=300s
kubectl wait --for=condition=ready pod -l role=coordinator --timeout=300s

# Get the service URL
MINIKUBE_IP=$(minikube ip)
COORD1_NODE_PORT=$(kubectl get svc memgraph-coordinator-1-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
DATA0_NODE_PORT=$(kubectl get svc memgraph-data-0-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
DATA1_NODE_PORT=$(kubectl get svc memgraph-data-1-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')

echo "Memgraph is ready at: $MINIKUBE_IP:$COORD1_NODE_PORT"

# Step 2: Copy custom snapshot to the data pod
echo "Step 2: Copying custom snapshot to the data pod..."
kubectl cp custom_snapshot memgraph-data-0-0:/var/lib/memgraph/snapshots/

# Waiting for mgconsole to become accessible
sleep 10

# Step 3: Register the cluster
echo "Step 3: Registering the cluster..."

# Get NodePorts for coordinators
COORD2_NODE_PORT=$(kubectl get svc memgraph-coordinator-2-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
COORD3_NODE_PORT=$(kubectl get svc memgraph-coordinator-3-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')

# Add coordinators
echo "ADD COORDINATOR 1 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD1_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-1.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-1.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "ADD COORDINATOR 2 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD2_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-2.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-2.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "ADD COORDINATOR 3 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD3_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-3.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-3.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

# Register data instances
echo "REGISTER INSTANCE instance_0 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$DATA0_NODE_PORT', 'management_server': 'memgraph-data-0.default.svc.cluster.local:10000', 'replication_server': 'memgraph-data-0.default.svc.cluster.local:20000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "REGISTER INSTANCE instance_1 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$DATA1_NODE_PORT', 'management_server': 'memgraph-data-1.default.svc.cluster.local:10000', 'replication_server': 'memgraph-data-1.default.svc.cluster.local:20000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

# Set main instance
echo "SET INSTANCE instance_0 TO MAIN;" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

# Step 4: Create new database and recover from snapshot
echo "Step 4: Creating new database and recovering from snapshot..."
echo "CREATE DATABASE my_new_db;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT
echo "USE DATABASE my_new_db; RECOVER SNAPSHOT '/var/lib/memgraph/snapshots/custom_snapshot' FORCE;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

# Wait for replication to complete
echo "Waiting for replication to complete..."
sleep 10

# Verify data on both instances
echo "Verifying data on main instance:"
echo "USE DATABASE my_new_db; MATCH (n) RETURN COUNT(n) as cnt;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

echo "Verifying data on replica instance:"
echo "USE DATABASE my_new_db; MATCH (n) RETURN COUNT(n) as cnt;" | mgconsole --host $MINIKUBE_IP --port $DATA1_NODE_PORT

echo "Memgraph HA cluster is ready!"
echo "You can connect to Memgraph coordinator at: $MINIKUBE_IP:$COORD1_NODE_PORT"
echo "You can connect to Memgraph data instance at: $MINIKUBE_IP:$DATA0_NODE_PORT"
echo ""
echo "To check the status of your pods, run:"
echo "kubectl get pods"
echo ""
echo "To view logs of a specific pod, run:"
echo "kubectl logs <pod-name>" 