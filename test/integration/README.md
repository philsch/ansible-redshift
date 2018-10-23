# Integration tests

This integration test uses Ansible to test and verify the Redshift module.

## Prerequisites

* A running Redshift database
* A target machine or this computer which can reach Redshift, and
    * has `psql` client installed
    * has `pg8000` python package installed
* Rename `test/integration/group_vars/all.example.yml` to `all.yml` and configure it

## Run all tests

If you need a *Jump-Host* inside your VPC to reach Redshift, use the following command and replace `127.0.0.1` with 
the host which has access to Redshift (don't forget the trailing comma!) and set the ssh user via 
the `--user` flag. Use `ssh-add` to add your ssh key before running the test.

```
export ANSIBLE_LIBRARY=../../lib/ && ansible-playbook 000_test_all.yml -i "127.0.0.1," --user ssh-user
```

If your Redshift is public reachable you can also run Ansible locally from your computer. However you might need
to additionally define the correct Python interpreter so the `pg8000` module is found via `-e` flag.

```
export ANSIBLE_LIBRARY=../../lib/ && ansible-playbook 000_test_all.yml -i "127.0.0.1," -c local -e 'ansible_python_interpreter=/some/virtualenv/bin/python'
```