const $ = id => document.getElementById(id);
const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
let quartos = [], reservas = [];
$('ano').value = new Date().getFullYear();

const ocupacao = (iso, q) => reservas.filter(r => r.status !== 'cancelada' && r.checkin <= iso && iso < r.checkout && (!q || r.quarto_id === q));
const nomeQuarto = id => (quartos.find(q => q.id === id) || {}).numero || '?';

function desenhar() {
    const ano = +$('ano').value, q = $('f-quarto').value, hoje = new Date().toISOString().slice(0, 10);
    $('legenda').innerHTML = q
        ? '<span><i style="background:#ef4444"></i>Reservado</span><span><i style="background:#fff;border:1px solid #cbd5e1"></i>Livre</span>'
        : '<span><i style="background:#fde68a"></i>Alguns quartos ocupados</span><span><i style="background:#ef4444"></i>Todos ocupados</span><span><i style="background:#fff;border:1px solid #cbd5e1"></i>Livre</span>';
    let h = '';
    for (let m = 0; m < 12; m++) {
        const dias = new Date(ano, m + 1, 0).getDate(), inicio = new Date(ano, m, 1).getDay();
        h += `<div class="mes-card"><h3>${MESES[m]}</h3><div class="mes-dias">${[...'DSTQQSS'].map(d => `<b>${d}</b>`).join('')}${'<span></span>'.repeat(inicio)}`;
        for (let d = 1; d <= dias; d++) {
            const iso = `${ano}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`, n = ocupacao(iso, q).length;
            const cls = n === 0 ? '' : (q || n >= quartos.length ? 'lotado' : 'parcial');
            h += `<button type="button" class="ad ${cls} ${iso === hoje ? 'hoje' : ''}" data-d="${iso}">${d}</button>`;
        }
        h += '</div></div>';
    }
    $('meses').innerHTML = h;
}

$('meses').addEventListener('click', e => {
    const b = e.target.closest('.ad'); if (!b) return;
    const iso = b.dataset.d, q = $('f-quarto').value, ocup = ocupacao(iso, q), usados = new Set(ocupacao(iso).map(r => r.quarto_id));
    const livres = quartos.filter(x => !usados.has(x.id)).map(x => esc(x.numero)).join(', ') || 'nenhum';
    $('detalhe').hidden = false;
    $('detalhe').innerHTML = `<strong>${dataBR(iso)}</strong>` + (ocup.length
        ? '<ul>' + ocup.map(r => `<li>Quarto <b>${esc(nomeQuarto(r.quarto_id))}</b>: ${esc(r.hospede)} · ${dataBR(r.checkin)} → ${dataBR(r.checkout)} · ${NOMES_ORIGEM[r.origem]} <a href="/reservas?editar=${r.id}">abrir</a></li>`).join('') + '</ul>'
        : '<p>Nenhuma reserva neste dia.</p>') + `<p>Quartos livres: ${livres}</p>`;
    $('detalhe').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
});

async function carregar() {
    try {
        [quartos, reservas] = await Promise.all([api('/api/quartos'), api('/api/reservas?ano=' + $('ano').value)]);
        if ($('f-quarto').options.length === 1) $('f-quarto').innerHTML += quartos.map(q => `<option value="${q.id}">Quarto ${esc(q.numero)}</option>`).join('');
        $('detalhe').hidden = true; desenhar();
    } catch (e) { mostrarAlerta(e.message); }
}
$('ano-ant').onclick = () => { $('ano').value--; carregar(); };
$('ano-prox').onclick = () => { $('ano').value++; carregar(); };
$('ano').onchange = carregar;
$('f-quarto').onchange = () => { $('detalhe').hidden = true; desenhar(); };
carregar();
