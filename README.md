# SIM Provisioning Studio (PyQt6 + Osmocom pySim)

A user-friendly desktop front end for authorized programmable SIM/USIM/ISIM cards.

## Included in this MVP

- PC/SC reader discovery
- Inserted-card ATR check
- Read-card workflow using `pySim-read.py`
- Guided provisioning form for:
  - card type
  - operator name
  - MCC / MNC
  - ICCID
  - IMSI
  - Ki
  - OPc
  - ADM1
  - ACC
- Client-side validation
- Secret masking / show-hide controls
- Random Ki / OPc generation
- Safe **Dry Run** before writing
- Explicit authorization acknowledgement before actual programming
- Background command execution so the UI does not freeze
- Command/output audit log
- Configurable pySim folder
- PC/SC reader selection

Use only with SIMs you own or are authorized to provision, such as programmable test/lab cards.

## Recommended environment

Python 3.11 or 3.12.

### Linux

```bash
sudo apt update
sudo apt install pcscd pcsc-tools libpcsclite-dev python3-dev git
sudo systemctl enable --now pcscd
```

### Windows

Install the PC/SC/CCID driver supplied by the reader vendor. Most USB CCID readers work through the Windows Smart Card service.

## Install pySim

```bash
git clone https://gitea.osmocom.org/sim-card/pysim.git
cd pysim
python -m pip install -r requirements.txt
```

The GUI expects the pySim folder to contain:

- `pySim-read.py`
- `pySim-prog.py`
- `pySim-shell.py`

## Install this GUI

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Workflow

1. Open **Settings** and select the cloned pySim directory.
2. Open **Reader** and click **Refresh Readers**.
3. Select the PC/SC reader and insert a programmable SIM.
4. Click **Check Card** to confirm the ATR.
5. Click **Read SIM**.
6. Open **Provision SIM**.
7. Fill provisioning values.
8. Click **Validate**.
9. Click **Dry Run**.
10. Review output.
11. Tick the authorization confirmation.
12. Click **Program SIM**.

## Important ADM warning

A wrong ADM1 can permanently lock administrative access on some programmable cards after a small number of failed attempts. Verify the ADM value from the card supplier before programming.

## Packaging

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "SIM Provisioning Studio" app.py
```

## Architecture

```text
PyQt6 UI
  |
  +-- PC/SC reader discovery (pyscard)
  |
  +-- pySim service
        |
        +-- pySim-read.py
        +-- pySim-prog.py
        +-- pySim-shell.py (future advanced browser/editor)
```

## Recommended production additions

- CSV batch provisioning wizard
- profile templates
- encrypted local secret vault
- inventory database
- QR/label printing
- CSV import/export
- core-network subscriber export
- role-based access
- post-program read-back verification
- configurable Ki/OPc redaction
- pySim-shell JSON integration for advanced EF browsing
