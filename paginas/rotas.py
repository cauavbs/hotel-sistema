from flask import Blueprint, render_template

from autenticacao.decoradores import login_obrigatorio

bp = Blueprint("paginas", __name__)

PAGINAS = {"calendario": "/", "anual": "/anual", "reservas": "/reservas", "quartos": "/quartos",
           "custos": "/custos", "relatorios": "/relatorios"}


def _registrar(nome, rota):
    @bp.route(rota, endpoint=nome)
    @login_obrigatorio
    def pagina():
        return render_template(f"{nome}.html", active_page=nome)


for _nome, _rota in PAGINAS.items():
    _registrar(_nome, _rota)
