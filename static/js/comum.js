// Utilidades e comportamento comum: sidebar, logout, service worker.
window.esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
window.brl = v => (v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
window.dataBR = iso => (iso || '').split('-').reverse().join('/');
window.mesAtual = () => new Date().toISOString().slice(0, 7);
window.NOMES_ORIGEM = { direto: 'Direto', airbnb: 'Airbnb', booking: 'Booking' };
window.api = async (url, opts = {}) => {
    const r = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.erro || 'Erro inesperado.');
    return d;
};
document.addEventListener('DOMContentLoaded', () => {
    const sb = document.getElementById('sidebar'), ov = document.getElementById('overlay');
    const fechar = () => { sb.classList.remove('open'); ov.classList.remove('active'); };
    document.getElementById('btn-toggle-sidebar').onclick = () => { sb.classList.add('open'); ov.classList.add('active'); };
    document.getElementById('btn-close-sidebar').onclick = fechar;
    ov.onclick = fechar;
    document.getElementById('btn-sair').onclick = () => { location.href = '/logout'; };
});
if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => { }));
