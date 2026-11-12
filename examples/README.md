# Examples

`examples/basic/` is the supported set for this release. The playbooks use placeholder names and do not contain appliance addresses.

| Playbook | Effect |
| --- | --- |
| `basic/read_identity.yml` | Reads firmware, model, serial and domain status. |
| `basic/read_object.yml` | Reads one configuration object. |
| `basic/ensure_domain.yml` | Creates one domain when it is missing, then saves. |

Start with the read-only playbook. Run `--syntax-check`, then the playbook. Use `--check --diff` before `ensure_domain.yml`.

An example is added in a later release only after it has been run against a DataPower appliance and reviewed with the collection version that ships beside it. The rule is in [docs/examples.md](../docs/examples.md).
