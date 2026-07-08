# ADR-0014: Estructura Propuesta real con LLM `route_structurer` (Gate 0)

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Deciden:** Joseph Robles (petter.chuquipiondo.r@uni.pe) · sesión de Claude
- **Ámbito:** `services/route_structurer/`, `routers/learning_paths.py`, `tests/test_route_structurer.py`, frontend `modules/curriculum/EstructuraPropuesta.tsx`, `modules/new-route/NuevaRuta.tsx`
- **Relación:** **continúa** [ADR-0013](0013-parse-at-upload-parsed-md.md) (momento de parseo de material) y **revisa** [ADR-0008 §7](0008-document-parsing-via2-ingestion.md) (scaffold de estructura).

## Contexto

Previamente, la propuesta curricular se mostraba a través de un mock estático hardcodeado en el frontend (`INITIAL_PROPOSAL`). Para cumplir la visión del MVP, el pipeline debe generar módulos y componentes reales adaptados al brief y a los documentos subidos por el cliente (material-first). 

Se requiere un servicio robusto en el backend que delegue al LLM (Claude Haiku 4.5 vía OpenRouter) la descomposición del material en módulos lógicos coherentes de aprendizaje, valide/normalice los enums y campos a tipos válidos del dominio, persista la estructura en la base de datos de forma asíncrona mediante un Job, y conecte el frontend (Gate 0) para realizar polling, renderizar cargando (skeletons) y posibilitar la regeneración en caso de fallo.

## Decisión

1. **Creación del servicio `route_structurer`:** Se encapsula la capacidad de descomposición instruccional bajo el contrato `RouteStructurerInterface`. La implementación real `LLMRouteStructurer` utiliza el adaptador OpenRouter para enviar el brief, contexto del cliente y el contenido parseado de los documentos (`parsed_md` vía ADR-0013) a un modelo de razonamiento rápido (`claude-haiku-4.5`).
2. **Generación asíncrona (Job en background):** La generación de la estructura curricular corre como un `JobsService` en background. Esto evita timeouts HTTP síncronos en peticiones del cliente que dependen del LLM. El Job actualiza el estado de la ruta persistiendo los módulos normalizados y marca el Job como `completed` o `failed`.
3. **Validación y Normalización rigurosa (`normalize.py`):** La salida JSON cruda del LLM se valida y clampa a los enums estrictos del dominio:
   - Tipos de módulos (`ModuleType`): `intro`, `capsula`, `lab`, `evaluacion`, `cierre`.
   - Tipos de componentes (`ComponentType`): `lesson`, `video`, `lab`, `infografia`, `quiz`.
   Cualquier tipo inventado por el LLM se clampa a un valor por defecto o se omite. Si no se produce al menos un módulo válido con componentes, el Job se considera fallido de forma explícitamente.
4. **Enriquecimiento de metadatos del módulo:** Los módulos devueltos por el backend y consumidos por el frontend incluyen:
   - `description` / `descripcion`: Explicación del objetivo del módulo generada por el LLM o heredada.
   - `target_minutes` / `duracion_objetivo_min`: Minutos estimados. Si el LLM no especifica un tiempo válido, se computa dinámicamente sumando fallbacks por tipo de componente (ej: quiz = 4 min, lab = 15 min, etc.).
5. **Conexión Frontend y Ciclo de Vida en Gate 0:**
   - Redirección inmediata: Al crear la ruta, el frontend viaja a `/estructura-propuesta` y realiza el polling asíncrono del Job.
   - Skeleton Loader: Muestra una interfaz animada (`pulse`) que imita la estructura curricular mientras se produce la generación.
   - Regeneración: Si el Job falla, se ofrece un botón de "Regenerar estructura" en la UI de Gate 0 para reintentar la llamada al estructurador LLM.
   - Guardado E2E: El frontend actualiza los módulos en la base de datos (con un PATCH) antes de aprobar la estructura para persistir cualquier ordenación o edición humana.

## Consecuencias

- **+** Generación instruccional real y contextualizada adaptada a los documentos del cliente (material-first).
- **+** Tolerancia a timeouts y control granular del flujo de generación asíncrona a nivel de interfaz de usuario.
- **+** Blindaje del backend frente a enums rotos o invenciones lógicas del modelo de lenguaje.
- **−** Requiere llamadas de red asíncronas adicionales y polling del frontend para detectar cuándo el currículo propuesto está listo.
