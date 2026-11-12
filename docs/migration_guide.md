# Migrating to gr.idg

The repository [dgraum/datapower-ansible](https://github.com/dgraum/datapower-ansible) kept the incubator modules on `master` (`idg_domain`, `idg_domain_config`, `library/`). Release 1.0.0 is the `gr.idg` collection. Those old names redirect through 1.x.

Point the inventory at `ansible.netcommon.httpapi`. Remove `connection: local` and remove the `connection` dictionary. The password belongs in `ansible_password`.

The `idg_*` names redirect to `gr.idg` through the 1.x series and are removed in 2.0.0. The new name has no prefix.

`gr.idg.domain` identifies the domain with `name`. Every other module uses `domain`. In this version, `domain_config` accepts `name` as an alias of `domain`.

`domain_config` no longer accepts `state: reseted`. Restart with `gr.idg.domain` and `state: restarted`. Save, export and import stay on `domain_config`, each in its own task.

Each module performs one operation. Saving is another task, or a handler that calls `domain_config` with `state: saved`. An action returns `action_id` and does not wait. The next task uses `action_queue` with `until`.

| Previous name | New name |
| --- | --- |
| `idg_action_queue` | `gr.idg.action_queue` |
| `idg_chkpoint` | `gr.idg.chkpoint` |
| `idg_chkpoint_status` | `gr.idg.chkpoint_status` |
| `idg_cli` | `gr.idg.cli` |
| `idg_crypto_object` | `gr.idg.crypto_object` |
| `idg_documentcache_summary` | `gr.idg.documentcache_summary` |
| `idg_domain` | `gr.idg.domain` |
| `idg_domain_active_services` | `gr.idg.domain_active_services` |
| `idg_domain_config` | `gr.idg.domain_config` |
| `idg_domain_log_level` | `gr.idg.domain_log_level` |
| `idg_domain_status` | `gr.idg.domain_status` |
| `idg_facts` | `gr.idg.facts` |
| `idg_file_management` | `gr.idg.file_management` |
| `idg_file_upload` | `gr.idg.file_upload` |
| `idg_loadbalancer_groupmembers` | `gr.idg.loadbalancer_groupmembers` |
| `idg_loadbalancer_status` | `gr.idg.loadbalancer_status` |
| `idg_log_error_summary` | `gr.idg.log_error_summary` |
| `idg_password_alias` | `gr.idg.password_alias` |
| `idg_ping` | `gr.idg.ping` |
| `idg_sensors_current` | `gr.idg.sensors_current` |
| `idg_sensors_env_fan` | `gr.idg.sensors_env_fan` |
| `idg_sensors_other` | `gr.idg.sensors_other` |
| `idg_sensors_power` | `gr.idg.sensors_power` |
| `idg_sensors_temperature` | `gr.idg.sensors_temperature` |
| `idg_sensors_voltage` | `gr.idg.sensors_voltage` |
| `idg_service_config` | `gr.idg.config` |
| `idg_service_resolve_by_endpoint` | `gr.idg.service_resolve_by_endpoint` |
| `idg_status_connectionsaccepted` | `gr.idg.status_connectionsaccepted` |
| `idg_status_cpu` | `gr.idg.status_cpu` |
| `idg_status_datetime` | `gr.idg.status_datetime` |
| `idg_status_ethernet_interface` | `gr.idg.status_ethernet_interface` |
| `idg_status_filesystem` | `gr.idg.status_filesystem` |
| `idg_status_memory` | `gr.idg.status_memory` |
| `idg_status_raidphysicaldrive` | `gr.idg.status_raidphysicaldrive` |
| `idg_status_systemusage` | `gr.idg.status_systemusage` |
| `idg_status_tcpsummary` | `gr.idg.status_tcpsummary` |
| `idg_status_transactionrate` | `gr.idg.status_transactionrate` |
| `idg_status_transactiontimes` | `gr.idg.status_transactiontimes` |
| `idg_stylesheetcache_flush` | `gr.idg.stylesheetcache_flush` |
| `idg_stylesheetcache_summary` | `gr.idg.stylesheetcache_summary` |
| `idg_systemsettings` | `gr.idg.systemsettings` |
| `idg_tcpconnectiontest` | `gr.idg.tcpconnectiontest` |
| `idg_traceroute` | `gr.idg.traceroute` |
| `idg_wsgateway_config` | `gr.idg.wsgateway_config` |
| `idg_wsgateway_operations_status` | `gr.idg.wsgateway_operations_status` |
| `idg_wsgateway_wsdl_refresh` | `gr.idg.wsgateway_wsdl_refresh` |
| `idg_wsgateway_wsdl_status` | `gr.idg.wsgateway_wsdl_status` |
| `idg_wsrr_savedsearchsubscription_status` | `gr.idg.wsrr_savedsearchsubscription_status` |
| `idg_wsrr_savedsearchsubscription_sync` | `gr.idg.wsrr_savedsearchsubscription_sync` |

`gr.idg.status`, `gr.idg.action` and `gr.idg.mgmt_info` are new. They have no `idg_*` name.

`gr.idg.crypto_key` and `gr.idg.crypto_certificate` manage each class on its own. `state: detail` on a certificate posts `ViewCertificateDetails` and returns the record without key material. `state: retarget` changes `Filename` on an existing object and sends back the rest of the document it read. It does not create the object, the file or the alias. `idg_crypto_object` still redirects to `gr.idg.crypto_object`.
