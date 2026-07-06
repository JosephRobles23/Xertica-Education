# Kickoffs por dev

Guías de arranque: **cómo desarrollar tus primeras tareas usando las 12 skills agénticas**, con el concepto e importancia de cada una, en el orden en que las necesitas. Son la aplicación práctica del pipeline descrito en [`Skills_Desarrollo_Agentico.md`](../../../Documents/Skills/Skills_Desarrollo_Agentico.md) §6, personalizada por dev.

| Dev | Feature | Primeras tareas | Kickoff |
| :-- | :-- | :-- | :-- |
| **Arantza** | Sourcing / Deep Research | Contexto del Cliente (#16) · Spike Deep Research (#17) | [arantza-kickoff.md](arantza-kickoff.md) |
| **Joseph** | Knowledge Base / Integraciones | Google Drive (#18) · Quick wins descargas (#19) | [joseph-kickoff.md](joseph-kickoff.md) |
| **Sebas** | Video | Spike video largo (#21) · Reutilización de videos (#20) | [sebas-kickoff.md](sebas-kickoff.md) |
| **Santiago** | Infografía | Pipeline de infografía (#13) | [santiago-kickoff.md](santiago-kickoff.md) |

Tareas: [`docs/backlog.md`](../backlog.md) · cruces de arquitectura: [`architecture.md`](../arquitectura/architecture.md) §14.

## El pipeline en una línea
```
/decision-mapping → /grill-with-docs → /prototype → /to-prd → /to-issues → /tdd + /ponytail → /ponytail-review
```
- **Spikes** (research) usan sobre todo `/decision-mapping` + `/prototype` + `/grill-with-docs` (→ ADR).
- **Features** (build) recorren el pipeline completo.
- `/ponytail` está **siempre activo** durante la implementación; `/domain-modeling` se activa dentro de `/grill-with-docs`.

> **Nota sobre los ADR:** los números de ADR en los ejemplos (p. ej. "ADR-0006") son **ilustrativos**. El siguiente número real se asigna secuencialmente al crearlo — hoy el próximo disponible es **0006** (ver [`docs/adr/`](../adr/)). Si varias tareas generan ADRs, se numeran 0006, 0007, 0008… en orden de creación.
