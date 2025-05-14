from neo4j import GraphDatabase
import time

driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)

def create_global_node(session):
    session.run("MERGE (:Global {id: 1})")

def create_trigger(session, name, phase):
    session.run(f"""
        CREATE TRIGGER {name}
        ON CREATE {phase} COMMIT
        EXECUTE
        UNWIND createdVertices AS node
        MATCH (g:Global {{id: 1}})
        CREATE (node)-[:CONNECTED_TO]->(g)
    """)

def drop_trigger(session, name):
    try:
        result = session.run(f"DROP TRIGGER {name}")
        result.consume()
    except Exception as e:
        print(f"Trigger {name} does not exist. Nothing to drop.")

def check_connections(session):
    result = session.run("""
        MATCH (n:TestNode)-[:CONNECTED_TO]->(g:Global)
        RETURN n.id AS node_id, g.id AS global_id
    """)
    return result.data()

def modify_global_node(tx):
    tx.run("MATCH (g:Global {id: 1}) SET g.temp = 'modified'")

def create_new_node(tx, node_id):
    tx.run("CREATE (:TestNode {id: $id})", id=node_id)


def test_trigger_phase(phase_name, trigger_name):
    with driver.session() as setup_session:
        print(f"\n--- {phase_name} TRIGGER TEST ---")
        drop_trigger(setup_session, trigger_name)
        create_trigger(setup_session, trigger_name, phase_name)
        print(f"{phase_name} COMMIT trigger created.")

    # Simulate tx1 in session1
    session1 = driver.session()
    tx1 = session1.begin_transaction()
    modify_global_node(tx1)
    print("tx1: Modified global node (not committed).")

    # Simulate tx2 in session2
    session2 = driver.session()
    tx2 = session2.begin_transaction()
    create_new_node(tx2, node_id=101 if phase_name == "BEFORE" else 102)
    try:
        tx2.commit()
        print("f{phase_name} COMMIT TRIGGER didn't fail!")
        exit(1)
    except Exception as e:
        print(f"{phase_name} COMMIT TRIGGER failed as expected ")

    # Commit tx1
    tx1.commit()
    session1.close()
    session2.close()
    print("tx1: Committed.")

    time.sleep(1 if phase_name == "AFTER" else 0.1)

    # Check connections
    with driver.session() as read_session:
        connections = check_connections(read_session)
        print("Connections:")
        for record in connections:
            print(record)

        drop_trigger(read_session, trigger_name)
        print(f"{phase_name} COMMIT trigger dropped.")


if __name__ == "__main__":
    with driver.session() as session:
        create_global_node(session)
        print("Global node created.")

    test_trigger_phase("BEFORE", "connect_before")
    test_trigger_phase("AFTER", "connect_after")

    driver.close()
