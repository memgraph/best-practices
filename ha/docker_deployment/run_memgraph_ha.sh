#!/bin/bash

echo "Cleaning up old Docker containers and volumes..."
docker stop coord1 coord2 coord3 instance1 instance2 instance3 2>/dev/null || true
docker rm coord1 coord2 coord3 instance1 instance2 instance3 2>/dev/null || true
docker volume rm mg_lib1 mg_lib2 mg_lib3 mg_lib4 mg_lib5 mg_lib6 2>/dev/null || true
docker volume rm mg_log1 mg_log2 mg_log3 mg_log4 mg_log5 mg_log6 2>/dev/null || true

export ORG_NAME="<MEMGRAPH_ORGANIZATION_NAME>"
export MEMGRAPH_ENTERPRISE_LICENSE="<MEMGRAPH_ENTERPRISE_LICENSE>"

echo "Launching Coordinator 1..."
docker run -d --name coord1 --network=host -p 7691:7691 -p 7444:7444 -v mg_lib1:/var/lib/memgraph -v mg_log1:/var/log/memgraph \
    -e MEMGRAPH_ORGANIZATION_NAME=$ORG_NAME \
    -e MEMGRAPH_ENTERPRISE_LICENSE=$MEMGRAPH_ENTERPRISE_LICENSE \
    memgraph/memgraph-mage:3.2 \
    --bolt-port=7691 --log-level=TRACE --also-log-to-stderr --coordinator-id=1 \
    --coordinator-port=10111 --management-port=12121 \
    --coordinator-hostname=localhost --nuraft-log-file=/var/log/memgraph/nuraft

echo "Launching Coordinator 2..."
docker run -d --name coord2 --network=host -p 7692:7692 -p 7445:7444 -v mg_lib2:/var/lib/memgraph -v mg_log2:/var/log/memgraph \
    -e MEMGRAPH_ORGANIZATION_NAME=$ORG_NAME \
    -e MEMGRAPH_ENTERPRISE_LICENSE=$MEMGRAPH_ENTERPRISE_LICENSE \
    memgraph/memgraph-mage:3.2 \
    --bolt-port=7692 --log-level=TRACE --also-log-to-stderr --coordinator-id=2 \
    --coordinator-port=10112 --management-port=12122 \
    --coordinator-hostname=localhost --nuraft-log-file=/var/log/memgraph/nuraft

echo "Launching Coordinator 3..."
docker run -d --name coord3 --network=host -p 7693:7693 -p 7446:7444 -v mg_lib3:/var/lib/memgraph -v mg_log3:/var/log/memgraph \
    -e MEMGRAPH_ORGANIZATION_NAME=$ORG_NAME \
    -e MEMGRAPH_ENTERPRISE_LICENSE=$MEMGRAPH_ENTERPRISE_LICENSE \
    memgraph/memgraph-mage:3.2 \
    --bolt-port=7693 --log-level=TRACE --also-log-to-stderr --coordinator-id=3 \
    --coordinator-port=10113 --management-port=12123 \
    --coordinator-hostname=localhost --nuraft-log-file=/var/log/memgraph/nuraft

echo "Launching Main Instance..."
docker run -d --name instance1 --network=host -p 7687:7687 -p 7447:7444 -v mg_lib4:/var/lib/memgraph -v mg_log4:/var/log/memgraph \
    -e MEMGRAPH_ORGANIZATION_NAME=$ORG_NAME \
    -e MEMGRAPH_ENTERPRISE_LICENSE=$MEMGRAPH_ENTERPRISE_LICENSE \
    memgraph/memgraph-mage:3.2 \
    --bolt-port=7687 --log-level=TRACE --also-log-to-stderr --management-port=13011 \
    --data-recovery-on-startup=true

echo "Launching Replica 1..."
docker run -d --name instance2 --network=host -p 7688:7688 -p 7448:7444 -v mg_lib5:/var/lib/memgraph -v mg_log5:/var/log/memgraph \
    -e MEMGRAPH_ORGANIZATION_NAME=$ORG_NAME \
    -e MEMGRAPH_ENTERPRISE_LICENSE=$MEMGRAPH_ENTERPRISE_LICENSE \
    memgraph/memgraph-mage:3.2 \
    --bolt-port=7688 --log-level=TRACE --also-log-to-stderr --management-port=13012 \
    --data-recovery-on-startup=true

echo "Launching Replica 2..."
docker run -d --name instance3 --network=host -p 7689:7689 -p 7449:7444 -v mg_lib6:/var/lib/memgraph -v mg_log6:/var/log/memgraph \
    -e MEMGRAPH_ORGANIZATION_NAME=$ORG_NAME \
    -e MEMGRAPH_ENTERPRISE_LICENSE=$MEMGRAPH_ENTERPRISE_LICENSE \
    memgraph/memgraph-mage:3.2 \
    --bolt-port=7689 --log-level=TRACE --also-log-to-stderr --management-port=13013 \
    --data-recovery-on-startup=true

echo "Waiting for instances to start..."
sleep 10

echo "Executing mgconsole commands on Coordinator 1 (port 7691)..."
MGCONSOLE="mgconsole"
COMMANDS=$(cat <<'EOF'
ADD COORDINATOR 2 WITH CONFIG {"bolt_server": "localhost:7692", "coordinator_server": "localhost:10112", "management_server": "localhost:12122"};
ADD COORDINATOR 3 WITH CONFIG {"bolt_server": "localhost:7693", "coordinator_server": "localhost:10113", "management_server": "localhost:12123"};
REGISTER INSTANCE instance_1 WITH CONFIG {"bolt_server": "localhost:7687", "management_server": "localhost:13011", "replication_server": "localhost:10001"};
REGISTER INSTANCE instance_2 WITH CONFIG {"bolt_server": "localhost:7688", "management_server": "localhost:13012", "replication_server": "localhost:10002"};
REGISTER INSTANCE instance_3 WITH CONFIG {"bolt_server": "localhost:7689", "management_server": "localhost:13013", "replication_server": "localhost:10003"};
SET INSTANCE instance_1 TO MAIN;
EOF
)

echo "$COMMANDS" | $MGCONSOLE --port=7691

echo "All Docker instances launched and configured successfully."
