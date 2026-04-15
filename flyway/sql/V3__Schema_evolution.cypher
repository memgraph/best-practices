// Schema evolution: add KNOWS relationships and enrich existing data.
// Demonstrates how Flyway tracks incremental graph changes.

// Add social connections between people
MATCH (a:Person {email: 'alice@memgraph.io'}), (b:Person {email: 'bob@memgraph.io'})
CREATE (a)-[:KNOWS {since: 2020, context: 'coworkers'}]->(b);

MATCH (a:Person {email: 'alice@memgraph.io'}), (c:Person {email: 'charlie@techcorp.com'})
CREATE (a)-[:KNOWS {since: 2022, context: 'conference'}]->(c);

MATCH (c:Person {email: 'charlie@techcorp.com'}), (d:Person {email: 'diana@techcorp.com'})
CREATE (c)-[:KNOWS {since: 2018, context: 'coworkers'}]->(d);

// Enrich WORKS_AT relationships with department information
MATCH (p:Person {email: 'alice@memgraph.io'})-[r:WORKS_AT]->(:Company {name: 'Memgraph'})
SET r.department = 'Engineering';

MATCH (p:Person {email: 'bob@memgraph.io'})-[r:WORKS_AT]->(:Company {name: 'Memgraph'})
SET r.department = 'Product';

MATCH (p:Person {email: 'charlie@techcorp.com'})-[r:WORKS_AT]->(:Company {name: 'TechCorp'})
SET r.department = 'Data Science';

MATCH (p:Person {email: 'diana@techcorp.com'})-[r:WORKS_AT]->(:Company {name: 'TechCorp'})
SET r.department = 'Executive';

// Add active status to all Person nodes
MATCH (p:Person) SET p.active = true;
