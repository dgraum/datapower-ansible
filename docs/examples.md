# Releasing an example

`examples/basic/` ships with collection 1.0.0. A later example joins a release only when all of the following are true:

1. The playbook has been run against a DataPower appliance on the collection commit that will be tagged.
2. `--syntax-check` passes, and a change playbook has been reviewed with `--check --diff`.
3. The playbook uses `hosts` from the caller's inventory. It does not contain an appliance address, a customer name, a password or a vault id from a real estate.
4. A changelog fragment names the example and the modules it uses.
5. The example and those modules are tagged together. The Git tag is `vX.Y.Z`, the same version as `galaxy.yml`.

Put the playbook in `examples/<topic>/` and add a row to `examples/README.md`. Keep the first-run path in `examples/basic/` stable. New readers start there.

Do not publish a playbook that only works on one laboratory inventory. Parameterize the domain, the class and the object name, as `examples/basic/read_object.yml` does.

The published repository contains only the examples included in that release. The collection tarball contains those directories.
