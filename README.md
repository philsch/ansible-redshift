# Ansible Redshift Module (Alpha)

Module to manage Redshift:
 - Users
 - Groups
 - Privileges on databases, schemas and tables
 
This module is inspired by the postgresql_user core module of Ansible, but uses the SQL syntax needed by Redshift.

## Dependencies

The machine targeted by Ansible needs to have installed:

 - `pg8000` Python psql package, does not rely on any further external packages

## Integration Testing

|                     | Function                         | Note                                        |
| ------------------- | -------------------------------- | ------------------------------------------- |
| :white_check_mark:  | Create Users / Groups            |                                             |
| :white_check_mark:  | Delete Users / Groups            |                                             |                                      
| :white_check_mark:  | Set / Revoke SUPERUSER           |                                             |                                      
| :white_check_mark:  | Associate User and Group         | Only 1:1, see *Assign an user to groups*    |
| :warning:           | Schema / Table privileges        | No integration tests yet                    |   

See [test/integration/](test/integration/) for details. Tested with Ansible 2.2.1 and Redshift Custer 1.0.1564.
 
## Usage

### Installation

Copy the provided Python script inside `/lib` into a location for Ansible libraries.

From the Ansible documentation:

> This is the default location Ansible looks to find modules:
>    
>    library = /usr/share/ansible
>
> Ansible knows how to look in multiple locations if you feed it a colon separated path, and it also will 
> look for modules in the ”./library” directory alongside a playbook.

### SSL support

The module uses by default a SSL connection, which can be turned of by setting `login_ssl: False`

### Redshift Users / Groups

**Create a normal user**
```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database 
    user: new_rs_user
    password: passwF0rN3wRsUser
    expires: '2017-01-01 00:00'
    conn_limit: 10
```

**Create a superuser**

*Note* The permission `SUPERUSER` will be transformed to Redshifts equivalent `CREATEUSER` permission.

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database 
    user: new_rs_user
    password: passwF0rN3wRsUser 
    permission_flags:
        - SUPERUSER
```

**Revoke superuser rights**

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database 
    user: new_rs_user
    password: passwF0rN3wRsUser 
    permission_flags:
        - NOSUPERUSER
```

**Update a user without the password parameter**

In case you are not storing your password anywhere (e.g. in Ansible Vault), the original password might not be
available anymore. To still be able to update other user attributes, use `update_password: on_create`.

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database 
    user: new_rs_user
    password: any_value
    update_password: on_create
```

**Create a group**

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database 
    group: new_rs_group
```

**Assign an user to groups**

*Note* Since version `0.3.0` a group MUST exist before you can assign users to it

*Note* If a user is part of other groups, the user will be removed from all groups which are not specified. This means
also the module only supports n:1 relationships of users and groups!

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    user: new_rs_user
    password: passwF0rN3wRsUser
    group: new_rs_group
```

**Remove a user from all groups**

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    user: new_rs_user
    password: passwF0rN3wRsUser
    # no group given 
    # state is implicit 'present' ('absent' would try to delete the user)
```

**Deleting users / groups**

*Note* A user or group can only be deleted if no permissions are assigned anymore for this resource.
This is something you have to do manually at the moment!

```
# remove user
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    user: new_rs_user
    password: passwF0rN3wRsUser
    state: absent

# remove group    
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    group: new_rs_group
    state: absent
```


### Privileges

For all calls to grant / revoke privileges, the `state` parameter has to be set to *present* (default). 
An *absent* state will always trigger a deletion of an user or group!

Refer also to the official AWS documentation how to set the privileges:
http://docs.aws.amazon.com/redshift/latest/dg/r_GRANT.html

**Grant full access to all tables of Schemas**

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    user: new_rs_user
    password: passwF0rN3wRsUser
    privs:
        - rs_schema_a:USAGE/ALL:ALL
    state: present
```

**Grant specific rights to different tables of Schemas**

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    user: new_rs_user
    password: passwF0rN3wRsUser
    privs:
        - rs_schema_a:USAGE/ALL:ALL
        - rs_schema_b:USAGE/ALL:SELECT,INSERT # USAGE on schema and SELECT,INSERT on all tables of this schema
        - rs_schema_c:USAGE/table_a:SELECT,INSERT/table_b:ALL # USAGE on schema and SELECT,INSERT on specific tables only
    state: present
```

**Grant rights for a group**

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    group: rs_group
    privs:
        - rs_schema_a:USAGE/ALL:ALL
        - rs_schema_b:USAGE/table_a:SELECT,INSERT/table_b:ALL
    state: present
```

*Note* Always use a extra statement for groups. If you set `user`, `group` and `privs` at the same time
the privileges will be applied to the user. This setup allows you to assign the user to a group and give special 
user-privileges at the same time like in the following example:

```
# This statement creates the group with priveleges
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    group: rs_group
    privs:
        - rs_schema_a:USAGE/ALL:ALL
        - rs_schema_b:USAGE/table_a:SELECT,INSERT/table_b:ALL
    state: present

# This statement creates a user, assign to the group and gives this user additionally access to rs_schema_c
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    user: new_rs_user
    group: rs_group
    privs:
        - rs_schema_c:USAGE/ALL:ALL
    state: present    
```

**Revoke rights**

**Note** In this current module version you have to call all schemas you gave rights like this.

```
- redshift_user:
    login_host: some-redshift.cluster.eu-central-1.redshift.amazonaws.com 
    login_user: rs_master 
    login_password: 123456Abcdef 
    db: my_database
    group: rs_group
    privs:
        - rs_schema_a #will remove all privileges from rs_schema_a and its tables
        - rs_schema_b #will remove all privileges from rs_schema_b and its tables
```

**Set rights on database level**

Not supported in this module version (yet)
 
## Developers FAQ

**Why isn't this module using psycopg2 ?**

The python psycopg2 package has `gcc` and `*-devel` as a dependency on machines based on the AWS Linux image. To
not have this dependency, a python library without external dependencies was used.

**Redshift vs PostgreSQL**

Redshift is not PostgreSQL, however we use a psql library for this module. This does the job, but at some points
the library does not behave as expected, e.g. `cursor.rowcount` is not working.

**Why is the result of a task always 'changed'?**

With release 0.2, the changed flag (also in dry-run) behaves like this:

* *working* if `update_password: on_create` is set, else *always true* because the module can't compare the 
  existing and the new password
* *always true* if `privs` are set

**When using camelCase user or group names the module throws exceptions**

NOTE: According to https://docs.aws.amazon.com/redshift/latest/dg/r_names.html

> Identifiers must consist of only UTF-8 printable characters. ASCII letters in standard and delimited identifiers are case-insensitive and are folded to lowercase in the database.

So I would strongly recommend you to stick to lowercase identifiers unless you love to track down difficult to debug issues.

## Contribute!

This module is in an early state. Feel free to contribute with bug reports or feature requests.
