from datetime import date


def br(iso: str) -> str:
    return "/".join(reversed(iso.split("-")))


def noites(checkin: str, checkout: str) -> int:
    return (date.fromisoformat(checkout) - date.fromisoformat(checkin)).days
