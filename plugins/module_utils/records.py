# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

"""Named records for status providers. Positional lists are not returned."""

from ansible_collections.gr.idg.plugins.module_utils.client import as_list, camel_to_snake


def _windows(record):
    return {
        "ten_seconds": record.get("tenSeconds"),
        "one_minute": record.get("oneMinute"),
        "ten_minutes": record.get("tenMinutes"),
        "one_hour": record.get("oneHour"),
        "one_day": record.get("oneDay"),
    }


def is_yes(value):
    return str(value).lower().strip() == "yes"


def _percent(free, total):
    try:
        total = float(total)
        free = float(free)
    except (TypeError, ValueError):
        return None
    if not total:
        return None
    return float("{0:.2f}".format((free / total) * 100))


def cpu(record):
    return _windows(record or {})


def connections(record):
    return _windows(record or {})


def memory(record):
    record = record or {}
    return {
        "usage": record.get("Usage"),
        "used": record.get("UsedMemory"),
        "free": record.get("FreeMemory"),
        "hold": record.get("HoldMemory"),
        "installed": record.get("InstalledMemory"),
        "requested": record.get("ReqMemory"),
        "reserved": record.get("ReservedMemory"),
        "total": record.get("TotalMemory"),
    }


def filesystem(record):
    record = record or {}
    stores = {}
    for name, total_key, free_key in (
        ("encrypted", "TotalEncrypted", "FreeEncrypted"),
        ("internal", "TotalInternal", "FreeInternal"),
        ("temporary", "TotalTemporary", "FreeTemporary"),
    ):
        total = record.get(total_key)
        free = record.get(free_key)
        stores[name] = {
            "total": total,
            "free": free,
            "free_percent": _percent(free, total) if free is not None and total else None,
        }
    return stores


def system_usage(record):
    record = record or {}
    return {
        "load": record.get("Load"),
        "work_list": record.get("WorkList"),
        "interval": record.get("Interval"),
    }


def tcp_summary(record):
    record = record or {}
    keys = (
        "listen",
        "established",
        "close_wait",
        "closed",
        "closing",
        "fin_wait_1",
        "fin_wait_2",
        "last_ack",
        "syn_received",
        "syn_sent",
        "time_wait",
    )
    return {key: record.get(key) for key in keys}


def datetime_status(current, extended=None):
    current = current or {}
    extended = extended or {}
    return {
        "time": current.get("time"),
        "timezone": {
            "name": current.get("timezone"),
            "spec": current.get("tzspec"),
        },
        "uptime": {
            "since_boot": extended.get("bootuptime3") or current.get("bootuptime2"),
            "since_reload": extended.get("uptime3") or current.get("uptime2"),
        },
    }


def ethernet(rows):
    interfaces = {}
    for row in as_list(rows):
        if not isinstance(row, dict):
            continue
        name = row.get("Name")
        interfaces[name] = {
            "collisions": row.get("Collisions2"),
            "flow_control_negotiation": row.get("FlowControlNegotiation"),
            "flow_control_status": row.get("FlowControlStatus"),
            "ip": row.get("IP") or None,
            "mac_address": row.get("MACAddress"),
            "mtu": row.get("MTU"),
            "mode": row.get("Mode"),
            "negotiate": row.get("Negotiate"),
            "rx_drops": row.get("RxDrops2"),
            "rx_errors": row.get("RxErrors2"),
            "rx_hc_bytes": row.get("RxHCBytes"),
            "rx_hc_packets": row.get("RxHCPackets"),
            "status": row.get("Status"),
            "tx_drops": row.get("TxDrops2"),
            "tx_errors": row.get("TxErrors2"),
            "tx_hc_bytes": row.get("TxHCBytes"),
            "tx_hc_packets": row.get("TxHCPackets"),
        }
    return interfaces


def raid(rows):
    drives = []
    for row in as_list(rows):
        if not isinstance(row, dict):
            continue
        temperature = row.get("Temperature")
        if isinstance(temperature, str):
            temperature = temperature.replace(" ", "")
        drives.append({
            "position": row.get("Position"),
            "array_id": row.get("ArrayID"),
            "coerced_size": row.get("CoercedSize"),
            "controller_id": row.get("ControllerID"),
            "device_id": row.get("DeviceID"),
            "failure": is_yes(row.get("Failure")),
            "interface_speed": row.get("InterfaceSpeed"),
            "interface_type": row.get("InterfaceType"),
            "logical_drive_id": row.get("LogicalDriveID"),
            "logical_drive_name": row.get("LogicalDriveName"),
            "product_id": row.get("ProductID"),
            "progress_percent": row.get("ProgressPercent"),
            "raw_size": row.get("RawSize"),
            "revision": row.get("Revision"),
            "sas_address": row.get("SASaddress"),
            "specific_info": row.get("SpecificInfo"),
            "state": row.get("State"),
            "temperature": temperature,
            "vendor_id": row.get("VendorID"),
        })
    return drives


