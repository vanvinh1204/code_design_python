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


# Các ca giải mã PJL chuyển từ script ví dụ examples/test_printer_pcl.py
@pytest.mark.parametrize(
    "raw, is_online, is_ready, display, code",
    [
        ('@PJL INFO STATUS\r\nCODE=10001\r\nDISPLAY="00 READY"\r\nONLINE=TRUE\r\n\x0c', True, True, "00 READY", 10001),
        ('@PJL INFO STATUS\r\nCODE=11003\r\nDISPLAY="Paper Jam"\r\nONLINE=TRUE\r\n\x0c', True, False, "Paper Jam", 11003),
        ('@PJL INFO STATUS\r\nCODE=11004\r\nDISPLAY="Load Tray 1"\r\nONLINE=TRUE\r\n\x0c', True, False, "Load Tray 1", 11004),
        ('@PJL INFO STATUS\r\nCODE=10002\r\nDISPLAY="Door Open"\r\nONLINE=FALSE\r\n\x0c', False, False, "Door Open", 10002),
    ],
    ids=["ready", "paper_jam", "load_tray", "door_open"],
)
def test_pjl_probe_parses_status_response(raw, is_online, is_ready, display, code):
    status = PJLStatusProbe().parse_response(raw)

    assert status.is_online is is_online
    assert status.is_ready is is_ready
    assert status.display == display
    assert status.code == code
    assert status.raw == raw


@pytest.mark.parametrize(
    "raw, is_ready",
    [("Ready", True), ("Paper Jam", False), ("Load Tray 1", False)],
)
def test_pjl_probe_parses_plain_text_response(raw, is_ready):
    assert PJLStatusProbe().parse_response(raw).is_ready is is_ready


def test_pjl_probe_empty_response_is_unknown():
    status = PJLStatusProbe().parse_response("")

    assert status.is_online is False
    assert status.is_ready is False
    assert status.display == "Unknown"


def test_printer_status_from_raw_is_deprecated_alias_of_probe():
    raw = '@PJL INFO STATUS\r\nCODE=11003\r\nDISPLAY="Paper Jam"\r\nONLINE=TRUE\r\n\x0c'

    with pytest.warns(DeprecationWarning):
        status = PrinterStatus.from_raw(raw)

    assert status == PJLStatusProbe().parse_response(raw)


def test_get_status_does_not_emit_deprecation_warning():
    simulated_pjl = '@PJL INFO STATUS\r\nCODE=10001\r\nDISPLAY="00 READY"\r\nONLINE=TRUE\r\n\x0c'
    printer = RawSocketPrinter(host="192.168.1.107", transport=FakeSocketTransport(simulated_query_response=simulated_pjl))

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        status = printer.get_status()

    assert status.is_ready is True


def test_printer_status_import_from_pcl_module_still_resolves():
    from core_kit.devices.printer_pcl import PrinterStatus as PclPrinterStatus

    assert PclPrinterStatus is PrinterStatus


def test_get_status_reports_printer_offline_when_unreachable():
    printer = RawSocketPrinter(host="192.168.1.108", transport=FakeSocketTransport(should_fail=True))

    # Không kết nối được máy in: get_status() không ném lỗi mà trả về trạng thái Printer Offline
    status = printer.get_status()

    assert status.is_online is False
    assert status.is_ready is False
    assert status.display != ""


def test_send_verify_ready_transmits_nothing_when_printer_offline():
    transport = FakeSocketTransport(should_fail=True)
    printer = RawSocketPrinter(host="192.168.1.109", transport=transport)

    success = printer.send(b"IMPORTANT_LABEL", verify_ready=True)

    assert success is False
    assert len(transport.sent_payloads) == 0


def test_printer_connection_error_exported_from_devices_package():
    from core_kit.devices import PrinterConnectionError

    with pytest.raises(PrinterConnectionError):
        FakeSocketTransport(should_fail=True).query("192.168.1.110", 9100, b"", 1.0)
