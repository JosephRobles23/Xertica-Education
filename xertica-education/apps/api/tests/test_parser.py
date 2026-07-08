"""Spec del SimpleParserAdapter (ADR-0008): formatos soportados y rechazo de legacy."""
import asyncio
import io

import pytest

from adapters.parser.simple import SimpleParserAdapter


def _parse(data: bytes, name: str) -> str:
    return asyncio.run(SimpleParserAdapter().parse_document(data, name))


def test_txt_and_md_passthrough():
    assert "hola mundo" in _parse(b"hola mundo", "notas.txt")
    assert "# Titulo" in _parse(b"# Titulo\n\ncuerpo", "doc.md")


def test_legacy_formats_rejected():
    for name in ["viejo.doc", "pres.ppt", "hoja.xls"]:
        with pytest.raises(ValueError):
            _parse(b"x", name)


def test_unsupported_format_rejected():
    with pytest.raises(ValueError):
        _parse(b"x", "imagen.png")


def test_xlsx_parsed_to_markdown():
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append(["Nombre", "Valor"])
    ws.append(["IA", 42])
    buf = io.BytesIO()
    wb.save(buf)

    md = _parse(buf.getvalue(), "hoja.xlsx")
    assert "## Datos" in md
    assert "Nombre | Valor" in md
    assert "IA | 42" in md
