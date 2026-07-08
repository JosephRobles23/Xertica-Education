# ADR-0013: Parse-at-upload — `documents.parsed_md` como contexto de estructura y fuente de KB

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Deciden:** Galo (contacto@soygalo.com) · sesión `/grill-with-docs`
- **Ámbito:** `routers/documents.py`, `services/kb/ingestion.py`, `routers/learning_paths.py` (`generate-structure`), `repositories/documents/`, `supabase/migrations/`, frontend `new-route/NuevaRuta.tsx`
- **Relación:** **revisa** [ADR-0008 §5-§7](0008-document-parsing-via2-ingestion.md) (`use_as_source`, momento de parseo, scaffold de estructura).

## Contexto

El material que sube el cliente ("Propuesta del cliente" en *Audiencia* + "Material de referencia") debe cumplir **dos** roles: (a) **alimentar la generación de módulos/submódulos** y (b) **almacenarse en el KB por default**. Hoy el flujo no lo permite:

- El **checkbox `use_as_source`** ([ADR-0008 §5-§6](0008-document-parsing-via2-ingestion.md)) hace *opcional* que el documento entre al KB.
- El **parseo ocurre en Gate 1** ([ADR-0008 §7](0008-document-parsing-via2-ingestion.md)), **después** de `generate-structure`. Por eso ADR-0008 dejó "usar el documento como scaffold de estructura" explícitamente **fuera de alcance**: cuando se generan los módulos, el texto del documento todavía no existe.
- El frontend trackea **un solo** archivo (`baseMaterialFile`): los dos uploaders comparten `baseMaterialInputRef` y se pisan.

## Decisión

1. **Ingesta por default; se elimina la ruta "solo contexto".** Todo documento subido es **contexto Y fuente de KB**. Se quita el checkbox "usar también como fuente" de `NuevaRuta`; `use_as_source` queda **deprecado (siempre `true`)**. `upload_document` siempre crea el `Source` Vía 2.

2. **Parse-at-upload (síncrono).** El endpoint de subida parsea el binario a Markdown verbatim (`SimpleParserAdapter`) **en el momento del upload** y persiste el resultado en una columna nueva:

   ```sql
   alter table documents add column parsed_md text;   -- markdown verbatim; null si el parse falló/pendiente
   ```

   Un solo parse, **dos consumidores** (estructura + ingesta). Síncrono para el MVP (archivos ≤20 MB, parser rápido en docs digitales); si resulta lento se promueve a Job. Si el parse falla, no bloquea la subida (regla de oro 1): `parsed_md=null` y se reintenta/omite en Gate 1.

3. **`generate-structure` recibe el contexto del documento.** Su contrato gana `parsed_docs` (los `parsed_md` de la ruta, concatenados). El generador mock los ignora hoy (regla de oro 3: IA real al final); se cablea el **contrato**, no la inteligencia.

4. **Gate 1 reutiliza `parsed_md`.** `RealDocumentProvider` lee `documents.parsed_md` en vez de re-descargar y re-parsear el binario. Reemplaza el "parseo pesado en Gate 1" de [ADR-0008 §7](0008-document-parsing-via2-ingestion.md).

5. **Múltiples documentos por ruta.** El frontend pasa de `baseMaterialFile` (1) a una **lista**; cada archivo se sube+parsea individual. `generate-structure` recibe la unión de `parsed_md`; Gate 1 ingesta cada documento como un `Source` Vía 2. La tabla `documents` ya es 1:N por ruta, así que el grueso es estado en el frontend + agregación de contexto.

## Consecuencias

- **+** Se cumplen los dos roles del material del cliente: informa la estructura **y** ancla la generación vía KB, sin doble parseo (una sola pasada, cacheada en `parsed_md`).
- **+** El feedback de errores de parseo se adelanta al **momento de subir** (antes llegaba en Gate 1, ADR-0008 §7): mejor UX.
- **+** UI más simple: desaparece el checkbox de doble rol; "subir = usar".
- **−** `parsed_md` persiste el derivado del binario (ADR-0008 §3 lo consideraba transitorio). Se acepta el costo de almacenamiento a cambio de no re-parsear; es regenerable desde el binario.
- **−** Parse síncrono alarga la respuesta del upload para archivos grandes; mitigado por el límite de 20 MB y la puerta a promoverlo a Job.
- **−** Cambio de contrato en `generate-structure` (`parsed_docs`) y en `documents` (columna nueva) — acordado en este ADR (CONTEXT §5 regla 2).
- **Supersesión parcial:** revisa [ADR-0008 §5](0008-document-parsing-via2-ingestion.md) (`use_as_source` deprecado) y **§7** (parseo movido de Gate 1 al upload); trae al alcance el "scaffold de estructura" que ADR-0008 había excluido. El resto de ADR-0008 sigue vigente salvo lo revisado por [ADR-0011](0011-kb-solo-via2-linking-por-modulo.md).
