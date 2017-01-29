#!/usr/bin/python
# -*- coding: utf-8 -*-

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '0.1'}

DOCUMENTATION = '''
---
module: redshift_user
short_description: Adds or removes a users (groups) from a AWS Redshift database.
'''

EXAMPLES = '''
TODO EXAMPLES

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
ALIAS_FLAGS_USER = {'SUPERUSER': 'CREATEUSER'}


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
        if ALIAS_FLAGS_USER[flag] is not None:
            mapped_flags.append(ALIAS_FLAGS_USER[flag])
        else:
            mapped_flags.append(flag)

    return mapped_flags


def get_user_id(cursor, user):
    """Try to get the user id of the given user"""
    query_params = {'user': user}
    query = ['SELECT usesysid FROM pg_user_info WHERE usename=\'%(user)s\' LIMIT 1']

    query = ' '.join(query)
    cursor.execute(query % query_params)
    user = cursor.fetchone()

    if user is None:
        raise ValueError('Internal error: couldn\'t find user to get id')

    return user[0]


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
    query = ['%(type)s USER %(user)s WITH PASSWORD \'%(password)s\'']

    if password is None:
        raise ValueError('Password must not be empty when creating a user')
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


def group_assign(cursor, group, user):
    """Adds user to the group and removes the user from not mentioned groups"""
    #TODO: support multiple groups

    user_id = get_user_id(cursor, user)

    query_params = {'uid': user_id}
    query = ['SELECT groname FROM pg_group']
    query.append('WHERE array_to_string(grolist, \',\') ~ \'^%(uid)s$|^%(uid)s,.*|.*,%(uid)s,.*|.*,%(uid)s$\';')
    query = ' '.join(query)
    cursor.execute(query % query_params)
    list_of_groups = map(lambda el: el[0], cursor.fetchall())

    for member_of_group in list_of_groups:
        if member_of_group != group:
            query_params = {'drop_group': member_of_group, 'drop_user': user}
            query = 'ALTER GROUP %(drop_group)s DROP USER %(drop_user)s'
            cursor.execute(query % query_params)

    if group is not None and group != '':
        query_params = {'group': group, 'add_user': user}
        query = 'ALTER GROUP %(group)s ADD USER %(add_user)s'
        cursor.execute(query % query_params)

    return True


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
            port=dict(default=5439, type='int'),
            db=dict(required=True),
            user=dict(default=''),
            password=dict(default=None, no_log=True),
            group=dict(default=''),
            schema=dict(default=''),
            state=dict(default="present", choices=["absent", "present"]),
            permission_flags=dict(default=[], type='list'),
            priv=dict(default=[], type='list'),
            no_password_changes=dict(type='bool', default='no'),
            expires=dict(default=None),
            conn_limit=dict(default=None)
        ),
        supports_check_mode=True
    )

    user = module.params["user"]
    password = module.params["password"]
    state = module.params["state"]
    db = module.params["db"]
    group = module.params["group"]
    schema = module.params["schema"]
    if db == '' and user == '' and group == '' and schema == '':
        module.fail_json(msg="At least db, user, group or schema must be set")
    port = module.params["port"]
    no_password_changes = module.params["no_password_changes"]
    permission_flags = module.params["permission_flags"]
    priv = module.params["priv"]
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
        "port": "port",
        "db": "database"
    }
    kw = dict((params_map[k], v) for (k, v) in iteritems(module.params)
              if k in params_map and v != "")

    # If a login_unix_socket is specified, incorporate it here.
    is_localhost = "host" not in kw or kw["host"] == "" or kw["host"] == "localhost"
    if is_localhost and module.params["login_unix_socket"] != "":
        kw["host"] = module.params["login_unix_socket"]

    try:
        pg8000.paramstyle = "pyformat";
        db_connection = pg8000.connect(**kw)
        db_connection.autocommit = False
        cursor = db_connection.cursor()
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
            if not user_exists(cursor, user):
                user_change(cursor, user, password, permission_flags, expires, conn_limit)
                changed = True
                user_added = True
            else:
                user_change(cursor, user, password, permission_flags, expires, conn_limit, 'ALTER')
                changed = True

            if not group_exists(cursor, group):
                group_add(cursor, group)
                changed = True
                group_added = True

            group_assign(cursor, group, user)

        # absent case
        else:
            if user != '' and user_exists(cursor, user):
                group_assign(cursor, None, user)
                user_delete(cursor, user)
                changed = True
                user_removed = True

            if group != '' and group_exists(cursor, group):
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
