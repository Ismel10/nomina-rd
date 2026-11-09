# Etiquetas del proyecto

| Etiqueta | Color | Uso |
|---|---|---|
| `feature` | `1D76DB` | Funcionalidad nueva |
| `bug` | `D73A4A` | Algo no funciona como debería |
| `test` | `BFD4F2` | Solo tests |
| `docs` | `0075CA` | Documentación, ADR, CHANGELOG |
| `chore` | `C5DEF5` | Mantenimiento, configuración, CI, dependencias |
| `refactor` | `FBCA04` | Cambio interno sin cambiar comportamiento |
| `engine` | `5319E7` | Motor de cálculo |
| `api` | `0E8A16` | Endpoints FastAPI |
| `db` | `006B75` | Modelos, migraciones, persistencia |
| `frontend` | `F9D0C4` | SPA React |
| `documents` | `C2E0C6` | PDF y archivos de dispersión |
| `blocked` | `B60205` | Espera algo externo |
| `needs-normativa` | `E99695` | Falta una fuente legal (TSS, DGII, Código de Trabajo) |
| `priority:high` | `B60205` | Afecta montos o datos; atender primero |

## Crear todas con GitHub CLI (pedir confirmación antes)
```bash
gh label create feature        --color 1D76DB --description "Funcionalidad nueva" --force
gh label create bug            --color D73A4A --description "Algo no funciona como debería" --force
gh label create test           --color BFD4F2 --description "Solo tests" --force
gh label create docs           --color 0075CA --description "Documentación, ADR, CHANGELOG" --force
gh label create chore          --color C5DEF5 --description "Mantenimiento, configuración, CI" --force
gh label create refactor       --color FBCA04 --description "Cambio interno sin cambiar comportamiento" --force
gh label create engine         --color 5319E7 --description "Motor de cálculo" --force
gh label create api            --color 0E8A16 --description "Endpoints FastAPI" --force
gh label create db             --color 006B75 --description "Modelos, migraciones, persistencia" --force
gh label create frontend       --color F9D0C4 --description "SPA React" --force
gh label create documents      --color C2E0C6 --description "PDF y archivos de dispersión" --force
gh label create blocked        --color B60205 --description "Espera algo externo" --force
gh label create needs-normativa --color E99695 --description "Falta una fuente legal" --force
gh label create "priority:high" --color B60205 --description "Afecta montos o datos" --force
gh api repos/{owner}/{repo}/milestones -f title="MVP"
```
