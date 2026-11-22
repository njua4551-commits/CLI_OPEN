# Fase 5 — Revisión y publicación aisladas

Verificado en CachyOS Linux x86_64 con OpenCode v2.3.2. El supervisor prepara una copia temporal con los archivos seleccionados y deja el original fuera del namespace. Usa `write` de OpenCode para crear o reemplazar archivos en esa copia. El proveedor simulado recibe propuestas explícitas y devuelve llamadas deterministas a la herramienta nativa. La validación posterior exige los bytes propuestos, el conjunto exacto de archivos y sintaxis JSON donde corresponda. La copia se descarta al finalizar, incluso si la edición quedó a medias o falló.

## Interfaz

```sh
python3 -I -B implementacion/supervisor review-workspace /ruta/al/proyecto < edits.json
python3 -I -B implementacion/supervisor apply-workspace /ruta/al/proyecto --approve HUELLA_DE_REVISION < edits.json
```

El archivo de entrada tiene la forma `{"edits":[{"operation":"create","path":"ejemplo.json","text":"{}"}]}`. Se admiten hasta ocho archivos UTF-8 de 64 KiB, del nivel superior, con extensión `.txt`, `.md` o `.json`. Los enlaces, rutas anidadas o absolutas, archivos especiales y operaciones ajenas al catálogo se rechazan.

La revisión devuelve diffs, commit base si existe y una huella vinculada al directorio, base Git, contenido y operaciones. Para descartar una propuesta, basta con omitir la aprobación. La aplicación exige repetir la solicitud, su validación y la huella exacta. Si el origen o su base cambiaron, la revisión caduca. Para los archivos afectados, Git comprueba que índice, árbol base y preimagen observada coincidan; se vuelve a comprobar el origen antes de publicar.

La aplicación crea un commit local en `refs/heads/cli-open/review-<huella>` dentro del repositorio original. Usa un índice temporal y publica la referencia en una transacción Git que verifica HEAD y exige que la referencia de revisión esté ausente. La rama activa, su índice y los archivos del árbol de trabajo conservan el estado del usuario. Un fallo puede dejar objetos Git sin referencia, pero la publicación de la rama es atómica. La integración a la rama activa es una operación Git posterior y explícita.

## Evidencia

- `python3 -I -B tests/fase5-review.py` usó la CLI compilada y Bubblewrap real. Creó y reemplazó archivos con la herramienta nativa, validó el diff, rechazó una aprobación obsoleta y publicó los dos archivos en la rama de revisión. Un segundo intento con la misma referencia no alteró el commit publicado. Un JSON inválido rechazó la copia y el original siguió intacto.
- `python3 -B -m unittest discover -s tests`: diez pruebas aprobadas, incluidas carreras deterministas de creación y reemplazo y diffs de archivos sin salto de línea final.
- El alcance calificado es la edición por propuestas explícitas con simulador, sin inferencia remota ni sesión abierta de escritura. PLAN y DIAG mantienen su separación. Las demás distribuciones y plataformas siguen pendientes.
