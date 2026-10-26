"""Kiểm thử bộ tạo lệnh in mã vạch / tem nhãn TSPL: TSPLBuilder."""

import pytest
from core_kit.devices import TSPLBuilder


def test_tspl_builder_commands_sequence():
    builder = TSPLBuilder(width_mm=80, height_mm=50)

    builder.text(x=20, y=20, content="CONG TY ABC - TEM XUAT KHO", font="TSS24.BF2", x_multi=1, y_multi=1)
    builder.line(x=20, y=50, width=550, height=2)
    builder.text(x=20, y=60, content='SAN PHAM: "BAN LE"', font="TSS24.BF2", x_multi=1, y_multi=1)
    builder.barcode(x=20, y=100, code="PRD-998877", height=50, readable=1)
    builder.dmatrix(x=380, y=100, content="PRD-998877-LOT01", size=6)
    builder.qrcode(x=450, y=100, content="https://example.com/item", cell_width=4)

    raw_output = builder.print(copies=2)

    assert "SIZE 80 mm, 50 mm" in raw_output
    assert "GAP 3 mm, 0 mm" in raw_output
    assert "DIRECTION 1" in raw_output
    assert "CLS" in raw_output
    assert 'TEXT 20,20,"TSS24.BF2",0,1,1,"CONG TY ABC - TEM XUAT KHO"' in raw_output
    assert "BAR 20,50,550,2" in raw_output
    assert 'TEXT 20,60,"TSS24.BF2",0,1,1,"SAN PHAM: \\"BAN LE\\""' in raw_output
    assert 'BARCODE 20,100,"128",50,1,0,2,2,"PRD-998877"' in raw_output
    assert 'DMATRIX 380,100,6,6,"PRD-998877-LOT01"' in raw_output
    assert 'QRCODE 450,100,H,4,A,0,"https://example.com/item"' in raw_output
    assert "PRINT 2,1\r\n" in raw_output
