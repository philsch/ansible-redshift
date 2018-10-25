#!/usr/bin/python
# -*- coding: utf-8 -*-

# This file is based on Ansible modules and has been adopted to
# be used for AWS Redshift databases.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '0.3.0'}

DOCUMENTATION = '''
---
module: redshift_user
short_description: Adds or removes a users (groups) from a AWS Redshift database.
'''

try:
    import pg8000
    from pg8000 import DatabaseError
    from pg8000 import InterfaceError
except ImportError:
    pg8000_found = False
else:
    pg8000_found = True
from ansible.module_utils.six import iteritems
import itertools

PERMISSION_LEVEL_USER = 'user'

_flags = ('SUPERUSER', 'CREATEUSER', 'CREATEDB')
VALID_FLAGS_USER = frozenset(itertools.chain(_flags, ('NO%s' % f for f in _flags)))
ALIAS_FLAGS_USER = {'SUPERUSER': 'CREATEUSER', 'NOSUPERUSER': 'NOCREATEUSER'}
VALID_FLAGS_DB = ('CREATE', 'TEMPORARY', 'TEMP', 'ALL')
VALID_FLAGS_SCHEMA = ('CREATE', 'USAGE', 'ALL')
VALID_FLAGS_TABLE = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'REFERENCES', 'ALL')


# ===========================================
# Module specific methods.
#

def check_flags(flags, level):
    flags_set = set(flags)
    if level == PERMISSION_LEVEL_USER:
        if not flags_set.issubset(VALID_FLAGS_USER):
            raise ValueError('Given permission flags %s are invalid for type user' % flags_set)

    mapped_flags = []
    for flag in flags:
        if flag in ALIAS_FLAGS_USER and ALIAS_FLAGS_USER[flag] is not None:
            mapped_flags.append(ALIAS_FLAGS_USER[flag])
        else:
            mapped_flags.append(flag)

    return mapped_flags


def parse_and_check_privs(elements):
    """Reads a list of format schema:priv1,priv2/tableA:privs/tableB:privs and transforms it to a dictionary"""
    privs_dict = {}

    # TODO: call check_flags

    for priv_string in elements:
        privs_parts = priv_string.split('/', 1)
        if len(privs_parts) == 1:
            schema = privs_parts[0].split(':')[0]
            privs_dict[schema] = {'priv': None}
            continue

        (schema_part, tables_part_string) = privs_parts
        tables_part = tables_part_string.split('/')

        (schema, schema_privs) = schema_part.split(':')
        privs_dict[schema] = {'priv': schema_privs, 'tables': {}}
        for table_part in tables_part:
            (table, table_privs) = table_part.split(':')
            privs_dict[schema]['tables'][table] = table_privs

    return privs_dict


def get_user(cursor, user):
    """Try to get full pg_user_info data of the given user (note: password is masked)"""
    query_params = {'user': user}
    query = ['SELECT * FROM pg_user_info WHERE usename=\'%(user)s\' LIMIT 1']

    query = ' '.join(query)
    cursor.execute(query % query_params)
    user = cursor.fetchone()

    if user is None:
        raise ValueError('Internal error: couldn\'t find user')

    return user


def get_user_id(cursor, user):
    """Try to get the user id of the given user"""
    user = get_user(cursor, user)

    return user[1]


def user_exists(cursor, user):
    if user is None or user == '':
        return True

    query = "SELECT usename FROM pg_user_info WHERE usename=%(user)s"
    cursor.execute(query, {"user": user})
    return cursor.fetchone() is not None


def user_change(cursor, user, password, flags, expires, conn_limit, type = 'CREATE'):
    """Create a Redshift user"""
    if user is None or user == '':
        return True

    query_params = {'type': type, 'user': user, 'password': password, 'expires': expires, 'conn_limit': conn_limit}
    query = ['%(type)s USER %(user)s']

    if password is None and type == 'CREATE':
        raise ValueError('Password must not be empty when creating a user')
    if password is not None:
        query.append("WITH PASSWORD \'%(password)s\'")
    if expires is not None:
        query.append("VALID UNTIL %(expires)s")
    if conn_limit is not None:
        query.append("CONNECTION LIMIT %(conn_limit)s")
    flags = check_flags(flags, PERMISSION_LEVEL_USER)

    query.extend(flags)
    query = ' '.join(query)

    cursor.execute(query % query_params)
    return True


