const $ = id => document.getElementById(id);
let quartos = [];
async function listar() {
    quartos = await api('/api/quartos');
    $('lista').innerHTML = quartos.map(q => `<tr><td data-label="Número">${esc(q.numero)}</td><td data-label="Nome / tipo">${esc(q.nome)}</td><td data-label="Capacidade">${q.capacidade}</td>
        <td data-label="" class="acoes"><button class="btn-mini" data-a="editar" data-id="${q.id}">Editar</button>
        <button class="btn-mini" style="background:#ef4444" data-a="excluir" data-id="${q.id}">Excluir</button></td></tr>`).join('') || '<tr><td colspan="4" data-label="">Nenhum quarto cadastrado.</td></tr>';
}
let editando = null;
$('lista').addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    const q = quartos.find(x => x.id === b.dataset.id);
    try {
        if (b.dataset.a === 'editar') { editando = q.id; ['numero', 'nome', 'capacidade'].forEach(c => $(c).value = q[c]); scrollTo({ top: 0, behavior: 'smooth' }); }
        if (b.dataset.a === 'excluir' && await mostrarConfirmacao(`Excluir o quarto ${q.numero}?`)) { await api('/api/quartos/' + q.id, { method: 'DELETE' }); listar(); }
    } catch (err) { mostrarAlerta(err.message); }
});
$('form').addEventListener('submit', e => comTrava(e, async () => {
    const corpo = { numero: $('numero').value, nome: $('nome').value, capacidade: $('capacidade').value };
    try {
        await api(editando ? '/api/quartos/' + editando : '/api/quartos', { method: editando ? 'PUT' : 'POST', body: JSON.stringify(corpo) });
        editando = null; $('form').reset(); listar();
    } catch (err) { mostrarAlerta(err.message); }
}));
listar().catch(e => mostrarAlerta(e.message));

// ---------- bloqueio de datas ----------
(async () => {
    const qs = await api('/api/quartos');
    $('b-quarto').innerHTML = qs.map(q => `<option value="${q.id}">${esc(q.numero)}</option>`).join('');
    const nome = id => (qs.find(q => q.id === id) || {}).numero || '?';
    window.listarBloqueios = async () => {
        const lista = await api('/api/indisponiveis');
        $('lista-bloq').innerHTML = lista.map(b => `<tr><td data-label="Quarto">${esc(nome(b.quarto_id))}</td>
            <td data-label="Período">${dataBR(b.inicio)} → ${dataBR(b.fim)}</td><td data-label="Motivo">${esc(b.motivo_texto)}</td><td data-label="Observação">${esc(b.observacao) || '—'}</td>
            <td data-label="" class="acoes"><button class="btn-mini" style="background:#ef4444" data-bid="${b.id}">Remover</button></td></tr>`).join('')
            || '<tr><td colspan="5" data-label="">Nenhum bloqueio.</td></tr>';
    };
    await listarBloqueios();
})().catch(e => mostrarAlerta(e.message));
$('form-bloq').addEventListener('submit', e => comTrava(e, async () => {
    try {
        await api('/api/indisponiveis', { method: 'POST', body: JSON.stringify({ quarto_id: $('b-quarto').value, inicio: $('b-inicio').value, fim: $('b-fim').value, motivo: $('b-motivo').value, observacao: $('b-obs').value }) });
        $('form-bloq').reset(); await listarBloqueios();
    } catch (err) { mostrarAlerta(err.message); }
}));
$('lista-bloq').addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b || !await mostrarConfirmacao('Remover este bloqueio? As datas voltam a ficar livres.')) return;
    try { await api('/api/indisponiveis/' + b.dataset.bid, { method: 'DELETE' }); listarBloqueios(); } catch (err) { mostrarAlerta(err.message); }
});
