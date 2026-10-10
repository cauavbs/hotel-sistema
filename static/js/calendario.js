const mesEl = document.getElementById('mes'), box = document.getElementById('cal-box');
mesEl.value = mesAtual();
const DIA = 'DSTQQSS';

function somarMes(n) {
    const [a, m] = mesEl.value.split('-').map(Number), d = new Date(a, m - 1 + n, 1);
    mesEl.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    carregar();
}

async function carregar() {
    try {
        const [quartos, reservas] = await Promise.all([api('/api/quartos'), api('/api/reservas?mes=' + mesEl.value)]);
        const [a, m] = mesEl.value.split('-').map(Number), dias = new Date(a, m, 0).getDate();
        const hoje = new Date().toISOString().slice(0, 10), pad = d => `${mesEl.value}-${String(d).padStart(2, '0')}`;
        const fimMes = pad(dias);
        let h = '<thead><tr><th class="q">Quarto</th>';
        for (let d = 1; d <= dias; d++) {
            const dow = new Date(a, m - 1, d).getDay();
            h += `<th class="${pad(d) === hoje ? 'hoje' : ''} ${dow % 6 === 0 ? 'fds' : ''}" ${pad(d) === hoje ? 'id="col-hoje"' : ''}>${d}<small>${DIA[dow]}</small></th>`;
        }
        h += '</tr></thead><tbody>';
        for (const q of quartos) {
            h += `<tr><th class="q">${esc(q.numero)}</th>`;
            for (let d = 1; d <= dias;) {
                const iso = pad(d);
                const r = reservas.find(r => r.quarto_id === q.id && r.status !== 'cancelada' && r.checkin <= iso && iso < r.checkout);
                if (r) {
                    // uma célula única cobrindo todas as noites da reserva dentro do mês
                    const ultimo = r.checkout > fimMes ? dias : Number(r.checkout.slice(8)) - 1;
                    const span = Math.max(1, ultimo - d + 1);
                    h += `<td class="dia ${r.origem} ${r.situacao !== 'pago' ? 'pendente' : ''}" colspan="${span}" data-r="${r.id}" title="${esc(r.hospede)} · ${dataBR(r.checkin)} a ${dataBR(r.checkout)} · ${NOMES_ORIGEM[r.origem]} · ${r.situacao}"><span>${esc(r.hospede.split(' ')[0])}</span></td>`;
                    d += span;
                } else {
                    h += `<td class="dia" data-q="${q.id}" data-d="${iso}"></td>`;
                    d++;
                }
            }
            h += '</tr>';
        }
        document.getElementById('tabela').innerHTML = quartos.length ? h + '</tbody>' : '<tr><td>Cadastre os quartos primeiro (menu Quartos).</td></tr>';
        const col = document.getElementById('col-hoje');   // rola até o dia de hoje
        box.scrollLeft = col ? Math.max(0, col.offsetLeft - 90) : 0;
    } catch (e) { mostrarAlerta(e.message); }
}

document.getElementById('tabela').addEventListener('click', e => {
    const td = e.target.closest('td.dia');
    if (!td) return;
    location.href = td.dataset.r ? `/reservas?editar=${td.dataset.r}` : `/reservas?quarto=${td.dataset.q}&checkin=${td.dataset.d}`;
});
document.getElementById('mes-ant').onclick = () => somarMes(-1);
document.getElementById('mes-prox').onclick = () => somarMes(1);
document.getElementById('mes-hoje').onclick = () => { mesEl.value = mesAtual(); carregar(); };
mesEl.onchange = carregar;
carregar();
