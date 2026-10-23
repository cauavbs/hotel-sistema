from flask import Blueprint, render_template

from autenticacao.decoradores import login_obrigatorio

bp = Blueprint("paginas", __name__)

PAGINAS = {"hoje": "/", "calendario": "/calendario", "anual": "/anual", "reservas": "/reservas", "historico": "/historico", "quartos": "/quartos",
           "custos": "/custos", "relatorios": "/relatorios", "integracoes": "/integracoes", "backup": "/backup"}


def _registrar(nome, rota):
    @bp.route(rota, endpoint=nome)
    @login_obrigatorio
    def pagina():
        return render_template(f"{nome}.html", active_page=nome)


for _nome, _rota in PAGINAS.items():
    _registrar(_nome, _rota)
