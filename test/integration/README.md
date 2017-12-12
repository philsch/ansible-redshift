# Integration tests

This integration test uses Ansible to test and verify the Redshift module.

## Prerequisites

* A running Redshift database
* A target machine or this computer which can reach Redshift, and
    * has `psql` client installed
    * has `pg8000` python package installed
* Rename `test/integration/group_vars/all.example.yml` to `all.yml` and configure it

## Run all tests

```
export ANSIBLE_LIBRARY=../../lib/ && ansible-playbook 000_test_all.yml -i "127.0.0.1," --user ssh-user
```

Replace `127.0.0.1` with the host which has access to Redshift and don't forget the trailing comma!