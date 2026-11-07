// Utilidades e comportamento comum: sidebar, logout, service worker.
window.esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
window.brl = v => (v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
window.dataBR = iso => (iso || '').split('-').reverse().join('/');
window.hojeLocal = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
window.mesAtual = () => hojeLocal().slice(0, 7);
window.somarDias = (iso, n) => { const [a, m, d] = iso.split('-').map(Number), x = new Date(a, m - 1, d + n); return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`; };
// Impede o duplo clique: o botão do formulário fica desabilitado até o envio terminar.
window.comTrava = async (e, fn) => {
    e.preventDefault();
    const b = e.target.querySelector('button[type=submit], button:not([type])');
    if (b && b.disabled) return;
    if (b) b.disabled = true;
    try { await fn(); } finally { if (b) b.disabled = false; }
};
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

// ---- Comprovantes: reduz imagens no celular e envia ao servidor ----
window.enviarComprovante = file => new Promise((ok, falha) => {
    const enviar = (nome, tipo, dados) => api('/api/comprovantes', { method: 'POST', body: JSON.stringify({ nome, tipo, dados }) }).then(ok, falha);
    if (file.type === 'application/pdf') {
        if (file.size > 1000000) return falha(new Error('PDF acima de 1 MB. Reduza o arquivo ou tire uma foto.'));
        const r = new FileReader(); r.onload = () => enviar(file.name, file.type, r.result.split(',')[1]); return r.readAsDataURL(file);
    }
    if (!file.type.startsWith('image/')) return falha(new Error('Envie uma imagem ou um PDF.'));
    const img = new Image();
    img.onload = () => {
        const f = Math.min(1, 1600 / Math.max(img.width, img.height)), c = document.createElement('canvas');
        c.width = Math.round(img.width * f); c.height = Math.round(img.height * f);
        c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(img.src);
        enviar(file.name.replace(/\.\w+$/, '') + '.jpg', 'image/jpeg', c.toDataURL('image/jpeg', 0.75).split(',')[1]);
    };
    img.onerror = () => falha(new Error('Não foi possível ler esta imagem.'));
    img.src = URL.createObjectURL(file);
});
window.linkComprovante = (id, nome) => id ? `<a href="/api/comprovantes/${esc(id)}" target="_blank" rel="noopener">📎 ${esc(nome || 'Ver')}</a>` : '';
window.fmtCPF = v => String(v || '').replace(/\D/g, '').slice(0, 11)
    .replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
window.mascaraCPF = el => el.addEventListener('input', () => { el.value = fmtCPF(el.value); });
