"""iCal (.ics): leitura dos calendários do Airbnb e do Booking e geração dos calendários do sistema."""
import ipaddress
import re
import socket
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import requests

LIMITE_BYTES = 2_000_000
MARCA = "@hotel-sistema"        # termina o UID de tudo que o sistema exporta (serve para reconhecer eco)


def _desdobrar(texto):
    linhas = []
    for l in texto.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if l[:1] in (" ", "\t") and linhas:
            linhas[-1] += l[1:]                 # linha continuada
        else:
            linhas.append(l)
    return linhas


def _data(valor):
    m = re.match(r"\s*(\d{4})(\d{2})(\d{2})", valor)
    if not m:
        raise ValueError("data inválida")
    return date(int(m[1]), int(m[2]), int(m[3]))


def _texto(valor):
    return valor.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def ler(texto):
    """Devolve [{uid, inicio, fim, resumo, descricao, status}] (datas AAAA-MM-DD; fim = dia da saída)."""
    if "BEGIN:VCALENDAR" not in texto.upper():
        raise ValueError("O link não devolveu um calendário (.ics) válido.")
    eventos, atual = [], None
    for linha in _desdobrar(texto):
        u = linha.strip().upper()
        if u == "BEGIN:VEVENT":
            atual = {}
        elif u == "END:VEVENT":
            if atual is not None and "DTSTART" in atual:
                try:
                    ini = _data(atual["DTSTART"])
                    fim = _data(atual["DTEND"]) if "DTEND" in atual else ini + timedelta(days=1)
                except ValueError:
                    ini = None
                if ini:
                    if fim <= ini:
                        fim = ini + timedelta(days=1)
                    eventos.append({"uid": atual.get("UID") or f"sem-uid-{ini}-{fim}", "inicio": ini.isoformat(), "fim": fim.isoformat(),
                                    "resumo": _texto(atual.get("SUMMARY", "")), "descricao": _texto(atual.get("DESCRIPTION", "")),
                                    "status": atual.get("STATUS", "").strip().upper()})
            atual = None
        elif atual is not None and ":" in linha:
            nome, _, valor = linha.partition(":")
            atual.setdefault(nome.split(";")[0].strip().upper(), valor)
        if len(eventos) > 3000:
            break
    return eventos


def gerar(nome, eventos):
    """Calendário .ics com dias inteiros. Sem nomes nem dados pessoais: só 'Reservado' ou 'Bloqueado'."""
    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Hotel Sistema//Calendario//PT", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
              "X-WR-CALNAME:" + re.sub(r"[^\w .-]", "", nome)]
    for e in eventos:
        linhas += ["BEGIN:VEVENT", f"UID:{e['uid']}", f"DTSTAMP:{agora}", f"DTSTART;VALUE=DATE:{e['inicio'].replace('-', '')}",
                   f"DTEND;VALUE=DATE:{e['fim'].replace('-', '')}", f"SUMMARY:{e['resumo']}", "TRANSP:OPAQUE", "END:VEVENT"]
    linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas) + "\r\n"


def validar_url_basica(url):
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or len(url) > 600:
        raise ValueError("O link precisa começar com https:// e ter no máximo 600 caracteres.")


def _url_segura(url):
    """Só https e nunca para a rede interna (evita que o sistema seja usado para acessar endereços privados)."""
    validar_url_basica(url)
    try:
        infos = socket.getaddrinfo(urlparse(url).hostname, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError("Não consegui encontrar o endereço deste link.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError("Endereço do link não permitido.")


def buscar(url):
    for _ in range(4):                          # segue até 3 redirecionamentos, conferindo cada destino
        _url_segura(url)
        r = requests.get(url, timeout=10, allow_redirects=False, stream=True, headers={"User-Agent": "HotelSistema-iCal/1.0"})
        if r.is_redirect:
            url = urljoin(url, r.headers.get("Location", ""))
            continue
        r.raise_for_status()
        dados = r.raw.read(LIMITE_BYTES + 1, decode_content=True)
        if len(dados) > LIMITE_BYTES:
            raise ValueError("O calendário é grande demais.")
        return dados.decode("utf-8", "replace")
    raise ValueError("Redirecionamentos demais neste link.")
