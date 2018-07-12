Ansible & IBM DataPower Gateway (IDG)
==========================

Introduction
---------------

This repository is an **incubator** for the IDG modules for Ansible.
The architecture of the modules makes use of the XML and REST Management Interfaces.
The modules in this repository **may be broken due to experimentation or refactoring**.

The IDG modules for Ansible are freely provided to the open source community for automating IDG device configurations.

Your ideas
----------

**We are very interested in your ideas!!!**

Please present us any error, question or request for improvement. What modules do you want created?, In what order?
If you have a use case and can sufficiently describe the behavior you want to see, open an issue and we will hammer out the details.

Consider sending an email that introduces yourself and what you do. We love hearing about how you're using the IDG modules for Ansible.
- David Grau and the Gallo Rojo team - david@gallorojo.com.mx

Usage
----

To test our modules, be sure to:

1. [Ansible installed](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

2. Access to the [REST Management Interface](https://www.ibm.com/support/knowledgecenter/en/SS9H2Y_7.6.0/com.ibm.dp.doc/restmgtinterface.html) of an IDG. An excellent and fast alternative is the [IBM DataPower Gateway for Docker](https://hub.docker.com/r/ibmcom/datapower/). The following sequence of commands will configure by default the necessary services in the IDG:

```
conf; web-mgmt; admin-state enabled; exit; rest-mgmt; admin-state enabled; exit; exit;
```

3. Clone our repository:

```shell
git clone https://github.com/dgraum/datapower-ansible.git
```

4. Switch to the repository:

```shell
cd datapower-ansible
```

5. ¿How does it work?

    Domains in DataPowers are very versatile. To make it easier to use, we created two modules:

    1. Focused on the management of domains as logical partition(structure) that group, asylate and organize a variety of services and configurations.
       We call this module: `idg_domain` and it offers the functionalities like: create, delete, enable, quiesce and restart the domains

    2. Another module that we call `idg_domain_config` specialized in the management of the configuration(operation).
       Here you will find actions such as: save, export, import and reset.

6. Configure the connection parameters:

    We have two sets of playbooks, one for each module. Please modify the connection variables in both.

```shell
vi examples/domain/idg-connection.yml
tee examples/domain_{config,chkpoint}/idg-connection.yml > /dev/null < examples/domain/idg-connection.yml
```

7. Enjoy :blush:

Repeat the executions, The **idempotency** of the modules is very important!!!

**Module `idg_domain`**

```shell
ansible-playbook examples/domain/create.yml -e "domain_name=test"
ansible-playbook examples/domain/quiesce.yml -e "domain_name=test"
ansible-playbook examples/domain/unquiesce.yml -e "domain_name=test"
ansible-playbook examples/domain/restart.yml -e "domain_name=test"
ansible-playbook examples/domain/update.yml -e "domain_name=test"
ansible-playbook examples/domain/remove.yml -e "domain_name=test"
ansible-playbook examples/domain/create-multiple.yml
ansible-playbook examples/domain/remove-multiple.yml
```

**Module `idg_domain_config`**

```shell
# Configure a few services in test1. Why not, also upload some files to local:/
ansible-playbook examples/domain/create.yml -e "domain_name=test1"

# Another domain
ansible-playbook examples/domain/create.yml -e "domain_name=test2"

# Save the configuration of the default domain
ansible-playbook examples/domain_config/save.yml -e "domain_name=default"

# Run and validate that the configuration of test1 has been imported into test2
ansible-playbook examples/domain_config/export-import.yml -e "origin=test1 destination=test2"

# Remove the configuration of the domain test1.
ansible-playbook examples/domain_config/reset.yml -e "domain_name=test1"

# Save and restore the services of the new domain
ansible-playbook examples/domain_config/save.yml -e "domain_name=test2"
ansible-playbook examples/domain/restart.yml -e "domain_name=test2"
```

**Module `idg_domain_chkpoint`**

```shell
ansible-playbook examples/domain_chkpoint/create.yml -e "domain_name=test2 chkpoint_name=chk-point1"

# Configure a few services in test2. Why not, also upload some files to local:/

ansible-playbook examples/domain_chkpoint/restore.yml -e "domain_name=test2 chkpoint_name=chk-point1"

ansible-playbook examples/domain_chkpoint/remove.yml -e "domain_name=test2 chkpoint_name=chk-point1"
```

Documentation
-------------

The documentation is in development, however you can use ansible-doc to review the progress.

```shell
ansible-doc -M library/modules/appliance/ibm/ idg_domain
ansible-doc -M library/modules/appliance/ibm/ idg_domain_config
ansible-doc -M library/modules/appliance/ibm/ idg_domain_chkpoint
```

License
-------

GPL V3
~~~~~~
This License does not grant permission to use the trade names, trademarks, service marks,
or product names of the Licensor, except as required for reasonable and customary use in
describing the origin of the work.
