const $ = id => document.getElementById(id);
const NOME = { airbnb: 'Airbnb', booking: 'Booking' };
let quartos = [];

function estadoTxt(e) {
    if (!e) return 'Nunca sincronizado.';
    const q = new Date(e.ultima).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
    if (!e.ok) return `❌ ${q} · ${esc(e.erro)}`;
    return `✅ ${q} · ${e.criadas || 0} nova(s), ${e.atualizadas || 0} alterada(s), ${e.canceladas || 0} cancelada(s), ${e.bloqueios || 0} bloqueio(s)` + (e.vinculadas ? `, ${e.vinculadas} vinculada(s) às que você já lançou` : '')
        + (e.conflitos ? ` · ⚠ ${e.conflitos} conflito(s) de datas` : '') + (e.aviso ? ` · ${esc(e.aviso)}` : '');
}

function desenhar() {
    $('quartos').innerHTML = quartos.map(q => `<section class="card ical-quarto" data-q="${q.id}">
        <h2 style="margin-bottom:12px">Quarto ${esc(q.numero)}</h2>
        ${Object.keys(NOME).map(c => `<div class="ical-canal"><h3>${NOME[c]}</h3>
            <label>Entregar ao ${NOME[c]} (cole na importação de calendário de lá)</label>
            <div class="copiar"><input readonly value="${esc(q.links[c])}"><button type="button" class="btn-mini" data-copiar="${c}">Copiar</button></div>
            <label>Link do ${NOME[c]} (o sistema lê)</label>
            <input class="url" data-c="${c}" placeholder="https://..." value="${esc(q['ical_' + c])}" autocomplete="off">
            <small class="estado" id="e-${q.id}-${c}">${estadoTxt(q.estado[c])}</small></div>`).join('')}
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px"><button type="button" class="btn-mini" data-salvar style="flex:0 0 auto">Salvar links</button>
            <button type="button" class="btn-mini" data-sync style="background:#0f766e;flex:0 0 auto">Sincronizar este quarto</button></div></section>`).join('')
        || '<section class="card"><p>Cadastre os quartos primeiro (aba Quartos e Bloqueios).</p></section>';
}

async function carregar() { quartos = await api('/api/ical/config'); desenhar(); }

async function sincronizarQuarto(q, canais) {
    for (const c of canais) {
        const el = $(`e-${q.id}-${c}`); el.textContent = 'Sincronizando…';
        const r = await api('/api/ical/sincronizar', { method: 'POST', body: JSON.stringify({ quarto_id: q.id, canal: c }) });
        el.innerHTML = r.erro ? `❌ ${esc(r.erro)}` : estadoTxt({ ok: true, ultima: new Date().toISOString(), ...r });
    }
}

$('quartos').addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    const card = b.closest('.ical-quarto'), q = quartos.find(x => x.id === card.dataset.q);
    try {
        if (b.dataset.copiar) {
            const inp = b.parentElement.querySelector('input');
            try { await navigator.clipboard.writeText(inp.value); } catch { inp.select(); document.execCommand('copy'); }
            b.textContent = 'Copiado!'; setTimeout(() => b.textContent = 'Copiar', 1500);
        } else if (b.dataset.salvar !== undefined || b.dataset.sync !== undefined) {
            const corpo = Object.fromEntries([...card.querySelectorAll('.url')].map(i => ['ical_' + i.dataset.c, i.value]));
            b.disabled = true;
            try {
                await api('/api/ical/quartos/' + q.id, { method: 'PUT', body: JSON.stringify(corpo) });
                Object.assign(q, corpo);
                if (b.dataset.sync !== undefined) await sincronizarQuarto(q, Object.keys(NOME).filter(c => q['ical_' + c]));
                else mostrarAlerta('Links salvos!');
            } finally { b.disabled = false; }
        }
    } catch (err) { mostrarAlerta(err.message); }
});

$('sync-tudo').onclick = async () => {
    const b = $('sync-tudo'); b.disabled = true; $('status-geral').textContent = 'Sincronizando…';
    try {
        for (const q of quartos) await sincronizarQuarto(q, Object.keys(NOME).filter(c => q['ical_' + c]));
        $('status-geral').textContent = 'Pronto. Confira a aba Hoje para reservas importadas a completar e conflitos de datas.';
    } catch (err) { $('status-geral').textContent = ''; mostrarAlerta(err.message); } finally { b.disabled = false; }
};

$('novo-token').onclick = async () => {
    if (!await mostrarConfirmacao('Gerar novos links de entrega? Os links atuais param de funcionar e você precisará colar os novos no Airbnb e no Booking.')) return;
    try { await api('/api/ical/token/regenerar', { method: 'POST' }); await carregar(); mostrarAlerta('Novos links gerados. Cole-os de novo nas plataformas.'); }
    catch (err) { mostrarAlerta(err.message); }
};
carregar().catch(e => mostrarAlerta(e.message));
