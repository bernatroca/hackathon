"""Genera una prova visual autònoma, exclusivament amb dades inventades."""
from pathlib import Path
import sys

ARREL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ARREL))
sys.path.insert(0, str(ARREL / 'app'))

from components.graella import Cella, CSS, CSS_FILTRES, filtres_html, taula_html, script_linies_html
from components.ajuda_part2 import CSS_GUIA, prova_guia_html


def setmana_inventada():
    """Cinc dies, subgrups simultanis dilluns i dimecres i tots els estats."""
    noms = (
        'Fonaments de Sistemes Distribuïts i Xarxes',
        'Disseny de Mecanismes i Materials Experimentals',
        'Models Matemàtics per a Enginys Sostenibles',
        'Arquitectures de Sensors i Comunicacions Òptiques',
        'Desenvolupament d’aplicacions per a Enginys Cooperatius',
        'Projectes de Robòtica i Fabricació Creativa',
        'Mètodes de Control per a Sistemes Autònoms',
    )
    return [Cella(
        id_sessio=f'INVENTADA-{i}', dia=dia, ini=570, fi=690,
        aula=f'Aula fictícia {i + 1}', assignatura=nom,
        tipus='Problemes' if dia in ('L', 'X') else 'Teoria',
        grup=f'PAUL/90{i}' if dia in ('L', 'X') else 'TE/99',
        canvi_franja=i == 2, canvi_aula=False,
        aula_assignada=i == 1,
        relaxacions=('Excepció fictícia per a la prova visual.',) if i == 4 else (),
    ) for i, (dia, nom) in enumerate(zip(('L', 'L', 'M', 'X', 'X', 'J', 'V'), noms))]


def genera():
    celles = setmana_inventada()
    casos = ''.join(
        f'<section class="prova" style="width:{ample}px"><h2>Contenidor de {ample} px</h2>'
        + filtres_html(celles)
        + taula_html(celles, 'Setmana inventada', estils=False)
        + '</section>' for ample in (887, 390))
    return '''<!doctype html>
<html lang="ca"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prova de la graella · dades inventades</title><style>
*{box-sizing:border-box}body{margin:0;padding:20px;background:#f4f3ef;color:#1a1a18;font:14px/1.4 system-ui}
.prova-menu{position:fixed;left:0;top:0;bottom:0;width:240px;padding:80px 20px;background:#fff;border-right:1px solid #e6e5e0;z-index:1000003}
.prova-obre-menu{position:fixed;top:12px;left:12px;z-index:1000004;background:white;border:1px solid #d4d3cd;border-radius:8px;padding:8px}
main{margin-left:240px;padding-top:24px;container:contingut / inline-size;min-width:0}
.menu-plegat .prova-menu{display:none}.menu-plegat main{margin-left:0;padding-top:64px}
.prova-panell{position:fixed;left:18px;bottom:84px;top:auto;right:auto;margin:0;max-width:calc(100vw - 36px);z-index:2147483647;padding:16px;background:#fff;border:1px solid #d4d3cd;border-radius:12px}
@media(max-width:700px){main{margin-left:0;padding-top:64px}.prova-menu{width:240px}}
h1{font-size:24px}h2{font-size:18px}.prova{max-width:100%;margin-bottom:40px}.p2-filtres{margin-bottom:12px}
''' + CSS + CSS_FILTRES + CSS_GUIA + '</style></head><body class="st-key-p2-pagina"><main id="prova-contingut"><h1>Horari proposat · prova visual</h1><p>Totes les classes, grups i aules són inventats.</p>' + casos + prova_guia_html() + '</main>' + script_linies_html() + '''
<script>
document.querySelectorAll('.prova').forEach(prova=>{
  prova.querySelectorAll('[data-filtre]').forEach(boto=>boto.onclick=()=>{
    prova.querySelectorAll('[data-filtre]').forEach(b=>b.setAttribute('aria-pressed',String(b===boto)));
    prova.querySelectorAll('.classe').forEach(c=>c.classList.toggle('apagada',boto.dataset.filtre!=='totes'&&c.dataset.estat!==boto.dataset.filtre));
  });
});
</script></body></html>'''


if __name__ == '__main__':
    desti = ARREL / 'docs' / 'disseny' / 'part2-prova-app.html'
    desti.write_text(genera(), encoding='utf-8')
    print('Prova HTML generada amb dades inventades.')
