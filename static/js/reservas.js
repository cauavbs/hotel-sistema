const $ = id => document.getElementById(id);
const CAMPOS = ['quarto_id', 'checkin', 'checkout', 'origem', 'hospede', 'cpf', 'telefone', 'valor_total', 'status', 'observacao'];
const FORMAS = { pix: 'Pix', dinheiro: 'Dinheiro', debito: 'Débito', credito: 'Crédito', plataforma: 'Repasse da plataforma' };
let editando = null, quartos = [], reservas = [];
mascaraCPF($('cpf'));

// ---------- linhas dinâmicas: acompanhantes e pagamentos ----------
const linhaAcomp = (a = {}) => `<div class="linha ac">
    <input class="a-nome" placeholder="Nome do acompanhante" value="${esc(a.nome || '')}">
    <input class="a-cpf" inputmode="numeric" placeholder="CPF (opcional)" maxlength="14" value="${esc(fmtCPF(a.cpf))}">
    <button type="button" class="btn-mini rem" style="background:#ef4444" aria-label="Remover">✕</button></div>`;

const anexoHTML = (id, nome) => id
    ? `${linkComprovante(id, nome)} <button type="button" class="btn-mini tira" style="background:#64748b">Remover</button>`
    : '<label class="anexar">📎 Anexar comprovante<input type="file" class="p-arq" accept="image/*,application/pdf" hidden></label>';

const linhaPag = (p = {}) => `<div class="linha pg" data-comp="${esc(p.comprovante_id || '')}" data-nomec="${esc(p.comprovante_nome || '')}">
    <input class="p-valor" type="number" min="0" step="0.01" placeholder="Valor (R$)" value="${p.valor ?? ''}">
    <select class="p-forma">${Object.entries(FORMAS).map(([k, v]) => `<option value="${k}" ${k === p.forma ? 'selected' : ''}>${v}</option>`).join('')}</select>
    <div class="p-anexo">${anexoHTML(p.comprovante_id, p.comprovante_nome)}</div>
    <button type="button" class="btn-mini rem" style="background:#ef4444" aria-label="Remover">✕</button></div>`;

function addAcomp(a) { $('acomp').insertAdjacentHTML('beforeend', linhaAcomp(a)); mascaraCPF($('acomp').lastElementChild.querySelector('.a-cpf')); resumo(); }
function addPag(p) { $('pags').insertAdjacentHTML('beforeend', linhaPag(p)); resumo(); }

function resumo() {
    const total = +$('valor_total').value || 0;
    const pago = [...document.querySelectorAll('.p-valor')].reduce((s, i) => s + (+i.value || 0), 0);
    const pessoas = 1 + [...document.querySelectorAll('.a-nome')].filter(i => i.value.trim()).length;
    $('resumo-pag').innerHTML = `👥 ${pessoas} hóspede(s) · Pago: <b>${brl(pago)}</b> · Saldo: <b style="color:${total - pago > 0.004 ? '#b91c1c' : '#166534'}">${brl(total - pago)}</b>`;
}

$('add-acomp').onclick = () => addAcomp();
$('add-pag').onclick = () => addPag();
$('form').addEventListener('input', resumo);

$('acomp').addEventListener('click', e => { if (e.target.closest('.rem')) { e.target.closest('.linha').remove(); resumo(); } });
$('pags').addEventListener('click', e => {
    if (e.target.closest('.rem')) { e.target.closest('.linha').remove(); resumo(); }
    if (e.target.closest('.tira')) {            // tira o anexo (o arquivo só é apagado ao salvar)
        const l = e.target.closest('.linha'); l.dataset.comp = ''; l.dataset.nomec = '';
        l.querySelector('.p-anexo').innerHTML = anexoHTML();
    }
});
$('pags').addEventListener('change', async e => {
    if (!e.target.classList.contains('p-arq') || !e.target.files[0]) return;
    const l = e.target.closest('.linha'), alvo = l.querySelector('.p-anexo');
    alvo.textContent = 'Enviando…';
    try {
        const c = await enviarComprovante(e.target.files[0]);
        l.dataset.comp = c.id; l.dataset.nomec = c.nome; alvo.innerHTML = anexoHTML(c.id, c.nome);
    } catch (err) { alvo.innerHTML = anexoHTML(); mostrarAlerta(err.message); }
});

// ---------- formulário ----------
function limpar() {
    editando = null; $('form').reset();
    $('acomp').innerHTML = ''; $('pags').innerHTML = '';
    $('titulo-form').textContent = '📝 Nova Reserva';
    $('cancelar-edicao').style.display = 'none'; resumo();
}

