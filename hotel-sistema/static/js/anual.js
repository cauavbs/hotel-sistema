const $ = id => document.getElementById(id);
const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
let quartos = [], reservas = [], bloqueios = [];
$('ano').value = new Date().getFullYear();
const nomeQ = id => (quartos.find(q => q.id === id) || {}).numero || '?';

// Situação de um dia para todos os quartos (ou só o quarto escolhido no filtro).
// Quarto bloqueado conta como indisponível, igual a quarto reservado.
function estado(iso, q) {
    const qs = q ? quartos.filter(x => x.id === q) : quartos, ids = new Set(qs.map(x => x.id));
    const res = reservas.filter(r => r.status !== 'cancelada' && r.checkin <= iso && iso < r.checkout && ids.has(r.quarto_id));
    const blq = bloqueios.filter(b => b.inicio <= iso && iso < b.fim && ids.has(b.quarto_id));
    const usados = new Set([...res.map(r => r.quarto_id), ...blq.map(b => b.quarto_id)]);
    return { res, blq, livres: qs.filter(x => !usados.has(x.id)), n: usados.size, total: qs.length };
}

function desenhar() {
    const ano = +$('ano').value, q = $('f-quarto').value, hoje = hojeLocal();
    $('legenda').innerHTML = q
        ? '<span><i style="background:#ef4444"></i>Reservado ou bloqueado</span><span><i style="background:#fff;border:1px solid #cbd5e1"></i>Livre</span>'
        : '<span><i style="background:#fde68a"></i>Alguns quartos ocupados</span><span><i style="background:#ef4444"></i>Todos ocupados</span><span><i style="background:#fff;border:1px solid #cbd5e1"></i>Livre</span>';
    let h = '';
    for (let m = 0; m < 12; m++) {
        const dias = new Date(ano, m + 1, 0).getDate(), inicio = new Date(ano, m, 1).getDay();
        h += `<div class="mes-card"><h3>${MESES[m]}</h3><div class="mes-dias">${[...'DSTQQSS'].map(d => `<b>${d}</b>`).join('')}${'<span></span>'.repeat(inicio)}`;
        for (let d = 1; d <= dias; d++) {
            const iso = `${ano}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`, e = estado(iso, q);
            const cls = e.n === 0 ? '' : (e.livres.length === 0 ? 'lotado' : 'parcial');
            h += `<button type="button" class="ad ${cls} ${iso === hoje ? 'hoje' : ''}" data-d="${iso}">${d}</button>`;
        }
        h += '</div></div>';
    }
    $('meses').innerHTML = h;
}

const novaReserva = (iso, livre) => `/reservas?quarto=${livre.id}&checkin=${iso}&checkout=${somarDias(iso, 1)}`;

// O que acontece ao tocar num dia:
//  - livre em todos os quartos  -> nova reserva (já no primeiro quarto livre)
//  - todos os quartos ocupados  -> reservas daquele dia (ou a reserva do quarto filtrado)
//  - parcialmente ocupado       -> escolha: nova reserva neste dia ou ver os quartos ocupados
$('meses').addEventListener('click', e => {
    const b = e.target.closest('.ad'); if (!b) return;
    const iso = b.dataset.d, q = $('f-quarto').value, s = estado(iso, q);
    $('detalhe').hidden = true;
    if (!s.total) return mostrarAlerta('Cadastre os quartos primeiro (menu Quartos e Bloqueios).');
    if (s.n === 0) { location.href = novaReserva(iso, s.livres[0]); return; }
    if (s.livres.length === 0) {
        if (!s.res.length) { location.href = '/quartos#bloqueios'; return; }          // só bloqueios
        location.href = q ? `/reservas?editar=${s.res[0].id}` : `/reservas?dia=${iso}`;
        return;
    }
    const ocupados = [...s.res.map(r => `<li>Quarto <b>${esc(nomeQ(r.quarto_id))}</b>: ${esc(r.hospede)} · ${dataBR(r.checkin)} → ${dataBR(r.checkout)} · ${NOMES_ORIGEM[r.origem]}</li>`),
        ...s.blq.map(x => `<li>Quarto <b>${esc(nomeQ(x.quarto_id))}</b>: bloqueado (${esc(x.motivo_texto)})</li>`)].join('');
    $('detalhe').hidden = false;
    $('detalhe').innerHTML = `<strong>${dataBR(iso)}</strong> · ${s.n} de ${s.total} quartos ocupados<ul>${ocupados}</ul>
        <p>Livres: ${s.livres.map(x => esc(x.numero)).join(', ')}</p>
        <a class="btn-link" href="${novaReserva(iso, s.livres[0])}">➕ Nova reserva neste dia</a>
        <a class="btn-link sec" href="${s.res.length ? '/reservas?dia=' + iso : '/quartos#bloqueios'}">🛏️ Ver quartos ocupados</a>`;
    $('detalhe').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
});

async function carregar() {
    try {
        [quartos, reservas, bloqueios] = await Promise.all([api('/api/quartos'), api('/api/reservas?ano=' + $('ano').value), api('/api/indisponiveis?ano=' + $('ano').value)]);
        if ($('f-quarto').options.length === 1) $('f-quarto').innerHTML += quartos.map(q => `<option value="${q.id}">Quarto ${esc(q.numero)}</option>`).join('');
        $('detalhe').hidden = true; desenhar();
    } catch (e) { mostrarAlerta(e.message); }
}
$('ano-ant').onclick = () => { $('ano').value--; carregar(); };
$('ano-prox').onclick = () => { $('ano').value++; carregar(); };
$('ano').onchange = carregar;
$('f-quarto').onchange = () => { $('detalhe').hidden = true; desenhar(); };
carregar();
