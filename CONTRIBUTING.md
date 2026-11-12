# Contributing

Issues and pull requests go to [github.com/dgraum/datapower-ansible](https://github.com/dgraum/datapower-ansible).

## Develop from a clone

The controller needs `ansible-core` 2.19 and Python 3.11 or later.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
mkdir -p .collections/ansible_collections/gr
ln -sfn ../../../ .collections/ansible_collections/gr/idg
```

`ansible.cfg` in this clone adds `.collections` to the collection path. That file is for development. It is not part of the Galaxy tarball.

```bash
PYTHONPATH=.collections python3 -m pytest tests/unit -q
ansible-galaxy collection build
ansible-playbook --syntax-check -i examples/basic/inventory.yml examples/basic/read_identity.yml
```

## Changes

A module performs one operation. It does not save, wait or chain a second REST call. Playbooks do that.

User-facing text in modules, examples and docs is English.

A behavior change needs a fragment in `changelogs/fragments/`. The fragment types are listed in `changelogs/config.yaml`.

An example follows [docs/examples.md](docs/examples.md). It ships in the same tag as the modules it was tested with.

## What never goes in a commit

Passwords, vault password files, certificates, private keys, appliance addresses from a real network, and export files. The public history is created from a clean tree. Do not push an older history that already contains them.
