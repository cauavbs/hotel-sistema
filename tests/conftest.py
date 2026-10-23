"""Banco Realtime simulado em memória, para testar sem o Firebase real.  Rodar: pytest"""
import copy
import itertools
import os
import sys

os.environ.update(FLASK_DEBUG="true", FIREBASE_DATABASE_URL="teste", SECRET_KEY="teste")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import servicos.firebase_service as fs

DB, _ids = {}, itertools.count(1)


class Ref:
    def __init__(self, caminho):
        self.p = [x for x in caminho.split("/") if x]

    def _no(self, criar=False):
        n = DB
        for k in self.p:
            if not isinstance(n, dict) or k not in n:
                if not criar:
                    return None
                n[k] = {}
            n = n[k]
        return n

    def get(self, etag=False, shallow=False):
        no = self._no()
        return {k: True for k in no} if shallow and isinstance(no, dict) else copy.deepcopy(no)

    def set(self, v):
        pai = Ref("/".join(self.p[:-1]))._no(True) if len(self.p) > 1 else DB
        pai[self.p[-1]] = copy.deepcopy(v)

    def update(self, campos):
        for k, v in campos.items():
            Ref("/".join(self.p + [k])).delete() if v is None else Ref("/".join(self.p + [k])).set(v)

    def push(self, v):
        r = Ref("/".join(self.p + [f"id{next(_ids)}"]))
        r.set(v)
        r.key = r.p[-1]
        return r

    def delete(self):
        pai = Ref("/".join(self.p[:-1]))._no(True) if len(self.p) > 1 else DB
        if isinstance(pai, dict):
            pai.pop(self.p[-1], None)

    def transaction(self, fn):
        novo = fn(self.get())          # uma exceção em fn aborta sem gravar, como no Firebase
        self.delete() if novo is None else self.set(novo)
        return novo


fs.referencia = Ref
from app import app as flask_app  # noqa: E402  (precisa vir depois do banco simulado)
import autenticacao.rotas as _rotas  # noqa: E402

_rotas.inicializar_firebase = lambda: None  # não precisa da credencial real nos testes


@pytest.fixture(autouse=True)
def banco_limpo():
    DB.clear()
    yield DB


@pytest.fixture
def client():
    return flask_app.test_client()


@pytest.fixture
def logado(client):
    with client.session_transaction() as s:
        s.update(uid="u1", email="a@b.com", nome="A")
    return client
