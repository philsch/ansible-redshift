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

### Redshift Users / Groups

**Create a normal user**
```
- redshift_user:
    login_host=some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user=rs_master 
    login_password=123456Abcdef 
    db=myDatabase 
    user=newRsUser
    password=passwF0rN3wRsUser 
```

**Create a superuser**

*Note* The permission `SUPERUSER` will be transformed to Redshifts equivalent `CREATEUSER` permission.

```
- redshift_user:
    login_host=some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user=rs_master 
    login_password=123456Abcdef 
    db=myDatabase 
    user=newRsUser
    password=passwF0rN3wRsUser 
    permission_flags=SUPERUSER
```

**Create a group**

```
- redshift_user:
    login_host=some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user=rs_master 
    login_password=123456Abcdef 
    db=myDatabase 
    group=newRsGroup
```

**Assign an user to groups**

*Note* This statement will create user and group (if not already existing) and assign the user to that group.

*Note* If a user is part of other groups, the user will be removed from all groups which are not specified.

**Note** This module currently does *only* support a 1:1 relationship of user and group!

```
- redshift_user:
    login_host=some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user=rs_master 
    login_password=123456Abcdef 
    db=myDatabase
    user=newRsUser
    password=passwF0rN3wRsUser
    group=newRsGroup
```

**Remove a user from all groups**

```
- redshift_user:
    login_host=some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user=rs_master 
    login_password=123456Abcdef 
    db=myDatabase
    user=newRsUser
    password=passwF0rN3wRsUser
    # no group given 
    # state is implicit 'present' ('absent' would try to delete the user)
```

**Deleting users / groups**

*Note* A user or group can only be deleted if no permissions are assigned anymore for this resource.
This is something you have to do manually at the moment!

```
- redshift_user:
    login_host=some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user=rs_master 
    login_password=123456Abcdef 
    db=myDatabase
    user=newRsUser
    password=passwF0rN3wRsUser
    group=newRsGroup
    state=absent
```


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

*Why is the result of a task always 'changed'?*

I haven't found a way so far to check if the password of a user has actually changed or not. So even if no
input parameter has changed, the module still sends an `ALTER` command to Redshift. But you can see from the
other returned flags what was / will be changed.

*Contribute!*

This module is in an early state. Feel free to contribute with bug reports or feature requests.