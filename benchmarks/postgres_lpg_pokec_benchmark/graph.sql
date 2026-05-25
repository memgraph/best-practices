DROP PROPERTY GRAPH IF EXISTS pokec;

CREATE PROPERTY GRAPH pokec
    VERTEX TABLES (
        users
            LABEL person
            PROPERTIES (id, completion_percentage, gender, age)
    )
    EDGE TABLES (
        friendships
            SOURCE KEY (user_id) REFERENCES users (id)
            DESTINATION KEY (friend_id) REFERENCES users (id)
            LABEL friend_of
            PROPERTIES (user_id, friend_id)
    );

\echo
\echo === Q1: outbound friend count for user 40692 ===
SELECT count(*) AS friend_count
FROM GRAPH_TABLE (pokec
    MATCH (a IS person WHERE a.id = 40692)-[IS friend_of]->(b IS person)
    COLUMNS (b.id AS friend_id)
);

\echo
\echo === Q2: distinct friends-of-friends reachable from user 40692 in 2 hops ===
SELECT count(DISTINCT fof_id) AS reachable_in_two_hops
FROM GRAPH_TABLE (pokec
    MATCH (a IS person WHERE a.id = 40692)
          -[IS friend_of]->(b IS person)
          -[IS friend_of]->(c IS person)
    COLUMNS (c.id AS fof_id)
)
WHERE fof_id <> 40692;

\echo
\echo === Q3: average friend age for 25-year-old women (friend age > 0) ===
SELECT round(avg(friend_age)::numeric, 2) AS avg_friend_age
FROM GRAPH_TABLE (pokec
    MATCH (a IS person WHERE a.gender = 'woman' AND a.age = 25)
          -[IS friend_of]->(b IS person WHERE b.age > 0)
    COLUMNS (b.age AS friend_age)
);

\echo
\echo === Q4: top 5 most-followed users (in-degree by friend_of) ===
SELECT followed_id, count(*) AS in_degree
FROM GRAPH_TABLE (pokec
    MATCH (a IS person)-[IS friend_of]->(b IS person)
    COLUMNS (b.id AS followed_id)
)
GROUP BY followed_id
ORDER BY in_degree DESC
LIMIT 5;
