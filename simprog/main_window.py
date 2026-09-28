from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QThread
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QComboBox, QPlainTextEdit, QFormLayout,
    QLineEdit, QMessageBox, QFileDialog, QCheckBox, QGridLayout,
    QGroupBox, QSizePolicy
)

from .services.pcsc_service import PcscService
from .services.pysim_service import PySimService, RunResult
from .validators import validate_profile
from .workers import CommandWorker

APP_TITLE = "SIM Provisioning Studio"

class SecretField(QWidget):
    def __init__(self, placeholder=""):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.toggle = QPushButton("Show")
        self.toggle.setFixedWidth(72)
        self.toggle.clicked.connect(self._toggle)

        row.addWidget(self.edit)
        row.addWidget(self.toggle)

    def _toggle(self):
        hidden = self.edit.echoMode() == QLineEdit.EchoMode.Password
        self.edit.setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
        self.toggle.setText("Hide" if hidden else "Show")

    def text(self):
        return self.edit.text()

    def setText(self, value: str):
        self.edit.setText(value)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)

        self.settings = QSettings("LocalLab", "SIMProvisioningStudio")
        self.pcsc = PcscService()
        self._threads = []

        self._build_ui()
        self._apply_style()
        self.load_settings()
        self.refresh_readers()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)

        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 24)

        title = QLabel("SIM\nProvisioning")
        title.setObjectName("brand")
        side.addWidget(title)
        side.addSpacing(24)

        self.nav_buttons = []
        for idx, text in enumerate(["Dashboard", "Reader", "Provision SIM", "Logs", "Settings"]):
            btn = QPushButton(text)
            btn.setObjectName("nav")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self.show_page(i))
            side.addWidget(btn)
            self.nav_buttons.append(btn)

        side.addStretch()
        foot = QLabel("Authorized lab/test SIMs only")
        foot.setWordWrap(True)
        foot.setObjectName("muted")
        side.addWidget(foot)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._dashboard_page())
        self.stack.addWidget(self._reader_page())
        self.stack.addWidget(self._provision_page())
        self.stack.addWidget(self._logs_page())
        self.stack.addWidget(self._settings_page())

        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.show_page(0)

    def _page_shell(self, title, subtitle):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(34, 28, 34, 28)

        h = QLabel(title)
        h.setObjectName("pageTitle")
        s = QLabel(subtitle)
        s.setObjectName("muted")

        v.addWidget(h)
        v.addWidget(s)
        v.addSpacing(18)
        return page, v

    def _dashboard_page(self):
        page, v = self._page_shell(
            "Dashboard",
            "Reader status, safe provisioning workflow, and pySim integration at a glance."
        )

        grid = QGridLayout()
        self.reader_card = self._status_card("Reader", "Not checked")
        self.sim_card = self._status_card("SIM card", "Not checked")
        self.pysim_card = self._status_card("pySim", "Not configured")
        self.mode_card = self._status_card("Safety", "Dry-run first")

        grid.addWidget(self.reader_card, 0, 0)
        grid.addWidget(self.sim_card, 0, 1)
        grid.addWidget(self.pysim_card, 1, 0)
        grid.addWidget(self.mode_card, 1, 1)
        v.addLayout(grid)

        workflow = QGroupBox("Recommended workflow")
        w = QVBoxLayout(workflow)
        for text in [
            "1. Configure the pySim repository folder in Settings.",
            "2. Select a PC/SC reader and confirm the inserted card.",
            "3. Read the SIM and review current identifiers.",
            "4. Fill provisioning values and validate them.",
            "5. Run Dry Run, review output, then program only an authorized card.",
        ]:
            w.addWidget(QLabel(text))

        v.addWidget(workflow)
        v.addStretch()
        return page

    def _status_card(self, title, value):
        box = QFrame()
        box.setObjectName("card")
        box.setMinimumHeight(125)

        lay = QVBoxLayout(box)
        t = QLabel(title)
        t.setObjectName("muted")
        val = QLabel(value)
        val.setObjectName("cardValue")
        val.setWordWrap(True)

        lay.addWidget(t)
        lay.addWidget(val)
        lay.addStretch()

        box.value_label = val
        return box

    def _reader_page(self):
        page, v = self._page_shell(
            "Reader",
            "Detect a PC/SC smart-card reader, check ATR, and read accessible SIM data."
        )

        row = QHBoxLayout()
        self.reader_combo = QComboBox()
        self.reader_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        refresh = QPushButton("Refresh Readers")
        refresh.clicked.connect(self.refresh_readers)

        row.addWidget(self.reader_combo, 1)
        row.addWidget(refresh)
        v.addLayout(row)

        row2 = QHBoxLayout()
        check = QPushButton("Check Card")
        check.clicked.connect(self.check_card)

        read = QPushButton("Read SIM")
        read.setObjectName("primary")
        read.clicked.connect(self.read_sim)

        row2.addWidget(check)
        row2.addWidget(read)
        row2.addStretch()
        v.addLayout(row2)

        self.atr_label = QLabel("ATR: —")
        self.atr_label.setObjectName("mono")
        v.addWidget(self.atr_label)

        self.read_output = QPlainTextEdit()
        self.read_output.setReadOnly(True)
        self.read_output.setPlaceholderText("Readable SIM information will appear here.")
        v.addWidget(self.read_output, 1)
        return page

    def _provision_page(self):
        page, v = self._page_shell(
            "Provision SIM",
            "Provision common programmable SIM parameters through pySim-prog."
        )

        group = QGroupBox("Card and network profile")
        form = QFormLayout(group)

        self.card_type = QLineEdit("auto")
        self.card_type.setPlaceholderText("auto or supplier card type")
        self.operator_name = QLineEdit("Lab")
        self.mcc = QLineEdit()
        self.mnc = QLineEdit()
        self.iccid = QLineEdit()
        self.imsi = QLineEdit()
        self.ki = SecretField("32 hex characters")
        self.opc = SecretField("32 hex characters")
        self.adm = SecretField("Supplier-provided ADM1")
        self.acc = QLineEdit()
        self.acc.setPlaceholderText("Optional, e.g. 0001")

        form.addRow("Card type", self.card_type)
        form.addRow("Operator name", self.operator_name)
        form.addRow("MCC", self.mcc)
        form.addRow("MNC", self.mnc)
        form.addRow("ICCID", self.iccid)
        form.addRow("IMSI", self.imsi)
        form.addRow("Ki", self.ki)
        form.addRow("OPc", self.opc)
        form.addRow("ADM1", self.adm)
        form.addRow("ACC", self.acc)

        v.addWidget(group)

        secret_row = QHBoxLayout()
        gen_ki = QPushButton("Generate Ki")
        gen_ki.clicked.connect(lambda: self.ki.setText(secrets.token_hex(16)))
        gen_opc = QPushButton("Generate OPc")
        gen_opc.clicked.connect(lambda: self.opc.setText(secrets.token_hex(16)))

        secret_row.addWidget(gen_ki)
        secret_row.addWidget(gen_opc)
        secret_row.addStretch()
        v.addLayout(secret_row)

        self.auth_check = QCheckBox(
            "I confirm this is a programmable SIM I own or am authorized to provision."
        )
        v.addWidget(self.auth_check)

        actions = QHBoxLayout()

        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self.validate_form)

        dry_btn = QPushButton("Dry Run")
        dry_btn.clicked.connect(lambda: self.program(dry_run=True))

        prog_btn = QPushButton("Program SIM")
        prog_btn.setObjectName("danger")
        prog_btn.clicked.connect(lambda: self.program(dry_run=False))

        actions.addWidget(validate_btn)
        actions.addWidget(dry_btn)
        actions.addStretch()
        actions.addWidget(prog_btn)
        v.addLayout(actions)

        self.provision_output = QPlainTextEdit()
        self.provision_output.setReadOnly(True)
        self.provision_output.setPlaceholderText("Validation, dry-run, and provisioning output.")
        v.addWidget(self.provision_output, 1)

        return page

    def _logs_page(self):
        page, v = self._page_shell(
            "Logs",
            "Local activity log. Authentication secrets are redacted from displayed commands."
        )

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        v.addWidget(self.log_output, 1)

        clear = QPushButton("Clear Log")
        clear.clicked.connect(self.log_output.clear)
        v.addWidget(clear, alignment=Qt.AlignmentFlag.AlignRight)

        return page

    def _settings_page(self):
        page, v = self._page_shell(
            "Settings",
            "Point the application at your tested Osmocom pySim checkout."
        )

        group = QGroupBox("pySim")
        form = QFormLayout(group)

        path_row = QWidget()
        h = QHBoxLayout(path_row)
        h.setContentsMargins(0, 0, 0, 0)

        self.pysim_path = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_pysim)

        h.addWidget(self.pysim_path, 1)
        h.addWidget(browse)

        form.addRow("pySim directory", path_row)
        v.addWidget(group)

        save = QPushButton("Save Settings")
        save.setObjectName("primary")
        save.clicked.connect(self.save_settings)

        v.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        v.addStretch()
        return page

    def _apply_style(self):
        self.setStyleSheet("""
        QMainWindow, QWidget {
            background: #0f141b;
            color: #e9eef6;
            font-size: 14px;
        }
        #sidebar {
            background: #111923;
            border-right: 1px solid #253142;
        }
        #brand {
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }
        #pageTitle {
            font-size: 28px;
            font-weight: 700;
        }
        #muted {
            color: #94a3b8;
        }
        #card {
            background: #151f2b;
            border: 1px solid #263445;
            border-radius: 12px;
        }
        #cardValue {
            font-size: 18px;
            font-weight: 600;
        }
        QGroupBox {
            border: 1px solid #29384a;
            border-radius: 10px;
            margin-top: 12px;
            padding: 14px;
            font-weight: 600;
            background: #121a24;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        QLineEdit, QComboBox, QPlainTextEdit {
            background: #0b1118;
            border: 1px solid #314156;
            border-radius: 7px;
            padding: 8px;
            selection-background-color: #2563eb;
        }
        QPlainTextEdit {
            font-family: Consolas, "SFMono-Regular", monospace;
        }
        QPushButton {
            background: #1b2735;
            border: 1px solid #34465c;
            border-radius: 7px;
            padding: 8px 13px;
        }
        QPushButton:hover {
            background: #243346;
        }
        QPushButton#primary {
            background: #2563eb;
            border-color: #2563eb;
            font-weight: 600;
        }
        QPushButton#danger {
            background: #991b1b;
            border-color: #b91c1c;
            font-weight: 600;
        }
        QPushButton#nav {
            text-align: left;
            border: none;
            background: transparent;
            padding: 11px 12px;
            color: #b7c4d4;
        }
        QPushButton#nav:checked {
            background: #1c2a3a;
            color: white;
        }
        #mono {
            font-family: Consolas, "SFMono-Regular", monospace;
            color: #b9c7d9;
        }
        QCheckBox {
            spacing: 8px;
        }
        """)

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def browse_pysim(self):
        path = QFileDialog.getExistingDirectory(self, "Select pySim directory")
        if path:
            self.pysim_path.setText(path)

    def load_settings(self):
        path = self.settings.value("pysim_dir", "", str)
        self.pysim_path.setText(path)
        self._update_pysim_status()

    def save_settings(self):
        self.settings.setValue("pysim_dir", self.pysim_path.text().strip())
        self._update_pysim_status()
        QMessageBox.information(self, "Settings", "Settings saved.")

    def _update_pysim_status(self):
        text = self.pysim_path.text().strip()
        p = Path(text) if text else None
        ok = bool(p and (p / "pySim-prog.py").exists() and (p / "pySim-read.py").exists())
        self.pysim_card.value_label.setText("Ready" if ok else "Not configured / scripts missing")

    def refresh_readers(self):
        try:
            rs = self.pcsc.list_readers()
        except Exception as exc:
            rs = []
            self._log(f"Reader discovery error: {exc}")

        self.reader_combo.clear()
        self.reader_combo.addItems(rs)
        self.reader_card.value_label.setText(
            f"{len(rs)} reader(s) found" if rs else "No reader found"
        )

    def check_card(self):
        idx = self.reader_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Reader", "No PC/SC reader selected.")
            return

        status = self.pcsc.check_card(idx)

        if status.connected:
            self.atr_label.setText(f"ATR: {status.atr}")
            self.sim_card.value_label.setText("Card detected")
            self._log(f"Card detected on {status.reader}; ATR={status.atr}")
        else:
            self.atr_label.setText("ATR: —")
            self.sim_card.value_label.setText("No card / connection failed")
            QMessageBox.warning(self, "Card", status.message)
            self._log(status.message)

    def read_sim(self):
        idx = self.reader_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Read SIM", "Select a reader first.")
            return

        self.read_output.setPlainText("Reading SIM…")
        svc = PySimService(self.pysim_path.text().strip())
        self._run_background(lambda: svc.read_card(idx), self._on_read_result)

    def _on_read_result(self, result: RunResult):
        self.read_output.setPlainText(self._format_result(result))
        self._log_result("READ", result)

    def profile(self):
        return {
            "card_type": self.card_type.text(),
            "operator_name": self.operator_name.text(),
            "mcc": self.mcc.text(),
            "mnc": self.mnc.text(),
            "iccid": self.iccid.text(),
            "imsi": self.imsi.text(),
            "ki": self.ki.text(),
            "opc": self.opc.text(),
            "adm": self.adm.text(),
            "acc": self.acc.text(),
        }

    def validate_form(self):
        errors = validate_profile(self.profile())
        if errors:
            self.provision_output.setPlainText(
                "Validation failed:\n\n- " + "\n- ".join(errors)
            )
            return False

        self.provision_output.setPlainText("Validation passed.")
        return True

    def program(self, dry_run: bool):
        profile = self.profile()
        errors = validate_profile(profile)

        if errors:
            self.provision_output.setPlainText(
                "Validation failed:\n\n- " + "\n- ".join(errors)
            )
            return

        idx = self.reader_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Provision", "Select a PC/SC reader first.")
            return

        if not dry_run:
            if not self.auth_check.isChecked():
                QMessageBox.warning(
                    self,
                    "Authorization required",
                    "Confirm that you own or are authorized to provision this programmable SIM."
                )
                return

            answer = QMessageBox.warning(
                self,
                "Program SIM",
                "This will write provisioning data to the card.\n\n"
                "A wrong ADM1 can lock administrative access on some cards.\n"
                "Verify the ADM1 and all network parameters before continuing.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        self.provision_output.setPlainText(
            "Running dry-run…" if dry_run else "Programming SIM…"
        )

        svc = PySimService(self.pysim_path.text().strip())
        self._run_background(
            lambda: svc.provision(idx, profile, dry_run=dry_run),
            lambda result: self._on_program_result(result, dry_run)
        )

    def _on_program_result(self, result: RunResult, dry_run: bool):
        self.provision_output.setPlainText(self._format_result(result))
        self._log_result("DRY-RUN" if dry_run else "PROGRAM", result)

        if result.ok:
            QMessageBox.information(
                self,
                "Dry Run Complete" if dry_run else "Programming Complete",
                "pySim completed successfully."
            )
        else:
            QMessageBox.warning(
                self,
                "pySim Error",
                f"pySim exited with code {result.exit_code}. Review the output."
            )

    def _run_background(self, fn, on_success):
        thread = QThread(self)
        worker = CommandWorker(fn)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def finish(result):
            try:
                on_success(result)
            finally:
                thread.quit()

        def fail(message):
            self._log(f"ERROR: {message}")
            QMessageBox.critical(self, "Error", message)
            thread.quit()

        worker.finished.connect(finish)
        worker.failed.connect(fail)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            lambda: self._threads.remove(thread) if thread in self._threads else None
        )

        self._threads.append(thread)
        thread.start()

    @staticmethod
    def _format_result(result: RunResult):
        return (
            f"Command:\n{result.command_display}\n\n"
            f"Exit code: {result.exit_code}\n\n"
            f"STDOUT:\n{result.stdout or '(none)'}\n\n"
            f"STDERR:\n{result.stderr or '(none)'}"
        )

    def _log_result(self, action, result: RunResult):
        self._log(
            f"{action} | exit={result.exit_code}\n"
            f"{result.command_display}\n"
            f"{result.stdout[-3000:]}\n"
            f"{result.stderr[-3000:]}"
        )

    def _log(self, message):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self, "log_output"):
            self.log_output.appendPlainText(f"[{stamp}] {message}\n")
