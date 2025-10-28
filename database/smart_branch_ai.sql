--
-- PostgreSQL database cluster dump
--

-- Started on 2025-10-28 15:12:23

SET default_transaction_read_only = off;

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

--
-- Roles
--

CREATE ROLE postgres;
ALTER ROLE postgres WITH SUPERUSER INHERIT CREATEROLE CREATEDB LOGIN REPLICATION BYPASSRLS PASSWORD 'SCRAM-SHA-256$4096:Zu881vg2i3CrjeomsMLmlQ==$r2ySrC08zQEhR9X3mPSIcLQa7OPpbxf6tC885D74b3U=:vILwMaEli+rc8pTeHaGKZGK9Rp7avqULB3Lfzsewo/s=';

--
-- User Configurations
--








-- Completed on 2025-10-28 15:12:23

--
-- PostgreSQL database cluster dump complete
--

