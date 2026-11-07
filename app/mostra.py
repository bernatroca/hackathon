"""Valors ficticis escrits a mà, exclusivament per provar la interfície."""
import pandas as pd
from nivell1.troballes import Troballa


def exemples():
    resultat = {}
    for id_, titol, xifra, grafic, dades in [
        ('hi-cap-mati', 'Hi cap el matí?', '12 de 19', 'linia', {'etiqueta': ['08:30', '09:00'], 'classes': [8, 12]}),
        ('fora-torn', 'Quantes sessions queden fora de torn?', '120', 'barres', {'torn': ['Matí', 'Tarda'], 'sessions': [70, 50]}),
        ('hores-aula', "Quanta demanda d'aulari hi ha?", '60 %', 'barres', {'franja': ['Matí', 'Tarda'], 'hores': [60, 40]}),
        ('aforament', 'On falten places?', '8', 'barres', {'aula': ['Aula A', 'Aula B'], 'sessions': [5, 3]}),
        ('ocupacio', "Com s'ocupen els espais?", '55 %', 'heatmap', {'aula': ['Aula A', 'Aula A', 'sense aula'], 'dia': ['Dilluns'] * 3, 'etiqueta': ['08:30', '09:00', '08:30'], 'valor': [1, 0, 2]}),
    ]:
        resultat[id_] = Troballa(id=id_, titol=titol, xifra=xifra,
            frase='MOSTRA · Exemple fictici de presentació; no és un resultat del repte.',
            metode="MOSTRA: dades escrites a mà per provar la interfície. No s'ha executat cap consulta.",
            sql='-- MOSTRA: no hi ha cap consulta executada.', taula=pd.DataFrame(dades),
            grafic=grafic, extra={'mostra': True})
    resultat['hi-cap-mati'].extra.update(
        pic=[{'dia': 'Dilluns', 'etiqueta': '08:30', 'classes': 8}, {'dia': 'Dilluns', 'etiqueta': '09:00', 'classes': 12}],
        per_mida=[{'llindar': 48, 'demanda_h': 80, 'oferta_h': 100, 'oferta_h_amb_seminaris': 120, 'falla': False},
                  {'llindar': 100, 'demanda_h': 45, 'oferta_h': 40, 'oferta_h_amb_seminaris': 40, 'falla': True}])
    return resultat
