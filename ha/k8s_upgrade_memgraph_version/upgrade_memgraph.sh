#!/bin/bash

# Exit on error
set -e

# Configuration
RELEASE_NAME="memgraph-ha"

echo "=== Memgraph 3.2.1 to 3.3 Upgrade Demo ==="
echo "This script will:"
echo "1. Deploy Memgraph 3.2.1 in HA mode"
echo "2. Connect the cluster"
echo "3. Inject sample data"
echo "4. Upgrade to Memgraph 3.3"
echo ""

# Check if Minikube is running
if ! minikube status | grep -q "Running"; then
    echo "Starting Minikube..."
    minikube start --cpus 4 --memory 8192
fi

# Load both images into Minikube
echo "Loading Memgraph images into Minikube..."
minikube image load memgraph/memgraph-mage:3.2.1
minikube image load memgraph/memgraph-mage:3.3

# Add Memgraph Helm repository if not already added
if ! helm repo list | grep -q "memgraph"; then
    echo "Adding Memgraph Helm repository..."
    helm repo add memgraph https://memgraph.github.io/helm-charts
    helm repo update
fi

# Step 1: Deploy Memgraph 3.2.1
echo ""
echo "=== Step 1: Deploying Memgraph 3.2.1 ==="
helm upgrade --install $RELEASE_NAME memgraph/memgraph-high-availability \
    --values values_3.2.1.yaml \
    --wait

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l role=data --timeout=300s
kubectl wait --for=condition=ready pod -l role=coordinator --timeout=300s

# Get the service URLs
MINIKUBE_IP=$(minikube ip)
echo "Minikube IP: $MINIKUBE_IP"

# Get NodePorts for coordinators
COORD1_NODE_PORT=$(kubectl get svc memgraph-coordinator-1-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
COORD2_NODE_PORT=$(kubectl get svc memgraph-coordinator-2-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
COORD3_NODE_PORT=$(kubectl get svc memgraph-coordinator-3-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')

# Get NodePorts for data nodes
DATA0_NODE_PORT=$(kubectl get svc memgraph-data-0-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')
DATA1_NODE_PORT=$(kubectl get svc memgraph-data-1-external -o jsonpath='{.spec.ports[?(@.name=="bolt")].nodePort}')

echo "Coordinator 1 node port: $COORD1_NODE_PORT"
echo "Coordinator 2 node port: $COORD2_NODE_PORT"
echo "Coordinator 3 node port: $COORD3_NODE_PORT"
echo "Data 0 node port: $DATA0_NODE_PORT"
echo "Data 1 node port: $DATA1_NODE_PORT"

sleep 5

# Step 2: Connect the cluster
echo ""
echo "=== Step 2: Connecting the cluster ==="

# Add coordinators
echo "Adding coordinators to the cluster..."
echo "ADD COORDINATOR 1 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD1_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-1.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-1.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "ADD COORDINATOR 2 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD2_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-2.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-2.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "ADD COORDINATOR 3 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$COORD3_NODE_PORT', 'coordinator_server': 'memgraph-coordinator-3.default.svc.cluster.local:12000', 'management_server': 'memgraph-coordinator-3.default.svc.cluster.local:10000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

# Register data instances
echo "Registering data instances..."
echo "REGISTER INSTANCE instance_0 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$DATA0_NODE_PORT', 'management_server': 'memgraph-data-0.default.svc.cluster.local:10000', 'replication_server': 'memgraph-data-0.default.svc.cluster.local:20000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT
echo "REGISTER INSTANCE instance_1 WITH CONFIG {'bolt_server': '$MINIKUBE_IP:$DATA1_NODE_PORT', 'management_server': 'memgraph-data-1.default.svc.cluster.local:10000', 'replication_server': 'memgraph-data-1.default.svc.cluster.local:20000'};" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

# Set main instance
echo "Setting main instance..."
echo "SET INSTANCE instance_0 TO MAIN;" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

sleep 5

# Step 3: Inject sample data
echo ""
echo "=== Step 3: Injecting sample data ==="
echo "Creating sample nodes and relationships..."

# Create some sample data
echo "CREATE (alice:Person {name: 'Alice', age: 30}), (bob:Person {name: 'Bob', age: 25}), (charlie:Person {name: 'Charlie', age: 35});" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT
echo "MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'}) CREATE (a)-[:KNOWS {since: 2020}]->(b);" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT
echo "MATCH (b:Person {name: 'Bob'}), (c:Person {name: 'Charlie'}) CREATE (b)-[:WORKS_WITH {project: 'Memgraph'}]->(c);" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

# Verify data is replicated
echo "Verifying data replication..."
echo "Data in main instance (instance_0):"
echo "MATCH (n) RETURN n.name as name, n.age as age;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

sleep 3

echo "Data in replica instance (instance_1):"
echo "MATCH (n) RETURN n.name as name, n.age as age;" | mgconsole --host $MINIKUBE_IP --port $DATA1_NODE_PORT

sleep 5

# Step 4: Upgrade to Memgraph 3.3
echo ""
echo "=== Step 4: Upgrading to Memgraph 3.3 ==="
echo "Performing Helm upgrade..."

helm upgrade $RELEASE_NAME memgraph/memgraph-high-availability \
    --values values_3.3.yaml \
    --wait

# Wait for pods to be ready after upgrade
echo "Waiting for pods to be ready after upgrade..."
kubectl wait --for=condition=ready pod -l role=data --timeout=300s
kubectl wait --for=condition=ready pod -l role=coordinator --timeout=300s

sleep 10

# Step 5: Verify upgrade and data integrity
echo ""
echo "=== Step 5: Verifying upgrade and data integrity ==="

# Check version
echo "Checking Memgraph version after upgrade:"
echo "SHOW VERSION;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

# Verify data is still there
echo ""
echo "Verifying data integrity after upgrade..."
echo "Data in main instance (instance_0):"
echo "MATCH (n) RETURN n.name as name, n.age as age;" | mgconsole --host $MINIKUBE_IP --port $DATA0_NODE_PORT

sleep 3

echo "Data in replica instance (instance_1):"
echo "MATCH (n) RETURN n.name as name, n.age as age;" | mgconsole --host $MINIKUBE_IP --port $DATA1_NODE_PORT

# Test cluster connectivity
echo ""
echo "Testing cluster connectivity..."
echo "SHOW INSTANCES;" | mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT

echo ""
echo "=== Upgrade Complete! ==="
echo "Memgraph has been successfully upgraded from 3.2.1 to 3.3"
echo ""
echo "Connection details:"
echo "Coordinator: $MINIKUBE_IP:$COORD1_NODE_PORT"
echo "Main Data Instance: $MINIKUBE_IP:$DATA0_NODE_PORT"
echo "Replica Data Instance: $MINIKUBE_IP:$DATA1_NODE_PORT"
echo ""
echo "To check the status of your pods, run:"
echo "kubectl get pods"
echo ""
echo "To view logs of a specific pod, run:"
echo "kubectl logs <pod-name>"
echo ""
echo "To connect to Memgraph using mgconsole:"
echo "mgconsole --host $MINIKUBE_IP --port $COORD1_NODE_PORT" 