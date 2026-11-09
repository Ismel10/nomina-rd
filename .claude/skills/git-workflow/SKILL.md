---
name: git-workflow
description: Usar SIEMPRE antes de cualquier operación de Git o GitHub (crear o cambiar de rama, add, commit, push, pull, merge, tag; crear, editar o cerrar issues y PRs; etiquetas, milestones, releases) y al actualizar el CHANGELOG o registrar una decisión (ADR). Define el flujo issue → rama → commits → PR → CI → merge de este proyecto.
---

# Flujo de trabajo con Git y GitHub

Proyecto de **un solo desarrollador**, trabajado como si fuera un equipo: todo cambio nace en un
issue, se hace en una rama, entra a `main` por PR y deja rastro (etiquetas, CHANGELOG, ADR).

## Reglas de oro
1. `main` siempre en verde. **Nunca** se hace commit directo a `main` (única excepción: el commit
   inicial del repositorio).
2. **Sin issue no hay rama.** Si el usuario pide un cambio y no existe issue, propón el texto del
   issue (plantilla en `templates/`) antes de empezar.
3. **Pide confirmación** antes de: `git commit`, `git push`, `git merge`, `git tag`, crear o cerrar
   issues/PRs, crear etiquetas o releases. Muestra primero lo que vas a ejecutar.
4. Antes de cada `git add`, corre `git status` y revisa que no entren `.env`, `.venv/`, cachés
   (`.mypy_cache`, `.ruff_cache`, `__pycache__`, `node_modules`) ni datos reales. Agrega rutas
   concretas; evita `git add .` salvo que hayas revisado el `status`.
5. Prohibido: `push --force` a `main`, reescribir commits ya publicados, commitear secretos.
6. Si `gh` (GitHub CLI) no está instalado o autenticado, no improvises: dale al usuario el texto
   listo para pegar en la web de GitHub (título, cuerpo, etiquetas).

## Nombres
| Elemento | Formato | Ejemplo |
|---|---|---|
| Rama | `<tipo>/<n-issue>-<slug-corto>` | `feat/1-engine-money`, `fix/12-redondeo-negativos` |
| Commit | Conventional Commits con scope (AGENTS.md §6) | `feat(engine): agrega round_line` |
| Referencia | En el cuerpo del commit: `Refs #<n>` | `Refs #1` |
| PR | Mismo estilo que el commit + `Closes #<n>` / `Fixes #<n>` en la descripción | `feat(engine): utilidades de dinero` |

Tipos de rama: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`.

## Flujo de una tarea nueva (feature)
1. **Issue**: crea o localiza el issue con `templates/issue-feature.md`. Etiquetas: tipo + área.
   Asígnalo al milestone vigente (p. ej. `MVP`).
   `gh issue create --title "..." --body-file <archivo> --label feature,engine --milestone MVP`
2. **Contexto**: antes de programar, lee el issue, los ADR relacionados en `docs/decisiones/` y las
   entradas recientes del `CHANGELOG.md`.
3. **Rama** desde `main` actualizado:
   `git switch main` → `git pull` (si hay remoto) → `git switch -c feat/<n>-<slug>`
4. **Commits pequeños**, un tema cada uno, con tests en el mismo cambio. `Refs #<n>` en el cuerpo.
5. **Verificación local** (definición de "listo", AGENTS.md §5) antes de publicar.
6. **CHANGELOG / ADR** (ver abajo) en la misma rama.
7. **Push**: `git push -u origin <rama>`.
8. **PR** a `main` con `templates/pull-request.md`, mismas etiquetas y milestone que el issue:
   `gh pr create --base main --title "..." --body-file <archivo> --label ... --milestone MVP`
9. **CI** debe quedar en verde (`gh pr checks`). Si falla, se corrige en la misma rama.
10. **Autorrevisión**: el usuario lee el diff completo en GitHub. Resume tú los puntos que
    merecen atención (decisiones, riesgos, `TODO(verificar-normativa)`).
11. **Merge** (solo con aprobación del usuario): squash y borrar rama.
    `gh pr merge <n> --squash --delete-branch` → `git switch main` → `git pull`.
    El issue se cierra solo gracias a `Closes #<n>`.

## Flujo de un bug
1. Issue con `templates/issue-bug.md`, etiqueta `bug` + área (y `priority:high` si afecta montos).
2. Rama `fix/<n>-<slug>`.
3. **Primero** un commit con el test que reproduce el bug (debe fallar): `test(<área>): reproduce #<n>`.
4. Después el commit con la corrección: `fix(<área>): ...`.
5. PR con `Fixes #<n>`, CHANGELOG en "Corregido", CI verde, merge.

## Etiquetas y milestones
Lista oficial y comandos para crearlas en `templates/labels.md`. Reglas:
- Todo issue y PR lleva **1 etiqueta de tipo** y **al menos 1 de área**.
- `blocked` / `needs-normativa`: el trabajo espera algo externo (p. ej. escala ISR de la DGII).
  Indica en el issue qué falta y quién lo aporta.
- Un milestone por fase (`MVP`, `Fase 2 - Asistencia`, …).

## Historial de contexto
- **`CHANGELOG.md`** (formato Keep a Changelog, en español): cada PR que cambie algo visible o de
  comportamiento agrega una línea en `## [Sin publicar]`, bajo `Agregado`, `Cambiado`, `Corregido`
  o `Eliminado`, con el número del PR o issue. Si el archivo no existe, créalo con
  `templates/changelog.md`.
- **ADR** (`docs/decisiones/NNNN-titulo.md`, plantilla `templates/adr.md`): crea uno cuando se
  tome una decisión de diseño o normativa que alguien podría cuestionar después (criterio de
  redondeo, estructura de tablas, una librería). Numeración consecutiva; un ADR aceptado no se
  edita: se crea otro que lo reemplace.
- Los PR enlazan su issue y sus ADR; así el historial queda trazable de punta a punta.

## Versiones (releases)
Al completar un milestone, con aprobación del usuario: mover `[Sin publicar]` a una versión
SemVer (`0.1.0`, `0.2.0`, …) con fecha, crear el tag `v0.x.0` y la release:
`git tag -a v0.1.0 -m "..."` → `git push origin v0.1.0` → `gh release create v0.1.0 --notes-file ...`

## Al terminar cualquier operación
Reporta al usuario: rama actual, commits creados, qué se publicó (push/PR/issue con su número y
enlace) y qué queda pendiente de su aprobación.
