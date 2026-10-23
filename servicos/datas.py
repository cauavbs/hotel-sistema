from datetime import date, datetime, timedelta, timezone

FUSO = timezone(timedelta(hours=-3))  # horário de Brasília / São Luís (sem horário de verão)


def hoje_local() -> date:
    """Data de hoje no Brasil. O servidor da Vercel roda em UTC, então date.today() erraria depois das 21h."""
    return datetime.now(FUSO).date()


def agora_iso() -> str:
    return datetime.now(FUSO).isoformat(timespec="seconds")


def br(iso: str) -> str:
    return "/".join(reversed(iso.split("-")))


def noites(checkin: str, checkout: str) -> int:
    return (date.fromisoformat(checkout) - date.fromisoformat(checkin)).days