def user_delete(cursor, user):
    """Try to remove a user. Returns True if successful otherwise False"""
    query_params = {'user': user}
    query = ['DROP USER %(user)s']

    query = ' '.join(query)

    cursor.execute(query % query_params)
    return True


def group_exists(cursor, group):
    """Check if a group exists"""
    if group is None or group == '':
        return True

    query = "select groname from pg_group where groname=%(group)s"
    cursor.execute(query, {"group": group})
    return cursor.fetchone() is not None


def group_add(cursor, group):
    """Create a new group"""
    query_params = {'group': group}
    query = ['CREATE GROUP %(group)s']

    query = ' '.join(query)

    cursor.execute(query % query_params)
    return True


def group_delete(cursor, group):
    """Try to delete a group"""
    query_params = {'group': group}
    query = ['DROP GROUP %(group)s']

    query = ' '.join(query)

    cursor.execute(query % query_params)
    return True

def group_assign(cursor, groups, user):
    """Adds user to the groups and removes the user from not mentioned groups"""
    user_id = get_user_id(cursor, user)

    query_params = {'uid': user_id}
    query = ['SELECT groname FROM pg_group']
    query.append('WHERE array_to_string(grolist, \',\') ~ \'^%(uid)s$|^%(uid)s,.*|.*,%(uid)s,.*|.*,%(uid)s$\';')
    query = ' '.join(query)
    cursor.execute(query % query_params)
    list_of_groups = map(lambda el: el[0], cursor.fetchall())

    assignment_updated = False
    already_assigned = False

    current_group_list=list(list_of_groups);
    for group in groups:
        for member_of_group in list_of_groups:
            if member_of_group not in groups:
                query_params = {'drop_group': member_of_group, 'drop_user': user}
                query = 'ALTER GROUP %(drop_group)s DROP USER %(drop_user)s'
                cursor.execute(query % query_params)
                assignment_updated = True

        if group is not None and group != '' and group not in current_group_list:
            query_params = {'group': group, 'add_user': user}
            query = 'ALTER GROUP %(group)s ADD USER %(add_user)s'
            cursor.execute(query % query_params)
            assignment_updated = True

    return assignment_updated

def apply_privs(cursor, privs, user, group):
    """Set permissions for schema, if user and group is set the privs are applied to the user only"""
    privs_map = parse_and_check_privs(privs)
    for (schema, schema_dict) in iteritems(privs_map):
        query_params = {'group': group, 'user': user, 'schema': schema}
        query = ['REVOKE ALL ON SCHEMA %(schema)s ']
        if user != '':
            query.append('FROM %(user)s')
        if group != '' and user == '':
            query.append('FROM GROUP %(group)s')
        query = ' '.join(query)
        cursor.execute(query % query_params)

        query = ['REVOKE ALL ON ALL TABLES IN SCHEMA %(schema)s ']
        if user != '':
            query.append('FROM %(user)s')
        if group != '' and user == '':
            query.append('FROM GROUP %(group)s')
        query = ' '.join(query)
        cursor.execute(query % query_params)

        if schema_dict['priv'] is None or schema_dict['priv'] == '':
            continue

        query_params = {'group': group, 'user': user, 'privs': schema_dict['priv'], 'schema': schema}
        query = ['GRANT %(privs)s ON SCHEMA %(schema)s ']
        if user != '':
            query.append('TO %(user)s')
        if group != '' and user == '':
            query.append('TO GROUP %(group)s')
        query = ' '.join(query)
        cursor.execute(query % query_params)

        for (table, table_privs) in iteritems(schema_dict['tables']):
            query_params = {'group': group, 'user': user, 'privs': table_privs, 'schema': schema, 'table': table}
            query = ['GRANT %(privs)s']
            if table == 'ALL':
                query.append('ON ALL TABLES IN SCHEMA %(schema)s')
            else:
                query.append('ON TABLE %(schema)s.%(table)s')
            if user != '':
                query.append('TO %(user)s')
            if group != '' and user == '':
                query.append('TO GROUP %(group)s')

            query = ' '.join(query)
            cursor.execute(query % query_params)

    return len(privs_map) > 0

# ===========================================
# Module execution.
#

