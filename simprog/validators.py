import re

HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")
HEX4 = re.compile(r"^[0-9a-fA-F]{4}$")

def validate_profile(p: dict) -> list[str]:
    errors = []

    mcc = p.get("mcc", "").strip()
    mnc = p.get("mnc", "").strip()
    iccid = p.get("iccid", "").strip()
    imsi = p.get("imsi", "").strip()
    ki = p.get("ki", "").strip()
    opc = p.get("opc", "").strip()
    adm = p.get("adm", "").strip()
    acc = p.get("acc", "").strip()

    if not (mcc.isdigit() and len(mcc) == 3):
        errors.append("MCC must be exactly 3 digits.")

    if not (mnc.isdigit() and len(mnc) in (2, 3)):
        errors.append("MNC must be 2 or 3 digits.")

    if not (iccid.isdigit() and len(iccid) in (18, 19, 20)):
        errors.append("ICCID must be 18, 19, or 20 digits.")

    if not (imsi.isdigit() and 6 <= len(imsi) <= 15):
        errors.append("IMSI must contain digits only and be no longer than 15 digits.")

    if not HEX32.fullmatch(ki):
        errors.append("Ki must be 32 hexadecimal characters (128 bits).")

    if not HEX32.fullmatch(opc):
        errors.append("OPc must be 32 hexadecimal characters (128 bits).")

    if adm and not (adm.isdigit() or re.fullmatch(r"[0-9a-fA-F]{16}", adm)):
        errors.append("ADM1 must be the supplier-provided decimal PIN or a 16-character hex value.")

    if acc and not HEX4.fullmatch(acc):
        errors.append("ACC must be exactly 4 hexadecimal characters (2 bytes).")

    if imsi and mcc and mnc and not imsi.startswith(mcc + mnc):
        errors.append("IMSI does not start with the entered MCC+MNC.")

    if len(p.get("operator_name", "")) > 16:
        errors.append("Operator name must be at most 16 characters for pySim-prog.")

    return errors
