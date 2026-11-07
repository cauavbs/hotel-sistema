const $ = id => document.getElementById(id);
let quartos = [];
$('data').value = hojeLocal();
$('f-mes').value = mesAtual();

async function listar() {
    const lista = await api('/api/custos?mes=' + $('f-mes').value);
    $('total').textContent = brl(lista.reduce((s, c) => s + c.valor, 0));
    const nome = id => (quartos.find(q => q.id === id) || {}).numero || 'Geral';
    $('lista').innerHTML = lista.map(c => `<tr><td data-label="Data">${dataBR(c.data)}</td><td data-label="Descrição">${esc(c.descricao)}</td>
        <td data-label="Quarto">${esc(nome(c.quarto_id))}</td><td data-label="Valor">${brl(c.valor)}</td>
        <td data-label="Comprovante">${linkComprovante(c.comprovante_id, c.comprovante_nome) || '—'}</td>
        <td data-label="" class="acoes"><button class="btn-mini" style="background:#ef4444" data-id="${c.id}">Excluir</button></td></tr>`).join('')
        || '<tr><td colspan="6" data-label="">Nenhum gasto neste mês.</td></tr>';
}
$('lista').addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b || !await mostrarConfirmacao('Excluir este gasto e o comprovante?')) return;
    try { await api('/api/custos/' + b.dataset.id, { method: 'DELETE' }); listar(); } catch (err) { mostrarAlerta(err.message); }
});
$('form').addEventListener('submit', e => comTrava(e, async () => {
    const corpo = Object.fromEntries(['data', 'descricao', 'valor', 'quarto_id'].map(c => [c, $(c).value]));
    try {
        const arq = $('arquivo').files[0];
        if (arq) { $('arq-info').textContent = 'Enviando comprovante…'; corpo.comprovante_id = (await enviarComprovante(arq)).id; }
        await api('/api/custos', { method: 'POST', body: JSON.stringify(corpo) });
        $('descricao').value = ''; $('valor').value = ''; $('arquivo').value = ''; $('arq-info').textContent = ''; listar();
    } catch (err) { $('arq-info').textContent = ''; mostrarAlerta(err.message); }
}));
$('f-mes').onchange = listar;
(async () => {
    quartos = await api('/api/quartos');
    $('quarto_id').innerHTML += quartos.map(q => `<option value="${q.id}">${esc(q.numero)}</option>`).join('');
    await listar();
})().catch(e => mostrarAlerta(e.message));
