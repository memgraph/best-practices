from gqlalchemy import Memgraph
from dotenv import load_dotenv
import os
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from tqdm import tqdm
import psycopg2
from typing import List, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv('DB_USER', 'memgraph')
DB_PASS = os.getenv('DB_PASS', 'memgraph')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'iam_demo')
MEMGRAPH_HOST = os.getenv('MEMGRAPH_HOST', 'localhost')
MEMGRAPH_PORT = int(os.getenv('MEMGRAPH_PORT', '7687'))

@dataclass
class MigrationStats:
    duration: float
    count: int

def count_nodes(memgraph: Memgraph, label: str) -> int:
    """Count nodes with a specific label"""
    result = next(memgraph.execute_and_fetch(f"MATCH (n:{label}) RETURN count(n) as count"))
    return result['count']

def count_relationships(memgraph: Memgraph, type: str) -> int:
    """Count relationships of a specific type"""
    result = next(memgraph.execute_and_fetch(f"MATCH ()-[r:{type}]->() RETURN count(r) as count"))
    return result['count']

def migrate_users_chunk(chunk_data: List[Tuple[int, int]]) -> Tuple[float, int]:
    """Migrate a chunk of users from PostgreSQL to Memgraph"""
    start_time = time.time()
    
    # Create new connections in the worker process
    memgraph = Memgraph()
    pg_conn = psycopg2.connect(
        host="localhost",
        database="iam_demo",
        user="memgraph",
        password="memgraph"
    )
    pg_cursor = pg_conn.cursor()
    
    start_idx, end_idx = chunk_data
    chunk_size = end_idx - start_idx
    
    # Get initial user count
    initial_count = count_nodes(memgraph, "User")
    
    # Migrate users in this chunk
    query = """
    CALL migrate.postgresql(
        'SELECT id, name FROM users ORDER BY id LIMIT """ + str(chunk_size) + " OFFSET " + str(start_idx - 1) + """',
        {
            host: 'localhost',
            port: 5432,
            database: 'iam_demo',
            user: 'memgraph',
            password: 'memgraph'
        }
    )
    YIELD row
    CREATE (n:User {id: row.id, name: row.name});
    """
    memgraph.execute(query)
    
    # Get final user count
    final_count = count_nodes(memgraph, "User")
    users_added = final_count - initial_count
    
    # Clean up connections
    pg_cursor.close()
    pg_conn.close()
    
    duration = time.time() - start_time
    return duration, users_added

