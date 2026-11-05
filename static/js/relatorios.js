const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const PALETA = ['#0f766e', '#ff5a5f', '#003580', '#f59e0b', '#8b5cf6', '#64748b'];
const anoSel = document.getElementById('ano');
const ano0 = new Date().getFullYear();
for (let a = ano0 + 1; a >= ano0 - 4; a--) anoSel.innerHTML += `<option ${a === ano0 ? 'selected' : ''}>${a}</option>`;
let charts = [];
Chart.defaults.font.size = innerWidth < 600 ? 11 : 13;

function grafico(titulo, tipo, labels, datasets, extra = {}) {
    const box = document.createElement('div');
    box.innerHTML = `<h3 style="font-size:1rem;margin-bottom:8px;">${titulo}</h3><div class="gbox"><canvas></canvas></div>`;
    document.getElementById('graficos').appendChild(box);
    charts.push(new Chart(box.querySelector('canvas'), { type: tipo, data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { boxWidth: 12 } } }, ...extra } }));
}
const pizza = (t, obj, fmt = v => v) => grafico(t, 'doughnut', Object.keys(obj), [{ data: Object.values(obj).map(fmt), backgroundColor: PALETA }]);

async function carregar() {
    try {
        const d = await api('/api/relatorios?ano=' + anoSel.value), k = d.kpis, m = d.meses;
        const kpis = [['Receita', brl(k.receita)], ['Recebido', brl(k.recebido)], ['A receber', brl(k.a_receber)], ['Custos', brl(k.custos)],
        ['Lucro', brl(k.lucro)], ['Reservas', k.reservas], ['Noites vendidas', k.noites], ['Ocupação', k.ocupacao.toFixed(1) + '%'],
        ['Diária média', brl(k.diaria_media)], ['Ticket médio', brl(k.ticket_medio)], ['Permanência média', k.permanencia_media.toFixed(1) + ' noites']];
        document.getElementById('kpis').innerHTML = kpis.map(([t, v]) => `<div class="kpi"><small>${t}</small><b>${v}</b></div>`).join('');

        charts.forEach(c => c.destroy()); charts = [];
        document.getElementById('graficos').innerHTML = '';
        grafico('Receita x Custos x Lucro por mês', 'bar', MESES, [
            { label: 'Receita', data: m.receita, backgroundColor: '#0f766e' },
            { label: 'Custos', data: m.custos, backgroundColor: '#ef4444' },
            { label: 'Lucro', data: m.lucro, type: 'line', borderColor: '#f59e0b', backgroundColor: '#f59e0b' }]);
        grafico('Taxa de ocupação por mês (%)', 'line', MESES, [{ label: 'Ocupação', data: m.ocupacao, borderColor: '#0f766e', fill: false }], { scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } });
        grafico('Época do ano: noites vendidas (todos os anos)', 'bar', MESES, [{ label: 'Noites', data: m.sazonalidade, backgroundColor: '#8b5cf6' }]);
        grafico('Quantas vezes cada quarto foi alugado', 'bar', d.por_quarto.map(q => q.quarto), [
            { label: 'Reservas', data: d.por_quarto.map(q => q.reservas), backgroundColor: '#0f766e' },
            { label: 'Noites', data: d.por_quarto.map(q => q.noites), backgroundColor: '#94a3b8' }]);
        grafico('Receita por quarto (R$)', 'bar', d.por_quarto.map(q => q.quarto), [{ label: 'Receita', data: d.por_quarto.map(q => q.receita), backgroundColor: '#0f766e' }]);
        pizza('Receita por origem (R$)', Object.fromEntries(Object.entries(d.por_origem).map(([o, v]) => [NOMES_ORIGEM[o], v.receita])));
        pizza('Formas de pagamento (R$ recebido)', d.formas_pagamento);
        grafico('Maiores gastos (R$)', 'bar', Object.keys(d.maiores_gastos), [{ label: 'Gasto', data: Object.values(d.maiores_gastos), backgroundColor: '#ef4444' }], { indexAxis: 'y', plugins: { legend: { display: false } } });
    } catch (e) { mostrarAlerta(e.message); }
}
anoSel.onchange = carregar;
carregar();
