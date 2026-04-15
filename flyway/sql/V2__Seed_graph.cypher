// Seed the graph with Person and Company nodes plus WORKS_AT relationships.

CREATE (:Person {name: 'Alice', email: 'alice@memgraph.io', role: 'Engineer'});
CREATE (:Person {name: 'Bob', email: 'bob@memgraph.io', role: 'Product Manager'});
CREATE (:Person {name: 'Charlie', email: 'charlie@techcorp.com', role: 'Data Scientist'});
CREATE (:Person {name: 'Diana', email: 'diana@techcorp.com', role: 'CTO'});

CREATE (:Company {name: 'Memgraph', founded: 2016, domain: 'graph-databases'});
CREATE (:Company {name: 'TechCorp', founded: 2010, domain: 'data-analytics'});

MATCH (p:Person {email: 'alice@memgraph.io'}), (c:Company {name: 'Memgraph'})
CREATE (p)-[:WORKS_AT {since: 2020}]->(c);

MATCH (p:Person {email: 'bob@memgraph.io'}), (c:Company {name: 'Memgraph'})
CREATE (p)-[:WORKS_AT {since: 2021}]->(c);

MATCH (p:Person {email: 'charlie@techcorp.com'}), (c:Company {name: 'TechCorp'})
CREATE (p)-[:WORKS_AT {since: 2018}]->(c);

MATCH (p:Person {email: 'diana@techcorp.com'}), (c:Company {name: 'TechCorp'})
CREATE (p)-[:WORKS_AT {since: 2015}]->(c);
