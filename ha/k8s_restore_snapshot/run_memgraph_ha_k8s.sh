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

minikube image load memgraph/memgraph-mage:3.3.0_pr608_f85b660-memgraph-3.3.0_pr3031_da16b9da830d-relwithdebinfo

# Add Memgraph Helm repository if not already added
if ! helm repo list | grep -q "memgraph"; then
    echo "Adding Memgraph Helm repository..."
    helm repo add memgraph https://memgraph.github.io/helm-charts
    helm repo update
fi

# Step 1: Initial deployment with no replication
echo "Step 1: Deploying Memgraph with no replication..."
helm upgrade --install $RELEASE_NAME memgraph/memgraph-high-availability \
    --values values_no_replication.yaml \
    --wait

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l role=data --timeout=300s
kubectl wait --for=condition=ready pod -l role=coordinator --timeout=300s

# Get the service URL
NODE_PORT=$(kubectl get svc memgraph-data-0-external -o jsonpath='{.spec.ports[0].nodePort}')
MINIKUBE_IP=$(minikube ip)

echo "Memgraph is ready at: $MINIKUBE_IP:$NODE_PORT"

sleep 2

# Step 2: Inject million nodes
echo "Step 2: Injecting million nodes..."
echo "UNWIND range(1, 1000000) AS i CREATE (n:Node {id: i});" | mgconsole --host $MINIKUBE_IP --port $NODE_PORT

# Step 3: Create snapshot
echo "Step 3: Creating snapshot..."
echo "CREATE SNAPSHOT;" | mgconsole --host $MINIKUBE_IP --port $NODE_PORT

LATEST_SNAPSHOT=$(echo "SHOW SNAPSHOTS;" | mgconsole --host $MINIKUBE_IP --port $NODE_PORT --output-format=csv | tail -n +2 | awk -F',' '$2 != "\"0\"" { gsub(/"/, "", $1); print $2, $1 }' | sort -k1 -nr | head -n 1 | awk '{print $2}')
echo "Latest snapshot path: $LATEST_SNAPSHOT"

# Step 6: Redeploy with full HA configuration
echo "Step 6: Redeploying with full HA configuration..."
helm upgrade --install $RELEASE_NAME memgraph/memgraph-high-availability \
    --values values.yaml \
    --wait

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l role=data --timeout=300s
kubectl wait --for=condition=ready pod -l role=coordinator --timeout=300s

# Registering the cluster
echo "Registering the cluster..."
# Get the coordinator URL
MINIKUBE_IP=$(minikube ip)
echo "Minikube IP: $MINIKUBE_IP"

COORD1_NODE_PORT=$(kubectl get svc memgraph-coordinator-1-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
echo "Coordinator 1 node port: $COORD1_NODE_PORT"

# Get NodePorts for coordinators
COORD2_NODE_PORT=$(kubectl get svc memgraph-coordinator-2-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
echo "Coordinator 2 node port: $COORD2_NODE_PORT"

COORD3_NODE_PORT=$(kubectl get svc memgraph-coordinator-3-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
echo "Coordinator 3 node port: $COORD3_NODE_PORT"

# Get NodePorts for data nodes
DATA0_NODE_PORT=$(kubectl get svc memgraph-data-0-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
echo "Data 0 node port: $DATA0_NODE_PORT"

DATA1_NODE_PORT=$(kubectl get svc memgraph-data-1-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
echo "Data 1 node port: $DATA1_NODE_PORT"

sleep 2

# Add other coordinators
echo "ADD COORDINATOR 1 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD1_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-1.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-1.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "ADD COORDINATOR 2 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD2_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-2.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-2.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "ADD COORDINATOR 3 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD3_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-3.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-3.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
# Register data instances
echo "REGISTER INSTANCE instance_0 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$DATA0_NODE_PORT', 'management_server': 'memgraph-data-0.default.svc.cluster.local:10000', 'replication_server': 'memgraph-data-0.default.svc.cluster.local:20000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "REGISTER INSTANCE instance_1 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$DATA1_NODE_PORT', 'management_server': 'memgraph-data-1.default.svc.cluster.local:10000', 'replication_server': 'memgraph-data-1.default.svc.cluster.local:20000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
# Set 
echo "SET INSTANCE instance_0 TO MAIN;" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

# Step 4: Use the latest snapshot to recover on a different database
echo "CREATE DATABASE my_new_db;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT
echo "Step 4: Recovering the database on a new tenant..."
echo "USE DATABASE my_new_db; RECOVER SNAPSHOT '$LATEST_SNAPSHOT' FORCE;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

echo "The amount of nodes in the new database (main) is:"
echo "USE DATABASE my_new_db; MATCH (n) RETURN COUNT(n) as cnt;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

sleep 10

echo "The amount of nodes in the new database (replica) is:"
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
echo ""
