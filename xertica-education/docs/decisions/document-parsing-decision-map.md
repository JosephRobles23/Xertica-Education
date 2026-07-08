# Decision Map — Parsing e ingesta de documentos (Vía 2) · rama `feature/KB-RAG`

> Decisiones del grilling (`/grill-with-docs`) para la fase de parsing de la Vía 2.
> Todas resueltas → [[docs/adr/0008-document-parsing-via2-ingestion]].
> Alcance: `adapters/parser/`, `adapters/storage/`, `services/kb/ingestion.py`,
> `repositories/{documents,sourcing}/`, `routers/`, `supabase/migrations/`.

## Contexto
El parser existe (`SimpleParserAdapter`) pero está desconectado; la ingesta usa
`MockDocumentProvider`. El frontend ya modela la subida (`baseMaterialFile` + `useAsSource`).
Este mapa define cómo parsear, almacenar y conectar los documentos del usuario a la KB.

---

## #1: ¿Motor de parsing?
Type: Discuss → **ADR**
### Answer
**RESUELTO → Determinista + puerto de escalación.** `SimpleParserAdapter` (librerías) por
defecto (verbatim); MinerU/Document AI/vision-LLM como fase 2 para escaneados/tablas. **No**
LLM como parser primario (parafrasea → rompe citas).

## #2: ¿Formatos MVP?
Type: Discuss
### Answer
**RESUELTO → `pdf, docx, pptx, xlsx, txt, md`** (+ openpyxl). Rechazar legacy `.doc/.ppt/.xls`
con error claro; alinear el `accept` del frontend.

## #3: ¿Qué persistimos?
Type: Discuss
### Answer
**RESUELTO → Binario en Supabase Storage + chunks en `kb_chunks`.** Markdown transitorio
(no se persiste aparte).

## #4: ¿Modelo de datos del documento?
Type: Discuss
### Answer
**RESUELTO → Tabla `documents` separada** (no extender `sources` con storage_path).

## #5: ¿Cómo se conecta a la KB / cita?
Blocked by: #4
Type: Discuss
### Answer
**RESUELTO → `documents (use_as_source) → Source(document_id) → kb_chunks`.** Camino de cita
único. Vía 1 = source con `url`; Vía 2 = source con `document_id`. `sources` gana `document_id`.

## #6: ¿Filtro de corpus (qué entra a la KB)?
Type: Discuss
### Answer
**RESUELTO → Filtro compuesto:** ingestar si `verificada_google` OR (`origin='upload'` AND
`use_as_source`). `verificada_google` queda como metadato de provenance, no gate único.

## #7: ¿Dónde corre el parseo?
Type: Discuss
### Answer
**RESUELTO → El upload solo almacena** (valida tipo/tamaño + guarda binario + `documents`
[+ `Source`]); el **parseo corre en el Job de ingesta de Gate 1** vía `DocumentProvider` real.

---

## Estado del mapa: **frontera resuelta.** → migración aditiva + StorageAdapter + parser xlsx +
DocumentProvider real + endpoint de subida (`/tdd` + `/ponytail`). Ver ADR-0008.
