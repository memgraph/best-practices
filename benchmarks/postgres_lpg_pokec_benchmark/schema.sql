DROP PROPERTY GRAPH IF EXISTS pokec;
DROP TABLE IF EXISTS friendships;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id                    integer PRIMARY KEY,
    completion_percentage integer,
    gender                text,
    age                   integer
);

CREATE TABLE friendships (
    user_id   integer NOT NULL REFERENCES users (id),
    friend_id integer NOT NULL REFERENCES users (id),
    PRIMARY KEY (user_id, friend_id)
);

CREATE INDEX friendships_friend_id_idx ON friendships (friend_id);
