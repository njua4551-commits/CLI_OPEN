# Fase 5 — Revisión de ediciones aisladas

En CachyOS Linux x86_64, el supervisor acepta propuestas explícitas de creación y reemplazo en una copia temporal. El original se consulta por un descriptor de directorio abierto en solo lectura y queda fuera de los montajes del editor. Bubblewrap monta únicamente la copia para escritura, además del almacenamiento temporal privado del entorno.

```bash
printf '%s\n' '{"edits":[{"operation":"create","path":"ejemplo.json","text":"{}\n"}]}' |
  python3 -I -B implementacion/supervisor review-workspace /ruta/al/proyecto
```

La salida JSON `review-only` contiene los diffs unificados y los tipos de operación. Se admiten hasta ocho archivos UTF-8 de 64 KiB cada uno, en el nivel superior y con extensión `.txt`, `.md` o `.json`. Se rechazan rutas anidadas o absolutas, archivos ocultos, enlaces, archivos no regulares y operaciones distintas de creación o reemplazo. La única validación de formato adicional es sintaxis JSON. Los validadores corren dentro de Bubblewrap y carecen de comandos suministrados por el usuario.

Se comprueban identidad y metadatos del origen, además de los contenidos y las ausencias observadas. Si aparece una modificación concurrente, un error de edición, un timeout o una validación fallida, se descarta la copia. Una revisión exitosa también descarta la copia tras generar el diff. El supervisor carece de una operación para aplicar el diff al original. Si se incorpora integración en el futuro, deberá volver a comprobar la base en ese momento; el diff describe el estado observado durante la revisión.

## Evidencia y límite

- `python3 -I -B tests/fase5-review.py` pasó con Bubblewrap real. Creó y reemplazó archivos en la copia, verificó el diff, rechazó JSON inválido después de un cambio parcial en la copia y confirmó el original intacto.
- `python3 -B -m unittest discover -s tests` pasó nueve pruebas. Las carreras de creación y reemplazo se inyectaron de forma determinista. El contenido concurrente se conservó y la copia temporal se eliminó.
- El flujo utiliza un editor tipado de propuestas. Sigue pendiente conectar el modo de edición de OpenCode con esta misma transacción y comprobar la invocación de herramientas del agente. WORKSPACE de agente permanece deshabilitado y la condición para iniciar Fase 6 no se cumple.
