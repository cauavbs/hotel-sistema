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
$('form').addEventListener('submit', async e => {
    e.preventDefault();
    const corpo = { numero: $('numero').value, nome: $('nome').value, capacidade: $('capacidade').value };
    try {
        await api(editando ? '/api/quartos/' + editando : '/api/quartos', { method: editando ? 'PUT' : 'POST', body: JSON.stringify(corpo) });
        editando = null; $('form').reset(); listar();
    } catch (err) { mostrarAlerta(err.message); }
});
listar().catch(e => mostrarAlerta(e.message));
