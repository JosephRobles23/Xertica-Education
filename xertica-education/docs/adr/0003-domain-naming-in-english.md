# ADR-0003: Nomenclatura del dominio en inglés

- **Estado:** Aceptado
- **Ámbito:** Modelo de dominio (Spine), API y persistencia

## Contexto

El dominio se habla en español (**Ruta**, **tema**, **brief**), pero mezclar idiomas en el código genera ambigüedad e inconsistencias entre API, modelos y base de datos.

## Decisión

Se oficializa la **denominación técnica en inglés** para las entidades del Spine. Por ejemplo, `Ruta` se mapea como **`LearningPath`** en toda la API y la persistencia.

## Consecuencias

- Consistencia de nomenclatura entre código, contratos y base de datos.
- Requiere mantener el mapeo dominio→código documentado en [`CONTEXT.md`](../../CONTEXT.md) (glosario de lenguaje ubicuo).
