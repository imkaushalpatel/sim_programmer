from dataclasses import dataclass

@dataclass
class CardStatus:
    reader: str
    atr: str
    connected: bool
    message: str

class PcscService:
    def list_readers(self) -> list[str]:
        try:
            from smartcard.System import readers
            return [str(r) for r in readers()]
        except Exception as exc:
            raise RuntimeError(
                "Unable to enumerate PC/SC readers. Install pyscard and the reader/PCSC driver."
            ) from exc

    def check_card(self, reader_index: int) -> CardStatus:
        try:
            from smartcard.System import readers
            rs = readers()
            if not rs:
                return CardStatus("", "", False, "No PC/SC readers found.")
            if reader_index < 0 or reader_index >= len(rs):
                return CardStatus("", "", False, "Selected reader is no longer available.")

            reader = rs[reader_index]
            conn = reader.createConnection()
            conn.connect()
            atr = "".join(f"{x:02X}" for x in conn.getATR())
            conn.disconnect()
            return CardStatus(str(reader), atr, True, "Card detected.")
        except Exception as exc:
            return CardStatus("", "", False, f"No usable card detected: {exc}")