def main():
    module = AnsibleModule(
        argument_spec=dict(
            login_user=dict(default="rs_master"),
            login_password=dict(default="", no_log=True),
            login_host=dict(default=""),
            login_unix_socket=dict(default=""),
            login_ssl=dict(default=True, type='bool'),
            port=dict(default=5439, type='int'),
            db=dict(required=True),
            user=dict(default=''),
            password=dict(default=None, no_log=True),
            update_password=dict(default="always", choices=["always", "on_create"]),
            group=dict(default='',type='list'),
            state=dict(default="present", choices=["absent", "present"]),
            permission_flags=dict(default=[], type='list'),
            privs=dict(default=[], type='list'),
            expires=dict(default=None),
            conn_limit=dict(default=None)
        ),
        supports_check_mode=True
    )

    user = module.params["user"]
    password = module.params["password"]
    update_password = module.params["update_password"]
    state = module.params["state"]
    db = module.params["db"]
    group = module.params["group"]
    port = module.params["port"]
    permission_flags = module.params["permission_flags"]
    privs = module.params["privs"]
    expires = module.params["expires"]
    conn_limit = module.params["conn_limit"]

    if not pg8000_found:
        module.fail_json(msg="the python pg8000 module is required")

    # To use defaults values, keyword arguments must be absent, so
    # check which values are empty and don't include in the **kw
    # dictionary
    params_map = {
        "login_host": "host",
        "login_user": "user",
        "login_password": "password",
        "login_ssl": "ssl",
        "port": "port",
        "db": "database"
    }
    kw = dict((params_map[k], v) for (k, v) in iteritems(module.params)
              if k in params_map and v != "")

    # If a login_unix_socket is specified, incorporate it here.
    is_localhost = "host" not in kw or kw["host"] == "" or kw["host"] == "localhost"
    if is_localhost and module.params["login_unix_socket"] != "":
        kw["host"] = module.params["login_unix_socket"]

    cursor = None
    try:
        pg8000.paramstyle = "pyformat"
        db_connection = pg8000.connect(**kw)
        db_connection.autocommit = False
        cursor = db_connection.cursor()
    except InterfaceError:
        e = get_exception()
        module.fail_json(msg="unable to connect to database, check credentials and SSL flag!: %s " % e)
    except Exception:
        e = get_exception()
        module.fail_json(msg="unable to connect to database: %s" % e)

    kw = {'user': user, 'group': group}
    changed = False
    user_added = False
    group_added = False
    user_removed = False
    group_removed = False

    # ===========================================
    # Main decision tree
    #
    try:
        if state == "present":
            if user != '':
                if not user_exists(cursor, user):
                    user_change(cursor, user, password, permission_flags, expires, conn_limit)
                    changed = True
                    user_added = True
                else:
                    current_user_data = get_user(cursor, user)
                    if update_password == "on_create":
                        password = None
                    user_change(cursor, user, password, permission_flags, expires, conn_limit, 'ALTER')
                    updated_user_data = get_user(cursor, user)
                    changed = update_password == "always" or current_user_data != updated_user_data

            if user == '' and group != '' and not group_exists(cursor, group):
                group_add(cursor, group)
                changed = True
                group_added = True

            group_updated = False
            if user != '':
                group_updated = group_assign(cursor, group, user)

            privs_updated = apply_privs(cursor, privs, user, group)

            changed = changed or group_updated or privs_updated

        # absent case
        else:
            if user != '' and user_exists(cursor, user):
                group_assign(cursor, None, user)
                user_delete(cursor, user)
                changed = True
                user_removed = True

            if user == '' and group != '' and group_exists(cursor, group):
                group_delete(cursor, group)
                changed = True
                group_removed = True


    except ValueError:
        e = get_exception()
        module.fail_json(msg="Invalid module input: %s" % e)
    except (InterfaceError, DatabaseError):
        e = get_exception()
        module.fail_json(msg="Database error occured: %s" % e)

    if changed:
        if module.check_mode:
            db_connection.rollback()
        else:
            db_connection.commit()

    cursor.close()

    kw['changed'] = changed
    kw['user_added'] = user_added
    kw['group_added'] = group_added
    kw['user_removed'] = user_removed
    kw['group_removed'] = group_removed
    module.exit_json(**kw)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.database import *

if __name__ == '__main__':
    main()
