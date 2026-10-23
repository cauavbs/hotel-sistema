const $ = id => document.getElementById(id);
$('pessoais').onchange = () => { $('l-reservas').href = '/api/exportar/reservas.csv' + ($('pessoais').checked ? '?pessoais=1' : ''); };
$('limpar').onclick = async () => {
    if (!await mostrarConfirmacao('Apagar os comprovantes sem uso? Não dá para desfazer.')) return;
    try { const r = await api('/api/manutencao/comprovantes-orfaos', { method: 'POST' }); mostrarAlerta(`${r.removidos} comprovante(s) apagado(s). ${r.recentes_mantidos} recente(s) mantido(s).`); }
    catch (e) { mostrarAlerta(e.message); }
};
