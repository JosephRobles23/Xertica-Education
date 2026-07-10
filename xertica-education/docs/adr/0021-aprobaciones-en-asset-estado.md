# ADR-0021 — Aprobaciones de contenido en `Asset.estado` con espejo en el JSON

- **Estado:** Aceptado (grill de persistencia, 2026-07-10)
- **Relacionados:** [[0020-materializacion-perezosa-spine]], [[0005-full-spine-schema]]

## Contexto

Todo el workflow de revisión (aprobar/refinar contenido por módulo, aprobar storyboard,
lab guide, marcar ruta generada, descartar fuentes) vivía **solo en React
state/localStorage**: se pierde con un refresh y no se comparte entre revisores.
ADR-0005 ya definió que la aprobación pertenece al `Asset.estado`
(`draft/generado/en_revision/aprobado`) y dejó el split como deuda.

## Decisión

1. **Aprobación de contenido** → `PATCH /learning-paths/{id}/modules/{mid}/contents/{kind}/approval`
   con body `{"status": "aprobado" | "en-revision" | "borrador"}`:
   - Actualiza `Asset.estado` (materializando el spine perezosamente, ADR-0020).
     Mapeo: `aprobado→aprobado`, `en-revision→en_revision`, `borrador→draft`.
   - **Espeja** el status en `details.modules[].contents[].status` — el frontend ya lee
     ese campo como fallback de su override local, así que la rehidratación no cambia
     el contrato (regla de oro #2).
2. **Flags a nivel ruta** (storyboard aprobado, lab guide, generado, fuentes
   descartadas) → `PATCH /learning-paths/{id}/approvals` que mergea en
   `details.approvals` (campo aditivo). Las fuentes descartadas se persisten **por URL**
   (no por índice: el orden del array cambia entre re-runs del deep-research).
3. `approved_by` queda **pospuesto** (nullable a futuro): no hay identidad de usuario
   en la app; registrar autoría real es otra épica.

## Consecuencias

- El frontend deja de ser la fuente de verdad del workflow: sus overrides locales pasan
  a ser capa optimista sobre lo que devuelve el `GET`.
- El vocabulario interino de status en el JSON sigue mezclado (`generado` post-creación
  vs `aprobado/en-revision/borrador` de revisión); el vocabulario canónico es el de
  `Asset.estado` y el split completo Ruta-ciclo-de-vida sigue como deuda de ADR-0005.
