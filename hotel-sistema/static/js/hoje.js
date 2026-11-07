const $ = id => document.getElementById(id);
const hoje = hojeLocal(), amanha = somarDias(hoje, 1);
let quartos = [], reservas = [], bloqueios = [];
const nomeQ = id => (quartos.find(q => q.id === id) || {}).numero || '?';
const ativas = () => reservas.filter(r => r.status !== 'cancelada');

const item = r => `<a class="linha-hoje" href="/reservas?editar=${esc(r.id)}"><b>${esc(r.hospede)}${r.acompanhantes.length ? ` <small>(+${r.acompanhantes.length})</small>` : ''}</b>
    <span>Quarto ${esc(nomeQ(r.quarto_id))} · ${dataBR(r.checkin)} → ${dataBR(r.checkout)} <span class="selo ${r.situacao}">${r.situacao}</span></span></a>`;
const bloco = (titulo, lista) => lista.length ? `<div class="sub-hoje">${titulo}</div>${lista.map(item).join('')}` : '';
const vazio = txt => `<p style="color:#64748b;margin:0">${txt}</p>`;

function desenhar() {
    const a = ativas();
    const cheg = [a.filter(r => r.checkin === hoje), a.filter(r => r.checkin === amanha)];
    const said = [a.filter(r => r.checkout === hoje), a.filter(r => r.checkout === amanha)];
    const casa = a.filter(r => r.checkin <= hoje && hoje < r.checkout);
    const ocupados = new Set(casa.map(r => r.quarto_id));
    const bloqHoje = bloqueios.filter(b => b.inicio <= hoje && hoje < b.fim);
    const bloqIds = new Set(bloqHoje.map(b => b.quarto_id));
    const livres = quartos.filter(q => !ocupados.has(q.id) && !bloqIds.has(q.id));
    const saldos = a.filter(r => r.saldo > 0.004 && r.checkin <= somarDias(hoje, 7)).sort((x, y) => x.checkin.localeCompare(y.checkin));

    $('data-hoje').textContent = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    $('kpis').innerHTML = [['Hóspedes na casa', casa.reduce((s, r) => s + (r.hospedes || 1), 0)], ['Chegadas hoje', cheg[0].length], ['Saídas hoje', said[0].length],
    ['Quartos livres', `${livres.length} de ${quartos.length}`], ['A receber', brl(saldos.reduce((s, r) => s + r.saldo, 0))]].map(([t, v]) => `<div class="kpi"><small>${t}</small><b>${v}</b></div>`).join('');

    $('quartos').innerHTML = quartos.map(q => {
        const r = casa.find(x => x.quarto_id === q.id), s = a.find(x => x.quarto_id === q.id && x.checkout === hoje), b = bloqHoje.find(x => x.quarto_id === q.id);
        const prox = a.filter(x => x.quarto_id === q.id && x.checkin > hoje).sort((x, y) => x.checkin.localeCompare(y.checkin))[0];
        let estado, cls;
        if (r) { estado = `Ocupado · ${esc(r.hospede)} (até ${dataBR(r.checkout)})`; cls = 'ocup'; }
        else if (b) { estado = `Bloqueado · ${esc(b.motivo_texto)} (até ${dataBR(b.fim)})`; cls = 'bloq'; }
        else if (s) { estado = `Saída hoje · ${esc(s.hospede)}`; cls = 'saida'; }
        else { estado = 'Livre'; cls = 'livre'; }
        return `<div class="qh ${cls}"><div class="qh-topo"><b>${esc(q.numero)}</b><span>${estado}</span></div>
            ${prox ? `<small>Próxima chegada: ${dataBR(prox.checkin)}</small>` : '<small>Sem próximas chegadas</small>'}
            <label class="limp">Limpeza <select data-id="${q.id}">
                <option value="limpo" ${q.limpeza === 'limpo' ? 'selected' : ''}>Limpo</option><option value="a_limpar" ${q.limpeza === 'a_limpar' ? 'selected' : ''}>A limpar</option></select></label>
            ${s && q.limpeza === 'limpo' && !r ? '<small class="aviso">Saída hoje: marque "A limpar" quando o hóspede sair.</small>' : ''}</div>`;
    }).join('') || vazio('Cadastre os quartos na aba Quartos.');

    const incompletas = a.filter(r => r.incompleta), conflitos = a.filter(r => r.conflito);
    $('atencao').hidden = !(incompletas.length || conflitos.length);
    $('atencao').innerHTML = (conflitos.length ? `<h2 style="color:#b91c1c">⚠ Conflitos de datas (${conflitos.length})</h2><p style="margin-top:0">Uma reserva importada bate com outra reserva ou bloqueio. Resolva cancelando uma delas na plataforma ou aqui.</p>${conflitos.map(item).join('')}` : '')
        + (incompletas.length ? `<h2 style="margin-top:${conflitos.length ? 18 : 0}px">📥 Reservas importadas para completar (${incompletas.length})</h2><p style="margin-top:0">Vieram do Airbnb ou do Booking só com as datas. Abra e preencha hóspede e valor.</p>${incompletas.map(item).join('')}` : '');

    $('chegadas').innerHTML = bloco('Hoje', cheg[0]) + bloco('Amanhã', cheg[1]) || vazio('Nenhuma chegada hoje ou amanhã.');
    $('saidas').innerHTML = bloco('Hoje', said[0]) + bloco('Amanhã', said[1]) || vazio('Nenhuma saída hoje ou amanhã.');
    $('nacasa').innerHTML = casa.map(item).join('') || vazio('Ninguém hospedado esta noite.');
    $('saldos').innerHTML = saldos.slice(0, 8).map(r => `<a class="linha-hoje" href="/reservas?editar=${esc(r.id)}"><b>${esc(r.hospede)}</b>
        <span>Quarto ${esc(nomeQ(r.quarto_id))} · ${dataBR(r.checkin)} · falta <b style="color:#b91c1c">${brl(r.saldo)}</b></span></a>`).join('')
        + (saldos.length > 8 ? vazio(`+ ${saldos.length - 8} reservas com saldo. Veja no Histórico.`) : '') || vazio('Nenhum saldo pendente.');
}

$('quartos').addEventListener('change', async e => {
    if (!e.target.dataset.id) return;
    try { await api(`/api/quartos/${e.target.dataset.id}/limpeza`, { method: 'PATCH', body: JSON.stringify({ status: e.target.value }) }); await carregar(); }
    catch (err) { mostrarAlerta(err.message); }
});

async function carregar() {
    [quartos, reservas, bloqueios] = await Promise.all([api('/api/quartos'), api('/api/reservas'), api('/api/indisponiveis')]);
    desenhar();
}
carregar().then(async () => {
    // Sincroniza com Airbnb e Booking o que estiver atrasado (mais de 30 min), uma vez por abertura da página.
    try {
        const r = await api('/api/ical/sincronizar-vencidos', { method: 'POST' });
        if (r.sincronizados) $('sync-status').textContent = `Airbnb/Booking sincronizados às ${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}` + (r.erros ? ` · ${r.erros} com erro (veja a aba Airbnb e Booking)` : '');
        if (r.mudancas) await carregar();
    } catch { /* a sincronização não deve atrapalhar o painel */ }
}).catch(e => mostrarAlerta(e.message));
