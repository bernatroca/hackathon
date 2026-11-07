SELECT id_sessio, setmana, tipus, alumnes, durada_min
FROM grau_nou WHERE sem=$semestre AND ($setmana IS NULL OR setmana=$setmana)
ORDER BY id_sessio
