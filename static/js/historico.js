const $ = id => document.getElementById(id);
const hoje = new Date().toLocaleDateString('sv-SE');          // AAAA-MM-DD no horário local
const FORMAS = { pix: 'Pix', dinheiro: 'Dinheiro', debito: 'Débito', credito: 'Crédito', plataforma: 'Repasse da plataforma', outros: 'Outros' };
const ABAS = [['concluida', 'Concluídas'], ['andamento', 'Em andamento'], ['futura', 'Futuras'], ['cancelada', 'Canceladas'], ['todas', 'Todas']];
const ROTULO_FASE = { concluida: 'Concluída', andamento: 'Em andamento', futura: 'Futura', cancelada: 'Cancelada' };
let aba = 'concluida', reservas = [], quartos = [];

const fase = r => r.status === 'cancelada' ? 'cancelada' : r.checkout <= hoje ? 'concluida' : r.checkin <= hoje ? 'andamento' : 'futura';
const dig = s => String(s || '').replace(/\D/g, '');
const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const nomeQuarto = id => (quartos.find(q => q.id === id) || {}).numero || '?';

// A busca vale para o hóspede principal e para os acompanhantes (nome, CPF e telefone)
function casaBusca(r, q) {
    if (!q) return true;
    const d = dig(q), n = norm(q);
    const pessoas = [{ nome: r.hospede, cpf: r.cpf, tel: r.telefone }, ...r.acompanhantes.map(a => ({ nome: a.nome, cpf: a.cpf, tel: '' }))];
    return pessoas.some(p => norm(p.nome).includes(n) || (d.length >= 3 && (dig(p.cpf).includes(d) || dig(p.tel).includes(d))));
}

const mesmaPessoa = (a, b) => (a.cpf && a.cpf === b.cpf) || (!a.cpf && dig(a.telefone) && dig(a.telefone) === dig(b.telefone) && norm(a.hospede) === norm(b.hospede));
const estadiaNumero = r => 1 + reservas.filter(x => x.id !== r.id && x.status !== 'cancelada' && x.checkin < r.checkin && mesmaPessoa(r, x)).length;

function cartao(r, mostrarFase) {
    const n = estadiaNumero(r), acomp = r.acompanhantes.length;
    const pags = r.pagamentos.map(p => `<li>${brl(p.valor)} · ${FORMAS[p.forma] || esc(p.forma)} ${linkComprovante(p.comprovante_id, p.comprovante_nome)}</li>`).join('');
    return `<details class="res ${r.status === 'cancelada' ? 'r-cancelada' : ''}">
        <summary>
            <div class="r-topo"><b>${esc(r.hospede)}${acomp ? ` <small>(+${acomp})</small>` : ''}${n > 1 ? ` <small title="Hóspede recorrente">🔁 ${n}ª estadia</small>` : ''}</b>
                <span class="selo ${r.status === 'cancelada' ? 'cancelada' : r.situacao}">${r.status === 'cancelada' ? 'cancelada' : r.situacao}</span></div>
            <div class="r-sub">Quarto ${esc(nomeQuarto(r.quarto_id))} · ${dataBR(r.checkin)} → ${dataBR(r.checkout)} (${r.noites}n) · ${NOMES_ORIGEM[r.origem]}${mostrarFase ? ' · ' + ROTULO_FASE[fase(r)] : ''}</div>
        </summary>
        <div class="r-corpo">
            <div class="det-grid">
                <div><b>CPF</b><br>${esc(fmtCPF(r.cpf)) || '—'}</div><div><b>Telefone</b><br>${esc(r.telefone) || '—'}</div>
                <div><b>Valor total</b><br>${brl(r.valor_total)}</div><div><b>Pago</b><br>${brl(r.valor_pago)}</div><div><b>Saldo</b><br>${brl(r.saldo)}</div>
            </div>
            ${acomp ? `<h4>Acompanhantes</h4><ul>${r.acompanhantes.map(a => `<li>${esc(a.nome)}${a.cpf ? ' · CPF ' + esc(fmtCPF(a.cpf)) : ''}</li>`).join('')}</ul>` : ''}
            ${pags ? `<h4>Pagamentos e comprovantes</h4><ul>${pags}</ul>` : ''}
            ${r.observacao ? `<h4>Observações</h4><p style="margin:0">${esc(r.observacao)}</p>` : ''}
            <p style="margin:12px 0 0"><a href="/reservas?editar=${esc(r.id)}">✏️ Editar reserva</a></p>
        </div></details>`;
}

function desenhar() {
    const q = $('busca').value.trim(), ano = $('f-ano').value, qto = $('f-quarto').value;
    const base = reservas.filter(r => casaBusca(r, q) && (!ano || r.checkin.slice(0, 4) === ano) && (!qto || r.quarto_id === qto));

    $('abas').innerHTML = ABAS.map(([k, t]) => `<button type="button" data-f="${k}" class="${k === aba ? 'ativa' : ''}">${t}<small>${k === 'todas' ? base.length : base.filter(r => fase(r) === k).length}</small></button>`).join('');

    const lista = (aba === 'todas' ? base : base.filter(r => fase(r) === aba)).sort((a, b) =>
        aba === 'futura' ? a.checkin.localeCompare(b.checkin) : aba === 'concluida' ? b.checkout.localeCompare(a.checkout) : b.checkin.localeCompare(a.checkin));

    const v = lista.filter(r => r.status !== 'cancelada'), soma = f => v.reduce((s, r) => s + f(r), 0);
    const kpis = [['Reservas', lista.length]];
    if (aba !== 'cancelada') kpis.push(['Noites', soma(r => r.noites)], ['Valor total', brl(soma(r => r.valor_total))], ['Recebido', brl(soma(r => r.valor_pago))], ['A receber', brl(soma(r => r.saldo))]);
    $('totais').innerHTML = kpis.map(([t, x]) => `<div class="kpi"><small>${t}</small><b>${x}</b></div>`).join('');

    $('lista').innerHTML = lista.map(r => cartao(r, aba === 'todas')).join('') || '<p style="color:#64748b">Nenhuma reserva encontrada com estes filtros.</p>';
}

$('abas').addEventListener('click', e => { const b = e.target.closest('button'); if (b) { aba = b.dataset.f; desenhar(); } });
$('busca').addEventListener('input', desenhar);
$('f-ano').addEventListener('change', desenhar);
$('f-quarto').addEventListener('change', desenhar);

(async () => {
    [quartos, reservas] = await Promise.all([api('/api/quartos'), api('/api/reservas')]);
    const anos = [...new Set(reservas.map(r => r.checkin.slice(0, 4)))].sort().reverse();
    $('f-ano').innerHTML += anos.map(a => `<option>${a}</option>`).join('');
    $('f-quarto').innerHTML += quartos.map(q => `<option value="${q.id}">Quarto ${esc(q.numero)}</option>`).join('');
    desenhar();
})().catch(e => mostrarAlerta(e.message));
