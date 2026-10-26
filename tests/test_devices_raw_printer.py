"""Kiểm thử module RAW Socket Printing: RawSocketPrinter, PJLStatusProbe và FakeSocketTransport."""

import warnings
import pytest
from core_kit.devices.printer_raw import (
    RawSocketPrinter,
    PJLStatusProbe,
    FakeSocketTransport,
    PrinterStatus,
)
from core_kit.devices.printer_pcl import PCLNetworkPrinter
from core_kit.devices.printer_tspl import TSPLNetworkPrinter


def test_fake_socket_transport_send_bytes():
    transport = FakeSocketTransport()
    printer = RawSocketPrinter(host="192.168.1.100", port=9100, transport=transport)

    test_payload = b"\x1b%-12345X@PJL\r\nPRINT DATA\r\n\x1b%-12345X"
    success = printer.send(test_payload)

    assert success is True
    assert len(transport.sent_payloads) == 1
    assert transport.sent_payloads[0] == test_payload
    assert transport.last_destination == ("192.168.1.100", 9100)


def test_raw_socket_printer_send_string_auto_encodes():
    transport = FakeSocketTransport()
    printer = RawSocketPrinter(host="192.168.1.101", port=9100, transport=transport)

    tspl_command = "SIZE 80 mm, 50 mm\r\nPRINT 1\r\n"
    success = printer.send(tspl_command, encoding="utf-8")

    assert success is True
    assert len(transport.sent_payloads) == 1
    assert transport.sent_payloads[0] == tspl_command.encode("utf-8")


def test_raw_socket_printer_transport_failure():
    transport = FakeSocketTransport(should_fail=True)
    printer = RawSocketPrinter(host="192.168.1.102", port=9100, transport=transport)

    success = printer.send(b"TEST_PAYLOAD")
    assert success is False
    assert len(transport.sent_payloads) == 0


def test_raw_socket_printer_status_probe():
    simulated_pjl = '@PJL INFO STATUS\r\nCODE=10001\r\nDISPLAY="00 READY"\r\nONLINE=TRUE\r\n\x0c'
    transport = FakeSocketTransport(simulated_query_response=simulated_pjl)
    printer = RawSocketPrinter(host="192.168.1.103", transport=transport)

    status = printer.get_status(probe=PJLStatusProbe())

    assert isinstance(status, PrinterStatus)
    assert status.is_online is True
    assert status.is_ready is True
    assert status.display == "00 READY"
    assert status.code == 10001


def test_raw_socket_printer_verify_ready_aborts_when_not_ready():
    simulated_jam = '@PJL INFO STATUS\r\nCODE=30002\r\nDISPLAY="PAPER JAM"\r\nONLINE=TRUE\r\n\x0c'
    transport = FakeSocketTransport(simulated_query_response=simulated_jam)
    printer = RawSocketPrinter(host="192.168.1.104", transport=transport)

    # Khi verify_ready=True và máy in báo kẹt giấy, không được gửi payload
    success = printer.send(b"IMPORTANT_LABEL", verify_ready=True)

    assert success is False
    assert len(transport.sent_payloads) == 0


def test_deprecated_pcl_network_printer_compatibility():
    transport = FakeSocketTransport()
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        printer = PCLNetworkPrinter(host="192.168.1.105", transport=transport)

        # Kiểm tra có phát cảnh báo DeprecationWarning
        assert any(issubclass(w.category, DeprecationWarning) for w in recorded_warnings)

    success = printer.send(b"\x1bPCL_DATA")
    assert success is True
    assert len(transport.sent_payloads) == 1
    assert transport.sent_payloads[0] == b"\x1bPCL_DATA"


def test_deprecated_tspl_network_printer_compatibility():
    transport = FakeSocketTransport()
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        printer = TSPLNetworkPrinter(host="192.168.1.106", transport=transport)

        # Kiểm tra có phát cảnh báo DeprecationWarning
        assert any(issubclass(w.category, DeprecationWarning) for w in recorded_warnings)

    success = printer.send_raw("CLS\r\nPRINT 1\r\n")
    assert success is True
    assert len(transport.sent_payloads) == 1
    assert transport.sent_payloads[0] == b"CLS\r\nPRINT 1\r\n"
