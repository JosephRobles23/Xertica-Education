# ADR-0008: Parsing e ingesta de documentos del usuario (Vía 2)

- **Estado:** Aceptado
- **Ámbito:** `adapters/parser/`, `adapters/storage/`, `services/kb/ingestion.py`, `repositories/{documents,sourcing}/`, `routers/`, `supabase/migrations/`, frontend `new-route`
- **Flujo:** Vía 2 — subida de archivos estilo NotebookLM (`baseMaterialFile` + toggle `useAsSource` en `NuevaRuta.tsx`)
- **Relación:** implementa el parser ligero de [ADR-0006](0006-kb-rag-ingestion-embeddings.md) y su conexión real a la KB; extiende [ADR-0007](0007-source-route-centrica-sourcing.md) (`sources` gana `origin` + `document_id`).

## Contexto

El `SimpleParserAdapter` existe pero está **desconectado**; la ingesta usa `MockDocumentProvider` (contenido sintético). No hay endpoint de subida ni storage cableado. El frontend ya modela la Vía 2 (accept `doc/docx/pdf/ppt/pptx/xls/xlsx/txt/md`, toggle `useAsSource` con doble rol: *scaffold* de personalización vs *fuente* de la KB). Además, el filtro de ingesta actual (`verificada_google`) **excluiría** las fuentes propias de la Vía 2. Resuelto en grilling (`/grill-with-docs`).

## Decisión

1. **Motor de parsing: determinista + puerto de escalación.** `SimpleParserAdapter` (librerías) como default → **texto verbatim** (citas fieles, coste ~0, sin alucinación). MinerU / Document AI / vision-LLM detrás del mismo `BaseParserAdapter` como **fase 2**, solo para escaneados/tablas complejas. **No** se usa LLM como parser primario (parafrasea → rompe el grounding).
2. **Formatos MVP:** `pdf, docx, pptx, xlsx (+ openpyxl), txt, md`. Los **legacy** `.doc/.ppt/.xls` se rechazan con error claro ("convierte a formato moderno"); se **alinea el `accept`** del frontend. (Sin LibreOffice en el MVP.)
3. **Storage:** el **binario** va a Supabase Storage (fuente de verdad, RLS · `StorageAdapter`); los **chunks** a `kb_chunks`. El **markdown es transitorio** (derivado, regenerable) — no se persiste aparte.
4. **Modelo de datos:** nueva tabla **`documents`** (separada de `sources`).
5. **Conexión a la KB:** un documento con `use_as_source=true` genera un **`Source` Vía 2** con `document_id` FK → `documents`. `kb_chunks.source_id` sigue apuntando a `sources` (**camino de cita único**). Vía 1 = source con `url`; Vía 2 = source con `document_id`. La cita muestra el `filename` y enlaza al binario.
6. **Filtro de corpus (ingesta):** entra a la KB si `verificada_google` **OR** (`origin='upload'` AND `use_as_source`). `verificada_google` pasa a ser **metadato de provenance** de la cita, no el gate único. (Reemplaza el filtro actual que dejaba fuera la Vía 2.)
7. **Dónde se parsea:** el endpoint de subida **valida tipo/tamaño y SOLO almacena** (binario + fila `documents` [+ `Source` si `use_as_source`]). El **parseo pesado corre en el Job de ingesta de Gate 1**, con un `DocumentProvider` real que lee el binario del Storage y llama al `SimpleParserAdapter`. Reutiliza el pipeline ya probado (`chunk_markdown → Embedder → kb_chunks`).

### Schema (migración aditiva)

```sql
documents(
  id uuid pk, learning_path_id uuid fk→learning_paths on delete cascade,
  storage_path text, filename text, mime text,
  use_as_source boolean not null default false, created_at timestamptz)
-- RLS on sin políticas (hereda ADR-0004)

alter table sources
  add origin text check (origin in ('deep_research','upload')) default 'deep_research',
  add document_id uuid null references documents(id) on delete cascade,
  alter column url drop not null;   -- los uploads no tienen url
-- unique(learning_path_id, url) sigue valiendo (Postgres permite múltiples NULL);
-- idempotencia de uploads por unique(learning_path_id, document_id).
```

## Consecuencias

- **+** La Vía 2 queda funcional end-to-end reusando el seam existente: solo se reemplaza `MockDocumentProvider` por el real; el resto del pipeline no cambia.
- **+** Citas fieles (verbatim) y trazables al documento original (binario en Storage).
- **+** El gate de ingesta pasa a reflejar la decisión humana + el `useAsSource`, no un flag de Google.
- **−** Nuevas piezas a construir: endpoint multipart, `StorageAdapter` real (Supabase Storage), `DocumentProvider` real, tabla `documents` + cambios en `sources`, `openpyxl`.
- **−** El feedback de errores de parseo llega en Gate 1 (no al subir); se mitiga validando tipo/tamaño en la subida.
- **Deuda / fuera de alcance:** MinerU/OCR (escaneados, escalación); uso del documento como *scaffold* para inferir estructura (concierne al `route_structurer`, no a la KB); fetch real de URLs de la Vía 1 (hoy sigue mock).
- **Ownership:** Vía 2 cruza Arantza (sourcing/subida) y Joseph (parser/KB); coordinar el contrato del endpoint.
