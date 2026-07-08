# AGENTS.md — Reglas y skills para agentes (cross-tool)

> **Fuente de verdad SIEMPRE ACTIVA** para cualquier asistente de IA que trabaje en este
> repo: **Claude Code · OpenAI Codex · Cursor · Google Antigravity**.
> Léelo completo antes de actuar y aplícalo en cada turno.

## 0. Cómo cada herramienta consume este archivo

| Herramienta | Reglas siempre activas | Skills |
| :-- | :-- | :-- |
| **Codex** | lee `AGENTS.md` nativo | vía el *protocolo de skills* (§2) |
| **Cursor** | `AGENTS.md` + `.cursor/rules/always.mdc` (`alwaysApply`) | protocolo (§2) o `.cursor/commands/` |
| **Antigravity** | lee `AGENTS.md` nativo | protocolo (§2) + `.agents/skills/` |
| **Claude Code** | `CLAUDE.md` importa este archivo (`@AGENTS.md`) | `.claude/skills/` nativo + protocolo (§2) |

Una sola fuente de verdad; sin duplicar skills por herramienta.

---

## 1. Reglas siempre activas

1. **Contexto primero.** Antes de explorar o tocar código, lee `xertica-education/CONTEXT.md`
   (dominio y glosario) y los ADRs en `xertica-education/docs/adr/`. Usa el vocabulario del
   glosario; no derives a sinónimos.
2. **Mocks-first, de izquierda a derecha.** `Contracts → Models → Endpoints → Frontend → IA real`.
   Primero el esqueleto determinista con mocks; la IA real al final. Ningún feature bloquea a otro:
   si una dependencia no está lista, devuelve un mock que **cumpla el contrato**.
3. **No cambies un contrato de API** (DTO/endpoint) sin acordarlo primero. La implementación
   interna detrás de un contrato existente es libre.
4. **Decisiones difíciles de revertir → ADR.** Si algo es irreversible en la práctica,
   sorprendente y fruto de un trade-off, regístralo como ADR (numerado) antes de codificarlo.
   Si algo contradice un ADR, **decláralo explícitamente**, no lo sobrescribas en silencio.
5. **TDD + minimalismo.** Implementa con ciclos red-green y la solución más simple que funcione
   (stdlib antes que dependencias; ver skills `/tdd` y `/ponytail`).
6. **Higiene de secretos.** Nunca commitees `.env`/claves. Usa rutas explícitas al hacer `git add`.
   No hagas `push` ni acciones externas sin que el usuario lo pida.
7. **Reporta con honestidad.** Si un test falla o un paso se omitió, dilo con la evidencia.

---

## 2. Protocolo de skills (funciona en las 4 herramientas)

Hay una **librería de skills reutilizables** versionada en el repo. Cuando el usuario:
- escriba **`/<nombre>`** (p. ej. `/tdd`, `/grill-with-docs`, `/ponytail`), o
- pida una skill por su nombre o su propósito,

**DEBES**: localizar su `SKILL.md`, leerlo y **seguirlo al pie de la letra** como si sus
instrucciones fueran tuyas. Lo que el usuario ponga tras el comando son sus `ARGUMENTS`.

**Dónde buscar** (revisa el nombre en ambas ubicaciones):
- `.claude/skills/<nombre>/SKILL.md`
- `.agents/skills/<nombre>/SKILL.md`

Si el `SKILL.md` menciona archivos de apoyo en su carpeta (referencias, plantillas), léelos también.

**Notas por herramienta:**
- *Claude Code* ya carga `.claude/skills/` de forma nativa (además de este protocolo).
- *Codex* (opcional): para tener el slash nativo, copia el cuerpo de un `SKILL.md` a
  `~/.codex/prompts/<nombre>.md` (sin el frontmatter YAML).
- *Cursor* (opcional): puedes espejar una skill como `.cursor/commands/<nombre>.md`.

---

## 3. Índice de skills

### Metodología de ingeniería (flujo agéntico)
| Skill | Qué hace | Carpeta |
| :-- | :-- | :-- |
| `decision-mapping` | Convierte una idea difusa en un mapa de tickets y los resuelve uno a uno. | `.claude` |
| `grilling` / `grill-me` | Entrevista implacable para validar/afilar un plan o diseño. | `.claude` / `.agents` |
| `grill-with-docs` | Grilling que además crea ADRs y glosario sobre la marcha. | `.claude` |
| `domain-modeling` | Construye y afila el modelo de dominio y el glosario. | `.claude` |
| `to-prd` | Sintetiza la conversación en un PRD. | `.claude` / `.agents` |
| `to-issues` | Rompe un plan/PRD en issues vertical-slice (tracer bullets). | `.claude` / `.agents` |
| `implement` | Implementa trabajo a partir de un PRD o issues. | `.agents` |
| `tdd` | Red-green-refactor para features y bugs. | `.claude` / `.agents` |
| `ponytail` | Modo minimalista: la solución más simple que funcione. | `.claude` |
| `ponytail-review` | Revisa diffs exclusivamente por over-engineering. | `.claude` |
| `code-review` | Revisa cambios desde un punto fijo por Standards + Spec. | `.agents` |
| `prototype` | Código desechable para responder una pregunta (lógica o variaciones de UI). | `.claude` |
| `improve-architecture` / `improve-codebase-architecture` | Escanea el código por oportunidades (reporte HTML) y grillea la elegida. | `.claude` / `.agents` |
| `code-comments` | Comentarios y documentación claros, junto al código. | `.agents` |
| `handoff` | Compacta la conversación en un documento de traspaso. | `.agents` |
| `setup-matt-pocock-skills` | Configura el repo para las skills de ingeniería (tracker, labels, domain). | `.agents` |

### Diseño de producto / UI
| Skill | Qué hace | Carpeta |
| :-- | :-- | :-- |
| `frontend-design` | Interfaces frontend de alta calidad, sin estética genérica de IA. | `.claude` |
| `ui-ux-pro-max` | Inteligencia de diseño UI/UX (estilos, paletas, componentes, stacks). | `.claude` |

### Utilidades
| Skill | Qué hace | Carpeta |
| :-- | :-- | :-- |
| `teach` | Enseña un concepto con lecciones HTML interactivas. | `.claude` |
| `caveman` | Modo de comunicación ultra-comprimida (menos tokens, misma precisión). | `.agents` |

> Cuando una skill existe en ambas carpetas (p. ej. `tdd`, `to-issues`, `to-prd`), la
> versión `.claude` suele publicar en Linear y la `.agents` en un issue tracker genérico:
> usa la que corresponda a tu herramienta/tracker.

---

## 4. Punteros del proyecto

- `xertica-education/CONTEXT.md` — dominio único y glosario (**leer primero**).
- `xertica-education/AGENTS.md` — protocolo multi-desarrollador y matriz de ownership de archivos.
- `xertica-education/docs/adr/` — decisiones de arquitectura (ADRs).
- `xertica-education/docs/dev/` — kickoffs por desarrollador (flujo con skills).
- `xertica-education/docs/decisions/` — mapas de decisiones de features.
