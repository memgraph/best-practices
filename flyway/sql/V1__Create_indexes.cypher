// Create indexes on frequently queried properties.
// Indexes speed up MATCH lookups and are essential for performant graph queries.

CREATE INDEX ON :Person(email);
CREATE INDEX ON :Person(name);
CREATE INDEX ON :Company(name);
