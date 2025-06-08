from gqlalchemy import Memgraph
from typing import List, Tuple
import time
import random
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class PermissionAnalyzer:
    def __init__(self):
        self.db = Memgraph(
            host=os.getenv('MEMGRAPH_HOST', 'localhost'),
            port=int(os.getenv('MEMGRAPH_PORT', '7687')),
            username=os.getenv('MEMGRAPH_USERNAME', ''),
            password=os.getenv('MEMGRAPH_PASSWORD', ''),
            encrypt=os.getenv('MEMGRAPH_ENCRYPT', 'false').lower() == 'true'
        )

    def verify_data(self):
        """Verify that data was migrated correctly"""
        queries = [
            "MATCH (u:User) RETURN count(u) as count",
            "MATCH (g:Group) RETURN count(g) as count",
            "MATCH (r:Role) RETURN count(r) as count",
            "MATCH (a:App) RETURN count(a) as count",
            "MATCH (p:Permission) RETURN count(p) as count",
            "MATCH ()-[r:MEMBER_OF]->() RETURN count(r) as count",
            "MATCH ()-[r:HAS_ROLE]->() RETURN count(r) as count",
            "MATCH ()-[r:CAN_ACCESS]->() RETURN count(r) as count",
            "MATCH ()-[r:HAS_PERMISSION]->() RETURN count(r) as count"
        ]
        
        print("\nVerifying data creation:")
        for query in queries:
            result = next(self.db.execute_and_fetch(query))
            print(f"{query}: {result['count']}")

    def check_user_permission(self, user_id: str, app_name: str) -> dict:
        """Check if a user has permission to access an app and return the access path"""
        query = """
        MATCH (u:User {id: $user_id}), (a:App {name: $app_name})
        OPTIONAL MATCH path = (u)-[:MEMBER_OF]->(g:Group)-[:HAS_ROLE]->(r:Role)-[:CAN_ACCESS]->(a)
        WITH path, a
        OPTIONAL MATCH (a)-[:HAS_PERMISSION]->(p:Permission)
        WHERE path IS NOT NULL
        RETURN 
            path IS NOT NULL as has_access,
            CASE 
                WHEN path IS NOT NULL THEN [node IN nodes(path) | 
                    labels(node)[0] + ': ' + 
                    CASE 
                        WHEN node.id IS NOT NULL THEN node.id 
                        ELSE node.name 
                    END
                ]
                ELSE []
            END as access_path,
            collect(DISTINCT p.name) as permissions,
            count(DISTINCT p) as permission_count
        """
        start_time = time.time()
        result = next(self.db.execute_and_fetch(query, {"user_id": user_id, "app_name": app_name}))
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        result['duration_ms'] = duration
        return result

    def find_test_cases(self) -> List[Tuple[str, str]]:
        """Find some valid user-app pairs for testing"""
        query = """
        MATCH (u:User)-[:MEMBER_OF]->(:Group)-[:HAS_ROLE]->(:Role)-[:CAN_ACCESS]->(a:App)
        WITH u, collect(a) as apps
        WITH u, apps[0] as first_app, apps[2] as third_app
        WHERE first_app IS NOT NULL AND third_app IS NOT NULL
        RETURN u.id as user_id, 
               first_app.name as first_app,
               third_app.name as third_app
        LIMIT 1
        """
        result = next(self.db.execute_and_fetch(query))
        return [
            (result['user_id'], result['first_app']),
            (result['user_id'], result['third_app'])
        ]

    def analyze_user_permissions(self, user_id: str = None) -> dict:
        """Analyze all permissions available to a user through their group memberships"""
        if user_id is None:
            # Get a random user if none specified
            query = "MATCH (u:User) RETURN u.id as user_id ORDER BY rand() LIMIT 1"
            result = next(self.db.execute_and_fetch(query))
            user_id = result['user_id']

        query = """
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)-[:HAS_ROLE]->(r:Role)-[:CAN_ACCESS]->(a:App)-[:HAS_PERMISSION]->(p:Permission)
        WITH u, g, r, a, collect(DISTINCT p.name) as perms
        RETURN 
            u.id as user_id,
            count(DISTINCT g) as total_groups,
            count(DISTINCT r) as total_roles,
            count(DISTINCT a) as total_apps,
            collect(DISTINCT {
                group: g.name,
                role: r.name,
                app: a.name,
                permissions: perms
            }) as access_details
        """
        
        start_time = time.time()
        result = next(self.db.execute_and_fetch(query, {"user_id": user_id}))
        duration = (time.time() - start_time) * 1000
        
        # Get total unique permissions
        perm_query = """
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(:Group)-[:HAS_ROLE]->(:Role)-[:CAN_ACCESS]->(:App)-[:HAS_PERMISSION]->(p:Permission)
        RETURN count(DISTINCT p) as total_permissions
        """
        perm_result = next(self.db.execute_and_fetch(perm_query, {"user_id": user_id}))
        
        result['query_time_ms'] = duration
        result['total_unique_permissions'] = perm_result['total_permissions']
        return result

def main():
    analyzer = PermissionAnalyzer()
    
    # Verify data migration
    analyzer.verify_data()
    
    # Run permission checks
    print("\nPermission Check Results:\n")
    print("| User ID | App Name | Access Time (ms) | Path | Permissions | Permission Count |")
    print("|----------|-----------|-----------------|------|-------------|-----------------|")
    
    test_cases = analyzer.find_test_cases()
    for user_id, app_name in test_cases:
        result = analyzer.check_user_permission(user_id, app_name)
        print(f"| {user_id} | {app_name} | {result['duration_ms']:.2f} | {' -> '.join(result['access_path'])} | {', '.join(result['permissions'])} | {result['permission_count']} |")
        
        print(f"\nDetailed analysis for {user_id} -> {app_name}:\n")
        if result['access_path']:
            group = result['access_path'][1]
            role = result['access_path'][2]
            print(f"Path through {group} and {role}:")
            print(f"- Permissions: {', '.join(result['permissions'])}")
            print(f"- Total permissions: {result['permission_count']}")
        else:
            print("No access path found")
    
    # Analyze random user's permissions
    print("\n=== Random User Permission Analysis ===\n")
    analysis = analyzer.analyze_user_permissions()
    
    print(f"Permission Analysis for User: {analysis['user_id']}")
    print(f"Query Time: {analysis['query_time_ms']:.2f}ms\n")
    
    print("Summary:")
    print(f"- Total Groups: {analysis['total_groups']}")
    print(f"- Total Roles: {analysis['total_roles']}")
    print(f"- Total Apps Accessible: {analysis['total_apps']}")
    print(f"- Total Unique Permissions: {analysis['total_unique_permissions']}\n")
    
    print("Detailed Access Paths:\n")
    print("| Group | Role | App | Permissions |")
    print("|--------|------|-----|-------------|")
    for detail in analysis['access_details']:
        print(f"| {detail['group']} | {detail['role']} | {detail['app']} | {', '.join(detail['permissions'])} |")

if __name__ == "__main__":
    main() 