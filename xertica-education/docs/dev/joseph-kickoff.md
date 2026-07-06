# Kickoff — Joseph · Knowledge Base / Integraciones

> Cómo llevar tus **primeras tareas** de principio a fin con las 12 skills agénticas.
> Lee primero: [`Skills_Desarrollo_Agentico.md`](../../../Documents/Skills/Skills_Desarrollo_Agentico.md) · [`CONTEXT.md`](../../CONTEXT.md) · [`docs/adr/`](../adr/) · [`architecture.md`](../arquitectura/architecture.md) §5 y §14.

## Tus primeras tareas
1. **Integración con Google Drive** — Drive como **fuente** ([issue #17](../issues/pending/joseph/issue-17-google-drive-source-ingestion.md), Vía 2) y como **destino de export** de assets ([issue #18](../issues/pending/joseph/issue-18-export-assets-google-drive.md)), con carpetas auto-organizadas por `cliente → ruta → módulo`.
2. **Quick win — descarga por módulo** ([issue #20](../issues/pending/joseph/issue-20-module-download-zip.md)) — descarga de assets agrupados por módulo (la descarga directa a Drive se apoya en el export de #18).

Orden: la **integración con Drive** primero (es la pieza estructural con incógnitas de OAuth); los **quick wins** después, porque reutilizan el mismo cliente de Drive.

> **Antes de tocar código:** Drive introduce una dependencia externa que hoy la arquitectura no contempla (asume solo Supabase Storage, §13). Esto **es material de ADR**. No lo decidas en un commit; decídelo en una sesión de grilling documentada.

---

## Tarea 1 · Integración con Google Drive

### Paso 0 — (opcional) `/teach`
**Concepto.** Crea un workspace de enseñanza con lecciones interactivas y glosario; usa ciencia cognitiva (retrieval practice, spacing).
**Por qué importa para ti.** Si el equipo no tiene claro cómo encajan `Asset.storage_path`, `provenance` y el grounding de la KB, un `/teach "spine: Asset, storage_path y provenance"` de 20 min ahorra malentendidos de arquitectura.

### Paso 1 — `/decision-mapping`
**Concepto.** Mapa de tickets con niebla de guerra.
**Por qué importa para ti.** Drive tiene muchas incógnitas acopladas (scopes OAuth, unidad personal vs compartida, deduplicación, permisos). Mapearlas evita descubrir a mitad de implementación que faltaba un scope.

```
> /decision-mapping "Integración con Google Drive: ingesta + exportación de assets"
```
```markdown
## #1: ¿Qué scopes OAuth mínimos? (drive.file vs drive.readonly)        Type: Research
## #2: ¿Los assets viven en Supabase Storage Y Drive, o Drive es espejo? Type: Discuss
## #3: ¿Cómo se nombran/estructuran las carpetas cliente→ruta→módulo?    Type: Discuss · Blocked by #2
## #4: Prototipo del flujo OAuth + subida de un archivo                  Type: Prototype · Blocked by #1
```

### Paso 2 — `/grill-with-docs` → ADR
**Concepto.** Interrogatorio implacable que además actualiza `CONTEXT.md` y crea ADRs.
**Por qué importa para ti.** La pregunta "¿Supabase Storage o Drive es la fuente de verdad del binario?" es **irreversible en la práctica** (define backups, permisos, costos). Tiene que quedar en un ADR.

> **Agente:** "Si Drive es la fuente de verdad del binario, pierdes el control de RLS que te da Supabase Storage. **Recomendación:** Supabase Storage es canónico (`Asset.storage_path`); Drive es un **export/espejo** para consumo del cliente. Así el grounding y la trazabilidad no dependen de permisos de Drive." → **ADR-0006: Google Drive como export, Supabase Storage como canónico**.

Actualiza `CONTEXT.md`:
```markdown
## Export a Drive
Copia de un ASSET aprobado hacia Google Drive del cliente, organizada en
carpetas cliente→ruta→módulo. Es un espejo de consumo; la fuente de verdad
del binario sigue siendo Supabase Storage (Asset.storage_path).
```

### Paso 3 — `/prototype` (rama Logic)
Un script que hace el OAuth, sube un archivo y crea la jerarquía de carpetas. Responde "¿qué scopes y qué llamadas necesito?" antes de meterlo en el pipeline. Se borra; la decisión va al ADR.

### Paso 4–5 — `/to-prd` → `/to-issues`
Vertical slices: p. ej. `Adjuntar fuente desde Drive (Vía 2)`, `Export de asset aprobado a Drive`, `Auto-organización de carpetas`. Cada uno end-to-end.

### Paso 6 — `/tdd` + `/ponytail`
**Por qué importa para ti.** El anti-patrón aquí es escribir tu propio wrapper de Drive. Ponytail te frena: usa el SDK oficial.

```python
# RED
def test_ruta_de_carpeta_por_cliente_ruta_modulo():
    path = drive_folder_path(cliente="acme", ruta="ia-generativa", modulo="intro")
    assert path == ["Xertica Education", "acme", "ia-generativa", "intro"]

# GREEN — ponytail: lista literal, no FolderPathStrategy ni builder
def drive_folder_path(cliente: str, ruta: str, modulo: str) -> list[str]:
    return ["Xertica Education", cliente, ruta, modulo]
```
```python
# ponytail: usar google-api-python-client (dep oficial), NO un wrapper propio
# ponytail: drive.file scope (solo lo que la app crea), no drive full
```

### Paso 7 — `/ponytail-review`
Antes del PR: caza el `DriveClient` con métodos que solo envuelven 1:1 el SDK, o el retry casero que `google-api-python-client` ya trae.

---

## Tarea 2 · Quick wins (descargas)
Tarea pequeña → **ponytail-first**. La escalera de decisión brilla aquí:

- **Descarga agrupada por módulo:** ¿stdlib lo resuelve? `zipfile` + streaming. No hace falta una librería de archivos.
- **Descarga a Drive:** reutiliza el cliente de la Tarea 1. Cero código nuevo de auth.

```python
# ponytail: zipfile de stdlib, streaming; no lib de terceros para un zip
import zipfile, io
def zip_assets_de_modulo(assets) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for a in assets:
            z.writestr(a.nombre, a.contenido)
    return buf.getvalue()
```

Aquí probablemente `/ponytail-review` diga *"Lean already. Ship."*

---

## Referencia rápida — qué skill en qué momento

| Momento | Skill |
| :-- | :-- |
| Integración con muchas incógnitas | `/decision-mapping` |
| Decisión irreversible (Storage vs Drive) | `/grill-with-docs` → ADR |
| Validar OAuth/subida | `/prototype` (Logic) |
| Formalizar | `/to-prd` → `/to-issues` |
| Implementar sin over-engineering | `/tdd` + `/ponytail` |
| Tarea chica (quick win) | `/ponytail` directo |
| Antes del PR | `/ponytail-review` |

## Definición de listo (DoD)
- [ ] Se pueden seleccionar archivos de Drive como fuentes (Vía 2).
- [ ] Los assets aprobados aparecen en Drive en `cliente/ruta/módulo`.
- [ ] Descarga por módulo y descarga a Drive funcionales.
- [ ] **ADR-0006** registra Storage canónico vs Drive espejo.
- [ ] `CONTEXT.md` con el término *Export a Drive*.