def _sensor_rows(rows):
    return [row for row in as_list(rows) if isinstance(row, dict)]


def temperature(rows):
    result = []
    for sensor in _sensor_rows(rows):
        upper_non = sensor.get("UpperNonRecoverableThreshold")
        if str(upper_non).strip() == "":
            upper_non = sensor.get("UpperNonCriticalThreshold")
        result.append({
            "name": sensor.get("Name"),
            "value": sensor.get("Value"),
            "status": sensor.get("ReadingStatus"),
            "upper_threshold": sensor.get("UpperCriticalThreshold"),
            "upper_noncritical_threshold": sensor.get("UpperNonCriticalThreshold"),
            "upper_nonrecoverable_threshold": upper_non,
        })
    return result


def voltage(rows):
    return [
        {
            "name": sensor.get("Name"),
            "status": sensor.get("ReadingStatus"),
            "lower_threshold": sensor.get("LowerCriticalThreshold"),
            "upper_threshold": sensor.get("UpperCriticalThreshold"),
            "value": sensor.get("Value"),
        }
        for sensor in _sensor_rows(rows)
    ]


def current(rows):
    return [
        {
            "name": sensor.get("Name"),
            "status": sensor.get("ReadingStatus"),
            "value": sensor.get("Value") == "true",
            "upper_threshold": sensor.get("UpperCriticalThreshold"),
        }
        for sensor in _sensor_rows(rows)
    ]


def power(rows):
    return [
        {"name": sensor.get("Name"), "value": sensor.get("Value")}
        for sensor in _sensor_rows(rows)
    ]


def other(rows):
    return [
        {
            "name": sensor.get("Name"),
            "status": sensor.get("ReadingStatus"),
            "value": sensor.get("Value") == "true",
        }
        for sensor in _sensor_rows(rows)
    ]


def fans(rows):
    result = []
    for sensor in _sensor_rows(rows):
        fan_id = sensor.get("FanID") or ""
        result.append({
            "name": str(fan_id).capitalize().replace("-", " "),
            "speed": sensor.get("FanSpeed"),
            "status": sensor.get("ReadingStatus"),
            "lower_threshold": sensor.get("LowerCriticalThreshold"),
        })
    return result


def wsdl_status(rows):
    mapped = []
    keys = (
        "ID",
        "LastRefresh",
        "Log",
        "PolicyExecution",
        "RefreshInterval",
        "Status",
        "WSDLSourceLocation",
    )
    for item in _sensor_rows(rows):
        row = {}
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            name = camel_to_snake(key)
            row[name] = None if key == "Log" and value == "" else value
        gateway = item.get("WSGateway")
        if isinstance(gateway, dict) and gateway.get("value"):
            row["ws_gateway"] = gateway.get("value")
        mapped.append(row)
    return mapped


def wsrr_subscriptions(rows):
    sync_keys = ("LastRefresh", "Status", "Count", "Method", "RefreshInterval")
    mapped = []
    for item in _sensor_rows(rows):
        row = {"sync": {}}
        for key in ("ServiceVersionCount",) + sync_keys:
            value = item.get(key)
            if value is None:
                continue
            name = camel_to_snake(key)
            if key in sync_keys:
                if name == "count":
                    row["sync"]["wsdls_count"] = value
                else:
                    row["sync"][name] = value
            else:
                row[name] = value
        subscription = item.get("Subscription")
        if isinstance(subscription, dict) and subscription.get("value"):
            row["name"] = subscription.get("value")
        mapped.append(row)
    return mapped


def active_services(rows):
    services = []
    for item in _sensor_rows(rows):
        services.append({
            "service_name": item.get("ServiceName"),
            "service_class": item.get("ServiceClass"),
            "local_ip": item.get("LocalIP"),
            "local_port": item.get("LocalPort"),
        })
    return services
