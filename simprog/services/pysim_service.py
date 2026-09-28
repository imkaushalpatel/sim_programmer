from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

@dataclass
class RunResult:
    ok: bool
    exit_code: int
    command_display: str
    stdout: str
    stderr: str

class PySimService:
    def __init__(self, pysim_dir: str):
        self.pysim_dir = Path(pysim_dir).expanduser() if pysim_dir else Path()

    def _script(self, name: str) -> Path:
        path = self.pysim_dir / name
        if not path.exists():
            raise FileNotFoundError(
                f"{name} was not found in the configured pySim directory: {self.pysim_dir}"
            )
        return path

    @staticmethod
    def _display_command(args: list[str], sensitive_values: list[str] | None = None) -> str:
        sensitive_values = [x for x in (sensitive_values or []) if x]
        safe = []
        for item in args:
            redacted = item
            for secret in sensitive_values:
                redacted = redacted.replace(secret, "********")
            safe.append(redacted)
        return " ".join(f'"{x}"' if " " in x else x for x in safe)

    def _run(self, args: list[str], sensitive_values=None, timeout=120) -> RunResult:
        proc = subprocess.run(
            args,
            cwd=str(self.pysim_dir),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return RunResult(
            ok=proc.returncode == 0,
            exit_code=proc.returncode,
            command_display=self._display_command(args, sensitive_values),
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )

    def read_card(self, reader_index: int) -> RunResult:
        script = self._script("pySim-read.py")
        args = [sys.executable, str(script), "--pcsc-device", str(reader_index)]
        return self._run(args, timeout=120)

    def provision(self, reader_index: int, profile: dict, dry_run: bool) -> RunResult:
        script = self._script("pySim-prog.py")
        args = [
            sys.executable, str(script),
            "--pcsc-device", str(reader_index),
            "--type", profile["card_type"].strip() or "auto",
            "--name", profile["operator_name"].strip() or "Lab",
            "--mcc", profile["mcc"].strip(),
            "--mnc", profile["mnc"].strip(),
            "--iccid", profile["iccid"].strip(),
            "--imsi", profile["imsi"].strip(),
            "--ki", profile["ki"].strip(),
            "--opc", profile["opc"].strip(),
        ]

        adm = profile.get("adm", "").strip()
        if adm:
            if len(adm) == 16 and all(c in "0123456789abcdefABCDEF" for c in adm):
                args += ["--pin-adm-hex", adm]
            else:
                args += ["--pin-adm", adm]

        acc = profile.get("acc", "").strip()
        if acc:
            args += ["--acc", acc]

        if dry_run:
            args.append("--dry-run")

        secrets = [profile.get("ki", ""), profile.get("opc", ""), adm]
        return self._run(args, sensitive_values=secrets, timeout=180)
