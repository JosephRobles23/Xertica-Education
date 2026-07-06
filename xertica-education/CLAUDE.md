# CLAUDE.md — Guía operativa para Claude Code

Guía para trabajar en el monorepo **Xertica Education**. Antes de explorar o editar dominio, lee **`CONTEXT.md`** (lenguaje ubicuo, gates, invariantes). Para el protocolo multi-desarrollador y la matriz de propiedad de archivos, lee **`AGENTS.md`** — es de cumplimiento obligatorio.

---

## Stack real (fuente de verdad = el código, no el README)

| Parte | Tecnología |
| :--- | :--- |
| Monorepo | npm workspaces + **Turborepo** (`turbo.json`) |
| `apps/web` | **Vite 5 + React 18 + TypeScript + React Router 6 + Tailwind 4 + Radix UI** (estilo shadcn/ui) |
| `apps/api` | **FastAPI (Python)** gestionado con **`uv`** |

> ⚠️ El `README.md` dice "Next.js 15 App Router" y `pip/venv` — **está desactualizado**. No lo tomes como referencia de stack; ver `CONTEXT.md` §6.

---

## Comandos

Desde la raíz del monorepo (`xertica-education/`):

```bash
npm install            # instala workspaces
npm run dev            # turbo dev (levanta apps)
npm run build          # turbo build
npm run lint           # turbo lint
```

Frontend (`apps/web/`):

```bash
npm run dev --workspace=xertica-education-web   # Vite dev server
npm run build          # tsc --noEmit && vite build
npm run typecheck      # tsc --noEmit
```

Backend (`apps/api/`) — usa **uv**, no venv+pip:

```bash
uv run uvicorn main:app --reload --port 8000    # dev (npm run dev)
uv run uvicorn main:app --host 0.0.0.0 --port 8000   # start
python verify_boot.py                            # smoke test de arranque
```

La API corre en `http://localhost:8000`; el frontend espera esa URL (fallback en `apps/web/src/lib/api.ts`).

---

## Estructura

```
xertica-education/
├── apps/
│   ├── web/          Vite + React SPA
│   │   └── src/{pages,components,lib,data,store.tsx}
│   └── api/          FastAPI
│       ├── routers/        rutas HTTP (jobs, learning_paths)
│       ├── services/       capacidades de negocio (route, jobs, video, workflow)
│       ├── repositories/   persistencia
│       ├── models/         domain/ (negocio) + dto/ (contratos HTTP)
│       ├── adapters/       llm/ storage/ parser/ renderer/
│       └── config/         settings.py (pydantic-settings), dependencies.py (DI)
├── docs/             backlog, issues (15 slices), prd, adr, agents
├── CONTEXT.md        modelo de dominio (leer primero)
├── AGENTS.md         protocolo multi-desarrollador (obligatorio)
└── README.md         puesta en marcha (parcialmente desactualizado)
```

---

## Convenciones al escribir código

1. **Reglas de oro del MVP** (ver `CONTEXT.md` §5): ninguna feature bloquea a otra → usa `mock.py` que cumpla el contrato; no cambies un contrato de API sin discutirlo; construye **de izquierda a derecha** (`Contracts → Models → Endpoints → Frontend → IA real`).
2. **Patrón de servicio backend**: cada servicio tiene `interface.py` + `service.py` + `mock.py`. Mantén los servicios deterministas y los prompts locales a la carpeta del servicio.
3. **Modelos**: separa `models/domain/` de `models/dto/`. No filtres modelos de dominio en respuestas HTTP.
4. **Frontend**: cliente HTTP centralizado en `src/lib/api.ts`; trabajo pesado se consulta por *polling* de jobs. Tipos en `src/lib/types.ts`. Alias de import `@/` → `src/`.
5. **Vocabulario**: usa los términos de `CONTEXT.md` (Ruta, Gate, Job, KB, Componente, Asset). No inventes sinónimos.
6. Al terminar cambios de frontend corre `npm run typecheck`; para el backend, `python verify_boot.py`.

---

## Protocolo de agentes (resumen — el detalle está en `AGENTS.md`)

- Al iniciar, lee `.agents/identity.json` (gitignored) para saber qué desarrollador representas. Si no existe, pide crearlo desde `identity.json.example`.
- **Solo puedes editar** los archivos dentro del *scope* de tu desarrollador activo o carpetas *Shared* (ej. `apps/web/` general, `docs/`). Para modificar fuera de scope, **pausa y pide confirmación explícita**.
- Puedes **leer** cualquier archivo del workspace.
- Issues se llevan como markdown local bajo `.scratch/<developer>/`, no como PRs externos.

---

## Antes de dar por terminado

- ¿El cambio respeta el contrato de API existente? Si tuvo que cambiar el contrato, ¿lo discutiste?
- ¿Corriste `typecheck` (web) / `verify_boot.py` (api)?
- ¿El código está dentro de tu scope de `AGENTS.md`?
- ¿Usaste el vocabulario de `CONTEXT.md`?
