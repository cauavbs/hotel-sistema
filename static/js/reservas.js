const $ = id => document.getElementById(id);
const CAMPOS = ['quarto_id', 'checkin', 'checkout', 'origem', 'hospede', 'telefone', 'hospedes', 'valor_total', 'valor_pago', 'forma_pagamento', 'status', 'observacao'];
let editando = null, quartos = [], reservas = [];

function limpar() {
    editando = null;
    $('form').reset();
    $('titulo-form').textContent = '📝 Nova Reserva';
    $('cancelar-edicao').style.display = 'none';
}

function editar(r) {
    editando = r.id;
    CAMPOS.forEach(c => { $(c).value = r[c] ?? ''; });
    $('titulo-form').textContent = '✏️ Editando reserva de ' + r.hospede;
    $('cancelar-edicao').style.display = 'block';
    scrollTo({ top: 0, behavior: 'smooth' });
}

async function listar() {
    const p = new URLSearchParams();
    if ($('f-mes').value) p.set('mes', $('f-mes').value);
    reservas = await api('/api/reservas?' + p);
    const nome = id => (quartos.find(q => q.id === id) || {}).numero || '?';
    const o = $('f-origem').value, s = $('f-situacao').value;
    $('lista').innerHTML = reservas.filter(r => (!o || r.origem === o) && (!s || r.situacao === s)).map(r => `
        <tr style="${r.status === 'cancelada' ? 'opacity:.5;text-decoration:line-through;' : ''}">
            <td data-label="Quarto">${esc(nome(r.quarto_id))}</td><td data-label="Hóspede">${esc(r.hospede)}</td>
            <td data-label="Período">${dataBR(r.checkin)} → ${dataBR(r.checkout)} (${r.noites}n)</td><td data-label="Origem">${NOMES_ORIGEM[r.origem]}</td>
            <td data-label="Total">${brl(r.valor_total)}</td><td data-label="Pago">${brl(r.valor_pago)}</td>
            <td data-label="Pagamento"><span class="selo ${r.situacao}">${r.situacao}</span> ${esc(r.forma_pagamento)}</td>
            <td data-label="" class="acoes"><button class="btn-mini" data-a="editar" data-id="${r.id}">Editar</button>
                ${r.situacao !== 'pago' && r.status !== 'cancelada' ? `<button class="btn-mini" style="background:#16a34a" data-a="quitar" data-id="${r.id}">Quitar</button>` : ''}
                <button class="btn-mini" style="background:#ef4444" data-a="excluir" data-id="${r.id}">Excluir</button></td>
        </tr>`).join('') || '<tr><td colspan="8" data-label="">Nenhuma reserva encontrada.</td></tr>';
}

$('lista').addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    const r = reservas.find(x => x.id === b.dataset.id);
    try {
        if (b.dataset.a === 'editar') editar(r);
        if (b.dataset.a === 'excluir' && await mostrarConfirmacao('Excluir esta reserva?')) { await api('/api/reservas/' + r.id, { method: 'DELETE' }); listar(); }
        if (b.dataset.a === 'quitar') {
            const forma = (await mostrarPrompt('Forma de pagamento (pix, dinheiro, debito, credito ou plataforma):', r.forma_pagamento || 'pix') || '').trim().toLowerCase();
            if (!forma) return;
            await api('/api/reservas/' + r.id, { method: 'PUT', body: JSON.stringify({ ...r, valor_pago: r.valor_total, forma_pagamento: forma }) });
            listar();
        }
    } catch (err) { mostrarAlerta(err.message); }
});

$('form').addEventListener('submit', async e => {
    e.preventDefault();
    const corpo = Object.fromEntries(CAMPOS.map(c => [c, $(c).value]));
    try {
        await api(editando ? '/api/reservas/' + editando : '/api/reservas', { method: editando ? 'PUT' : 'POST', body: JSON.stringify(corpo) });
        limpar(); listar(); mostrarAlerta('Reserva salva!');
    } catch (err) { mostrarAlerta(err.message); }
});
$('cancelar-edicao').onclick = limpar;
['f-mes', 'f-origem', 'f-situacao'].forEach(i => $(i).onchange = listar);

(async () => {
    quartos = await api('/api/quartos');
    $('quarto_id').innerHTML = quartos.map(q => `<option value="${q.id}">${esc(q.numero)}${q.nome ? ' · ' + esc(q.nome) : ''}</option>`).join('');
    await listar();
    const p = new URLSearchParams(location.search);
    if (p.get('editar')) { const r = reservas.find(x => x.id === p.get('editar')); if (r) editar(r); }
    if (p.get('quarto')) { $('quarto_id').value = p.get('quarto'); $('checkin').value = p.get('checkin') || ''; }
})().catch(e => mostrarAlerta(e.message));