function editar(r) {
    limpar(); editando = r.id;
    CAMPOS.forEach(c => { $(c).value = r[c] ?? ''; });
    $('cpf').value = fmtCPF(r.cpf);
    (r.acompanhantes || []).forEach(addAcomp);
    (r.pagamentos || []).forEach(addPag);
    $('titulo-form').textContent = '✏️ Editando reserva de ' + r.hospede;
    $('cancelar-edicao').style.display = 'block';
    scrollTo({ top: 0, behavior: 'smooth' }); resumo();
}

function corpoForm() {
    const corpo = Object.fromEntries(CAMPOS.map(c => [c, $(c).value]));
    corpo.acompanhantes = [...document.querySelectorAll('#acomp .linha')].map(l => ({ nome: l.querySelector('.a-nome').value, cpf: l.querySelector('.a-cpf').value })).filter(a => a.nome.trim());
    corpo.pagamentos = [...document.querySelectorAll('#pags .linha')].map(l => ({ valor: l.querySelector('.p-valor').value, forma: l.querySelector('.p-forma').value, comprovante_id: l.dataset.comp })).filter(p => +p.valor > 0);
    return corpo;
}

$('form').addEventListener('submit', async e => {
    e.preventDefault();
    try {
        await api(editando ? '/api/reservas/' + editando : '/api/reservas', { method: editando ? 'PUT' : 'POST', body: JSON.stringify(corpoForm()) });
        limpar(); listar(); mostrarAlerta('Reserva salva!');
    } catch (err) { mostrarAlerta(err.message); }
});
$('cancelar-edicao').onclick = limpar;

// ---------- lista ----------
async function listar() {
    const p = new URLSearchParams();
    if ($('f-mes').value) p.set('mes', $('f-mes').value);
    reservas = await api('/api/reservas?' + p);
    const nome = id => (quartos.find(q => q.id === id) || {}).numero || '?';
    const o = $('f-origem').value, s = $('f-situacao').value;
    $('lista').innerHTML = reservas.filter(r => (!o || r.origem === o) && (!s || r.situacao === s)).map(r => `
        <tr style="${r.status === 'cancelada' ? 'opacity:.5;text-decoration:line-through;' : ''}">
            <td data-label="Quarto">${esc(nome(r.quarto_id))}</td>
            <td data-label="Hóspede">${esc(r.hospede)}${r.acompanhantes.length ? ` <small>(+${r.acompanhantes.length})</small>` : ''}</td>
            <td data-label="Período">${dataBR(r.checkin)} → ${dataBR(r.checkout)} (${r.noites}n)</td><td data-label="Origem">${NOMES_ORIGEM[r.origem]}</td>
            <td data-label="Total">${brl(r.valor_total)}</td><td data-label="Pago">${brl(r.valor_pago)}</td>
            <td data-label="Pagamento"><span class="selo ${r.situacao}">${r.situacao}</span> ${[...new Set(r.pagamentos.map(p => FORMAS[p.forma] || p.forma))].join(', ')}
                ${r.pagamentos.filter(p => p.comprovante_id).map(p => linkComprovante(p.comprovante_id, 'comprovante')).join(' ')}</td>
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
        if (b.dataset.a === 'excluir' && await mostrarConfirmacao('Excluir esta reserva e os comprovantes dela?')) { await api('/api/reservas/' + r.id, { method: 'DELETE' }); listar(); }
        if (b.dataset.a === 'quitar') {      // lança o saldo como novo pagamento; o comprovante pode ser anexado depois em Editar
            const forma = (await mostrarPrompt('Forma de pagamento do saldo (pix, dinheiro, debito, credito ou plataforma):', 'pix') || '').trim().toLowerCase();
            if (!forma) return;
            await api('/api/reservas/' + r.id, { method: 'PUT', body: JSON.stringify({ ...r, pagamentos: [...r.pagamentos, { valor: r.saldo, forma, comprovante_id: '' }] }) });
            listar();
        }
    } catch (err) { mostrarAlerta(err.message); }
});
['f-mes', 'f-origem', 'f-situacao'].forEach(i => $(i).onchange = listar);

(async () => {
    quartos = await api('/api/quartos');
    $('quarto_id').innerHTML = quartos.map(q => `<option value="${q.id}">${esc(q.numero)}${q.nome ? ' · ' + esc(q.nome) : ''}</option>`).join('');
    await listar(); resumo();
    const p = new URLSearchParams(location.search);
    if (p.get('editar')) { const r = reservas.find(x => x.id === p.get('editar')) || (await api('/api/reservas')).find(x => x.id === p.get('editar')); if (r) editar(r); }
    if (p.get('quarto')) { $('quarto_id').value = p.get('quarto'); $('checkin').value = p.get('checkin') || ''; }
})().catch(e => mostrarAlerta(e.message));
