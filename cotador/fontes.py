# -*- coding: utf-8 -*-
"""Lê cada cotação do jeito que ela chega (texto, PDF ou planilha) e devolve texto puro para o Claude."""
import pathlib


def ler(caminho: pathlib.Path) -> str:
    ext = caminho.suffix.lower()
    if ext in (".txt", ".eml", ".md"):
        return caminho.read_text(encoding="utf-8")
    if ext == ".pdf":
        import pymupdf
        with pymupdf.open(caminho) as doc:
            return "\n".join(p.get_text() for p in doc)
    if ext == ".xlsx":
        from openpyxl import load_workbook
        linhas = []
        for ws in load_workbook(caminho, data_only=True).worksheets:
            for row in ws.iter_rows(values_only=True):
                celulas = ["" if v is None else str(v) for v in row]
                if any(celulas):
                    linhas.append("\t".join(celulas).rstrip())
        return "\n".join(linhas)
    raise ValueError(f"Formato não suportado: {caminho.name}")
