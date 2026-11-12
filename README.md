# Ansible & IBM DataPower Gateway

## Introduction

This repository is the Ansible collection for IBM DataPower Gateway. The modules are freely provided to the open source community for automating DataPower configuration.

The controller talks to the REST management interface. DataPower does not run Python. One `httpapi` connection, one REST client, and one task per operation.

The branch `master` still holds the earlier incubator (`library/` and the `idg_*` modules). Release 1.0.0 is the collection `gr.idg`. Those old names keep working through the 1.x series and are removed in 2.0.0.

## Why the modules are built this way

A domain in DataPower is a logical partition. It groups, isolates and organizes services and configuration. Operating on that partition is a different job from changing one object inside it. The modules follow that split.

- `gr.idg.domain` manages the partition: create, delete, enable, quiesce and restart.
- `gr.idg.domain_config` manages the operation: save, export and import.
- Every other module handles one class. A key, a certificate, a file, a status reading, a sensor.

A task does one thing, and you can see it in the play. The module does not save after a change, does not wait after an action, and does not hide a second REST call. The playbook chains the rest.

A change lives in memory until `SaveConfig`. Saving is its own task, usually a handler, so one play writes several objects and saves once. `gr.idg.domain_config` with `state: saved` calls `SaveConfig` only when `SaveNeeded` is not `off`.

Run the same play twice. The idempotency of the modules is the point. The second run compares the cleaned object with what you asked for. When they match, the module does not call the write API and returns `changed: false`. `--check` does that comparison without writing. `--diff` shows `before` and `after`.

The connection lives in the inventory, once per appliance. The modules no longer take a connection dictionary.

## Your ideas

We are very interested in your ideas.

Open an issue for an error, a question, or a module you want next. If you have a use case and can describe the behavior you want, we will hammer out the details.

An example joins a release only after it has been run against a DataPower appliance, together with the collection version it was tested with. The playbooks in `examples/basic/` are that set for 1.0.0.

Send an email that introduces you and what you do. We love hearing about how you are using the modules.

David Grau and the Gallo Rojo team, david@gallorojo.com.mx

## What you need

1. [ansible-core](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html) 2.19 or later, and earlier than 2.20. Python 3.11 or later on the controller.
2. `ansible.netcommon` 8.1.0 or later. Installing `gr.idg` from Galaxy pulls it in.
3. The REST management interface of a DataPower Gateway, usually port `5554`. A fast laboratory is [IBM DataPower Gateway for Docker](https://hub.docker.com/r/ibmcom/datapower/). On the appliance CLI:

```
conf; web-mgmt; admin-state enabled; exit; rest-mgmt; admin-state enabled; exit; exit;
```

`become` does not apply. Each REST call waits `ansible_httpapi_timeout` seconds. The default is 30. Raise it for an export, an import, or a long synchronization.

## Install

Pin the collection in the project that runs your playbooks:

```yaml
collections:
  - name: gr.idg
    version: ">=1.0.0,<2.0.0"
```

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install 'ansible-core>=2.19.0,<2.20'
ansible-galaxy collection install -r requirements.yml
ansible-doc gr.idg.domain
```

Until the Galaxy namespace is published, install the Git tag of this repository. The collection name is still `gr.idg`:

```yaml
collections:
  - name: git+https://github.com/dgraum/datapower-ansible.git
    type: git
    version: v1.0.0
```

`ansible-galaxy collection list gr.idg` prints the path. The first playbooks are installed with the collection, under `examples/basic/`.

## Inventory

Copy `examples/basic/inventory.yml` and set the address. The password belongs in Ansible Vault.

```yaml
all:
  hosts:
    idg:
      ansible_host: idg.example.com
      ansible_connection: ansible.netcommon.httpapi
      ansible_network_os: gr.idg.rest_mgmt
      ansible_httpapi_use_ssl: true
      ansible_httpapi_validate_certs: true
      ansible_httpapi_port: 5554
      ansible_user: admin
      ansible_password: "{{ vault_idg_password }}"
      ansible_httpapi_timeout: 30
```

```bash
mkdir -p group_vars/all
ansible-vault encrypt_string --name vault_idg_password > group_vars/all/vault.yml
```

A laboratory may set `ansible_httpapi_validate_certs: false`. Production keeps `true`. Do not run playbooks with `-vvvv`. The connection debugger can print request headers.

`gr.idg.domain` addresses the domain with `name`. Every other module uses `domain`, so one default covers the play:

```yaml
module_defaults:
  group/gr.idg.idg:
    domain: payments
```

## Try it

Read first. This playbook does not change the appliance.

```bash
ansible-playbook -i inventory.yml examples/basic/read_identity.yml --syntax-check
ansible-playbook -i inventory.yml examples/basic/read_identity.yml
```

You get firmware, model and serial, then the domain list. Run it again. The result is the same and nothing was written.

Read one object the same way:

```bash
ansible-playbook -i inventory.yml examples/basic/read_object.yml \
  -e config_domain=default \
  -e config_class=Domain \
  -e config_name=default
```

When you are ready to create a domain, look before you write, then run it, then run it again:

```bash
ansible-playbook -i inventory.yml examples/basic/ensure_domain.yml \
  -e domain_name=example --check --diff
ansible-playbook -i inventory.yml examples/basic/ensure_domain.yml \
  -e domain_name=example
ansible-playbook -i inventory.yml examples/basic/ensure_domain.yml \
  -e domain_name=example
```

The first real run creates the domain and the handler saves it. The second run returns `changed: false`.

An export is asynchronous. The module returns `action_id`. The next task waits:

```yaml
- name: Export the domain
  gr.idg.domain_config:
    domain: payments
    state: exported
  register: exported

- name: Wait for the export
  gr.idg.action_queue:
    domain: payments
    action_id: "{{ exported.action_id }}"
  register: queue
  until: queue.status in ['processed', 'completed']
  retries: 30
  delay: 2
```

A play that writes to one appliance uses `serial: 1`. For a change window: `--syntax-check`, then `--check --diff`, then the run.

## Documentation

`ansible-doc gr.idg.domain` is the reference for each option. The same pattern works for every module in the collection.

The families are domain and checkpoint, status and sensors, files, configuration (including keys and certificates), and actions such as ping, traceroute, CLI and cache. The porting notes from `idg_*` and the old connection dictionary are in [docs/migration_guide.md](docs/migration_guide.md).

Exports are confidential. A file written on the controller is mode `0600`. The collection redacts `password`, `passphrase`, `secret`, `privatekey`, `private_key`, `sslkey` and `credential` in results, in `--diff` and in error messages.

## License

GPL-3.0-or-later.