def migrate_data():
    """Migrate data from PostgreSQL to Memgraph using parallel processing"""
    total_start_time = time.time()
    stats = defaultdict(MigrationStats)
    
    # Create main process connections
    memgraph = Memgraph()
    pg_conn = psycopg2.connect(
        host="localhost",
        database="iam_demo",
        user="memgraph",
        password="memgraph"
    )
    pg_cursor = pg_conn.cursor()
    
    # Get total number of users
    pg_cursor.execute("SELECT COUNT(*) FROM users")
    total_users = pg_cursor.fetchone()[0]
    
    print("\nStarting migration process...")
    print(f"Total users to migrate: {total_users:,}")
    
    # Clear existing data
    print("\nClearing existing data...")
    clear_start = time.time()
    memgraph.execute("MATCH (n) DETACH DELETE n")
    stats['clear'] = MigrationStats(time.time() - clear_start, 0)
    
    # Create constraints
    print("Creating constraints...")
    constraints_start = time.time()
    constraints = [
        "CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE",
        "CREATE CONSTRAINT ON (g:Group) ASSERT g.name IS UNIQUE",
        "CREATE CONSTRAINT ON (r:Role) ASSERT r.name IS UNIQUE",
        "CREATE CONSTRAINT ON (a:App) ASSERT a.name IS UNIQUE",
        "CREATE CONSTRAINT ON (p:Permission) ASSERT p.name IS UNIQUE"
    ]
    for constraint in constraints:
        try:
            memgraph.execute(constraint)
        except Exception as e:
            print(f"Constraint might already exist: {e}")
    stats['constraints'] = MigrationStats(time.time() - constraints_start, len(constraints))
    
    # Migrate non-user data first (these are small enough to do in main process)
    print("\nMigrating permissions...")
    perm_start = time.time()
    initial_perm_count = count_nodes(memgraph, "Permission")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT name FROM permissions',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    CREATE (n:Permission {name: row.name});
    """)
    final_perm_count = count_nodes(memgraph, "Permission")
    stats['permissions'] = MigrationStats(time.time() - perm_start, final_perm_count - initial_perm_count)
    
    print("Migrating apps...")
    apps_start = time.time()
    initial_app_count = count_nodes(memgraph, "App")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT name FROM apps',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    CREATE (n:App {name: row.name});
    """)
    final_app_count = count_nodes(memgraph, "App")
    stats['apps'] = MigrationStats(time.time() - apps_start, final_app_count - initial_app_count)
    
    print("Migrating roles...")
    roles_start = time.time()
    initial_role_count = count_nodes(memgraph, "Role")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT name FROM roles',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    CREATE (n:Role {name: row.name});
    """)
    final_role_count = count_nodes(memgraph, "Role")
    stats['roles'] = MigrationStats(time.time() - roles_start, final_role_count - initial_role_count)
    
    print("Migrating groups...")
    groups_start = time.time()
    initial_group_count = count_nodes(memgraph, "Group")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT name FROM groups',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    CREATE (n:Group {name: row.name});
    """)
    final_group_count = count_nodes(memgraph, "Group")
    stats['groups'] = MigrationStats(time.time() - groups_start, final_group_count - initial_group_count)
    
    # Prepare user chunks for parallel processing
    num_processes = 8
    chunk_size = total_users // num_processes
    user_chunks = []
    
    for i in range(num_processes):
        start_idx = i * chunk_size + 1  # PostgreSQL IDs start at 1
        end_idx = start_idx + chunk_size if i < num_processes - 1 else total_users + 1
        user_chunks.append((start_idx, end_idx))
    
    # Migrate users in parallel
    print("\nMigrating users using parallel processing...")
    users_start = time.time()
    initial_user_count = count_nodes(memgraph, "User")
    
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        chunk_results = list(tqdm(executor.map(migrate_users_chunk, user_chunks),
                                total=num_processes,
                                desc="Processing user chunks"))
    
    # Calculate total user migration stats
    user_duration = time.time() - users_start
    total_users_added = sum(count for _, count in chunk_results)
    avg_chunk_duration = sum(duration for duration, _ in chunk_results) / len(chunk_results)
    stats['users'] = MigrationStats(user_duration, total_users_added)
    
    # Migrate relationships (after all nodes are created)
    print("\nMigrating app permissions...")
    app_perm_start = time.time()
    initial_app_perm_count = count_relationships(memgraph, "HAS_PERMISSION")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT app_id, permission_id FROM app_permissions',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    MATCH (a:App {name: row.app_id})
    MATCH (p:Permission {name: row.permission_id})
    CREATE (a)-[:HAS_PERMISSION]->(p);
    """)
    final_app_perm_count = count_relationships(memgraph, "HAS_PERMISSION")
    stats['app_permissions'] = MigrationStats(time.time() - app_perm_start, final_app_perm_count - initial_app_perm_count)
    
    print("Migrating role permissions...")
    role_perm_start = time.time()
    initial_role_perm_count = count_relationships(memgraph, "CAN_ACCESS")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT role_id, app_id FROM role_apps',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    MATCH (r:Role {name: row.role_id})
    MATCH (a:App {name: row.app_id})
    CREATE (r)-[:CAN_ACCESS]->(a);
    """)
    final_role_perm_count = count_relationships(memgraph, "CAN_ACCESS")
    stats['role_permissions'] = MigrationStats(time.time() - role_perm_start, final_role_perm_count - initial_role_perm_count)
    
    print("Migrating group roles...")
    group_role_start = time.time()
    initial_group_role_count = count_relationships(memgraph, "HAS_ROLE")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT group_id, role_id FROM group_roles',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    MATCH (g:Group {name: row.group_id})
    MATCH (r:Role {name: row.role_id})
    CREATE (g)-[:HAS_ROLE]->(r);
    """)
    final_group_role_count = count_relationships(memgraph, "HAS_ROLE")
    stats['group_roles'] = MigrationStats(time.time() - group_role_start, final_group_role_count - initial_group_role_count)
    
    print("Migrating user groups...")
    user_group_start = time.time()
    initial_user_group_count = count_relationships(memgraph, "MEMBER_OF")
    memgraph.execute("""
    CALL migrate.postgresql(
        'SELECT user_id, group_id FROM user_groups',
        {host: 'localhost', port: 5432, database: 'iam_demo', user: 'memgraph', password: 'memgraph'}
    )
    YIELD row
    MATCH (u:User {id: row.user_id})
    MATCH (g:Group {name: row.group_id})
    CREATE (u)-[:MEMBER_OF]->(g);
    """)
    final_user_group_count = count_relationships(memgraph, "MEMBER_OF")
    stats['user_groups'] = MigrationStats(time.time() - user_group_start, final_user_group_count - initial_user_group_count)
    
    # Clean up main process connections
    pg_cursor.close()
    pg_conn.close()
    
    total_duration = time.time() - total_start_time
    
    # Print detailed statistics
    print("\nMigration Statistics:")
    print("=" * 50)
    print(f"\nTotal Migration Time: {total_duration:.2f}s")
    
    print("\nNode Migration:")
    print("-" * 30)
    for node_type in ['permissions', 'apps', 'roles', 'groups', 'users']:
        s = stats[node_type]
        print(f"{node_type.capitalize()}:")
        print(f"  Count: {s.count:,}")
        print(f"  Time:  {s.duration:.2f}s")
        print(f"  Rate:  {s.count/s.duration:.1f} nodes/s")
    
    print("\nRelationship Migration:")
    print("-" * 30)
    for rel_type in ['app_permissions', 'role_permissions', 'group_roles', 'user_groups']:
        s = stats[rel_type]
        print(f"{rel_type.replace('_', ' ').capitalize()}:")
        print(f"  Count: {s.count:,}")
        print(f"  Time:  {s.duration:.2f}s")
        print(f"  Rate:  {s.count/s.duration:.1f} rels/s")
    
    print("\nParallel User Migration Details:")
    print("-" * 30)
    print(f"Number of processes: {num_processes}")
    print(f"Average chunk duration: {avg_chunk_duration:.2f}s")
    print(f"Users per process: {chunk_size:,}")
    print(f"Total throughput: {total_users_added/user_duration:.1f} users/s")

def main():
    migrate_data()

if __name__ == "__main__":
    main() 
