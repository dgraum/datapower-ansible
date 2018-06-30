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

1. Installed Ansible 2.5

2. Access to the [REST Management Interface](https://www.ibm.com/support/knowledgecenter/en/SS9H2Y_7.6.0/com.ibm.dp.doc/restmgtinterface.html) of an IDG. An excellent and fast alternative is the [IBM DataPower Gateway for Docker](https://hub.docker.com/r/ibmcom/datapower/). The following sequence of commands will configure by default the necessary services in the IDG:

```
conf; web-mgmt; admin-state enabled; exit; rest-mgmt; admin-state enabled; exit;
```

3. Clone our repository:

```shell
git clone https://github.com/dgraum/datapower-ansible.git
```

4. Switch to the repository:

```shell
cd datapower-ansible
```

5. Modify the necessary connection parameters:

```shell
vi examples/domain/idg-connection.yml
```

6. Enjoy :blush:

```shell
ansible-playbook examples/domain/create.yml -e "domain_name = test"
ansible-playbook examples/domain/quiesce.yml -e "domain_name = test"
ansible-playbook examples/domain/reset.yml -e "domain_name = test"
ansible-playbook examples/domain/unquiesce.yml -e "domain_name = test"
ansible-playbook examples/domain/save.yml -e "domain_name = default"
ansible-playbook examples/domain/restart.yml -e "domain_name = test"
ansible-playbook examples/domain/remove.yml -e "domain_name = test"
ansible-playbook examples/domain/save.yml -e "domain_name = default"
ansible-playbook examples/domain/create-multiple.yml
ansible-playbook examples/domain/remove-multiple.yml
```

Documentation
-------------

The documentation is in development, however you can use ansible-doc to review the progress.

```shell
ansible-doc -M library/modules/appliance/ibm/ idg_domain
```

License
-------

GPL V3
~~~~~~

This License does not grant permission to use the trade names, trademarks, service marks,
or product names of the Licensor, except as required for reasonable and customary use in
describing the origin of the work.
