Closes #<n>   <!-- usar "Fixes #<n>" si es un bug -->

## Qué cambia
- ...

## Por qué
<!-- Enlace a ADR si aplica: docs/decisiones/NNNN-... -->

## Cómo se probó
- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `mypy`
- [ ] `pytest` (resultado: ...)
- [ ] Frontend (si aplica): `npm run lint`, `npm run typecheck`, `npm test`

## Checklist
- [ ] Tests en el mismo cambio (bug: test que lo reproduce primero).
- [ ] `CHANGELOG.md` actualizado en `[Sin publicar]`.
- [ ] Glosario / AGENTS.md actualizados si cambió el dominio o las reglas.
- [ ] Sin datos sensibles ni `.env` en el diff.
- [ ] Puntos a revisar con atención: ...
