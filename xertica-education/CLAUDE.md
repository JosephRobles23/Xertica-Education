# CLAUDE.md — Guía operativa para Claude Code

Guía para trabajar en el monorepo **Xertica Education**. Antes de explorar o editar dominio, lee **`CONTEXT.md`** (lenguaje ubicuo, gates, invariantes). Para el protocolo multi-desarrollador y la matriz de propiedad de archivos, lee **`AGENTS.md`** — es de cumplimiento obligatorio.

---

## Stack real (fuente de verdad = el código, no el README)

| Parte | Tecnología |
| :--- | :--- |
| Monorepo | npm workspaces + **Turborepo** (`turbo.json`) |
| `apps/web` | **Next.js 14 (App Router) + React 18 + TypeScript + Tailwind 4 + shadcn/ui (Radix)** |
| `apps/api` | **FastAPI (Python)** gestionado con **`uv`** |

> ⚠️ El backend usa **`uv`**, no `venv`+`pip` como sugiere el `README.md`. El frontend ya migró a Next.js App Router (Tailwind v4 vía `@tailwindcss/postcss`, fuentes vía `next/font`).

---

## Comandos

El gestor de paquetes es **pnpm** (workspaces vía `pnpm-workspace.yaml`; ver `packageManager` en el `package.json` raíz). **No uses `npm`/`yarn`.**

Desde la raíz del monorepo (`xertica-education/`):

```bash
pnpm install           # instala todos los workspaces
pnpm dev               # turbo dev (levanta apps)
pnpm build             # turbo build
pnpm lint              # turbo lint
```

Frontend (`apps/web/`) — con `--filter` desde la raíz, o `pnpm <script>` dentro de `apps/web/`:

```bash
pnpm --filter xertica-education-web dev       # Next.js dev server (localhost:3000)
pnpm --filter xertica-education-web build     # next build
pnpm --filter xertica-education-web start      # next start (producción)
pnpm --filter xertica-education-web typecheck  # tsc --noEmit
```

Backend (`apps/api/`) — usa **uv**, no venv+pip:

```bash
uv run uvicorn main:app --reload --port 8000    # dev
uv run uvicorn main:app --host 0.0.0.0 --port 8000   # start
python verify_boot.py                            # smoke test de arranque
```

La API corre en `http://localhost:8000`; el frontend espera esa URL (fallback en `apps/web/src/shared/lib/api.ts`).

Persistencia — **Supabase** (schema en `supabase/`, ver ADR-0004):

```bash
npx supabase link --project-ref <ref>   # linkear al proyecto cloud
npx supabase db push                      # aplicar migrations/ al cloud
# seed.sql NO corre con db push → aplicarlo en el SQL Editor del dashboard
```

Los repos (`apps/api/repositories/*`) usan **Supabase con fallback in-memory**: si `SUPABASE_URL`/`SUPABASE_KEY` son placeholders o fallan, caen a memoria (regla de oro #1). Secretos reales en `apps/api/.env` (copiar de `.env.example`, gitignored). El backend usa la key **service_role**; RLS está activo sin políticas.

---

## Estructura

```
xertica-education/
├── apps/
│   ├── web/          Next.js App Router · modular por feature
│   │   └── src/
│   │       ├── app/       solo routing (page.tsx reexporta el módulo)
│   │       ├── modules/   1 módulo por feature del flujo:
│   │       │              routes · new-route · curriculum · video ·
│   │       │              lab · assets · library
│   │       │              (cada uno: pantalla + components/ + index.ts)
│   │       └── shared/    ui/ (shadcn·Radix) · content/ (viewers) ·
│   │                      components/ (Layout,PageHeader) · lib/ · store/ · data/
│   └── api/          FastAPI
│       ├── routers/        rutas HTTP (jobs, learning_paths)
│       ├── services/       capacidades de negocio (route, jobs, video, workflow)
│       ├── repositories/   persistencia
│       ├── models/         domain/ (negocio) + dto/ (contratos HTTP)
│       ├── adapters/       llm/ storage/ parser/ renderer/
│       ├── config/         settings.py (pydantic-settings), dependencies.py (DI)
│       └── .env.example    plantilla de secretos (copiar a .env, gitignored)
├── supabase/         schema versionado: migrations/ + seed.sql (ADR-0004)
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
4. **Frontend (Next.js App Router, modular por feature)**:
   - `src/app/**/page.tsx` = **solo routing**; cada uno reexporta el default de un módulo (`export { default } from '@/modules/<feature>'`). No pongas UI aquí.
   - `src/modules/<feature>/` = una feature del flujo (routes, new-route, curriculum, video, lab, assets, library). Contiene su pantalla, un `components/` para lo local-de-la-feature y un `index.ts` (barrel) que expone el default. Componente usado por **una** feature → vive en su módulo; usado por **varias** → sube a `shared/`.
   - `src/shared/` = `ui/` (primitivas shadcn/Radix), `content/` (viewers de tipos de contenido), `components/` (Layout, PageHeader), `lib/` (api, types, utils), `store/` (store global), `data/` (mocks).
   - Componentes con hooks/estado llevan `'use client'`; providers globales en `src/app/providers.tsx`. Navegación con `next/link` (`href`) y `next/navigation` (`useRouter`, `useParams`, `usePathname`). API vía `src/shared/lib/api.ts` (`process.env.NEXT_PUBLIC_API_URL`), trabajo pesado por *polling* de jobs. Alias `@/` → `src/`.
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
