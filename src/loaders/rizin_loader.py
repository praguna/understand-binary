"""Rizin-based binary loader using rzpipe."""

from __future__ import annotations

import json
from typing import Any

import rzpipe

from src.loaders.base import BinaryLoader, BinaryContext, FunctionInfo


class RizinLoader(BinaryLoader):
    name = "rizin"
    supported_formats = ["ELF", "PE", "Mach-O", "DEX"]

    def __init__(self) -> None:
        self._rz: rzpipe.open | None = None
        self._path: str = ""

    def load(self, path: str) -> BinaryContext:
        self._path = path
        self._rz = rzpipe.open(path, flags=["-2"])  # -2 suppresses stderr noise
        self._rz.cmd("aaa")  # full analysis

        info = self._parse_json(self._rz.cmd("ij"))
        arch = info.get("bin", {}).get("arch", "unknown")
        bin_format = info.get("bin", {}).get("bintype", "unknown").upper()
        if bin_format == "ELF64" or bin_format == "ELF32":
            bin_format = "ELF"
        elif "PE" in bin_format:
            bin_format = "PE"
        elif "MACH" in bin_format:
            bin_format = "Mach-O"

        functions = self._load_functions()
        strings = self._load_strings()
        imports = self._load_imports()
        sections = self._load_sections()
        call_graph = self._build_call_graph(functions)

        ctx = BinaryContext(
            binary_name=path.split("/")[-1].split("\\")[-1],
            architecture=arch,
            format=bin_format,
            sections=sections,
            functions=functions,
            strings=strings,
            imports=imports,
            call_graph=call_graph,
            _loader=self,
        )
        return ctx

    def decompile(self, address: str) -> str:
        if self._rz is None:
            return ""
        self._rz.cmd(f"s {address}")
        result = self._rz.cmd("pdc")
        if not result or "Cannot" in result:
            result = self._rz.cmd("pdf")
        return result or ""

    def _load_functions(self) -> list[FunctionInfo]:
        data = self._parse_json(self._rz.cmd("aflj"))
        if not isinstance(data, list):
            return []
        return [
            FunctionInfo(
                address=hex(f.get("offset", 0)),
                name=f.get("name", f"fcn_{f.get('offset', 0):08x}"),
                size=f.get("size", 0),
            )
            for f in data
        ]

    def _load_strings(self) -> list[str]:
        data = self._parse_json(self._rz.cmd("izj"))
        if not isinstance(data, list):
            return []
        return [s.get("string", "") for s in data if s.get("string")]

    def _load_imports(self) -> list[str]:
        data = self._parse_json(self._rz.cmd("iij"))
        if not isinstance(data, list):
            return []
        return [i.get("name", "") for i in data if i.get("name")]

    def _load_sections(self) -> list[dict[str, Any]]:
        data = self._parse_json(self._rz.cmd("iSj"))
        if not isinstance(data, list):
            return []
        return [
            {"name": s.get("name", ""), "size": s.get("size", 0), "perm": s.get("perm", "")}
            for s in data
        ]

    def _build_call_graph(self, functions: list[FunctionInfo]) -> dict[str, list[str]]:
        call_graph: dict[str, list[str]] = {}
        known_addrs = {fn.address for fn in functions}

        for fn in functions:
            self._rz.cmd(f"s {fn.address}")
            instrs = self._parse_json(self._rz.cmd("pdrj"))
            if not isinstance(instrs, list):
                continue
            callees = []
            for instr in instrs:
                if instr.get("type") == "call" and "jump" in instr:
                    callee_addr = hex(instr["jump"])
                    if callee_addr in known_addrs:
                        callees.append(callee_addr)
            if callees:
                call_graph[fn.address] = list(set(callees))
        return call_graph

    def _parse_json(self, text: str) -> Any:
        if not text or not text.strip():
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []
