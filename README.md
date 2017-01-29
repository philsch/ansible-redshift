# Ansible Redshift Module (Alpha)

Module to manage Redshift:
 - Users
 - Groups
 - Privileges on databases, schemas and tables
 
This module is inspired by the prostresql_user core module of Ansible, but uses the SQL syntax needed by Redshift.

 
## Dependencies

The machine targeted by Ansible needs to have installed:

 - `pg8000` Python psql package, does not rely on any further external packages
 
## Usage

### Installation

### Create Users / Groups

*Note* The permission `SUPERUSER` will be transformed to Redshifts equivalent `CREATEUSER` permission.

### Grant privileges

**Note** Granting access to a schema will *not* give automatically access to all tables in this schema.
See http://docs.aws.amazon.com/redshift/latest/dg/r_GRANT.html


 
## Developers FAQ

*Why isn't this module using psycopg2 ?*

The python psycopg2 package has `gcc` and `*-devel` as a dependency on machines based on the AWS Linux image. To
not have this dependency, a python library without external dependencies was used.

*Redshift vs PostgreSQL*

Redshift is not PostgreSQL, however we use a psql library for this module. This does the job, but at some points
the library does not behave as expected, e.g. `cursor.rowcount` is not working.

*Contribute!*

This module is in an early state. Feel free to contribute with bug reports or feature requests.