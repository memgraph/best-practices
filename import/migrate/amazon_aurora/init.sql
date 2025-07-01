-- Initialize the database for Aurora to Memgraph migration
-- This file is automatically executed when the Aurora container starts

-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS testdb;

-- Use the testdb database
USE testdb;

-- Create the test user if it doesn't exist
CREATE USER IF NOT EXISTS 'testuser'@'%' IDENTIFIED BY 'testpass';

-- Grant all privileges on testdb to testuser
GRANT ALL PRIVILEGES ON testdb.* TO 'testuser'@'%';

-- Flush privileges to apply changes
FLUSH PRIVILEGES;

-- Show the created database
SHOW DATABASES; 