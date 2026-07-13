# ADR-0019: Generacion de laboratorios para Google Classroom

- **Estado:** Aceptado
- **Fecha:** 2026-07-10
- **Ambito:** Laboratorios practicos, generacion de contenido por modulo, RAG, export TXT/PDF y UI de revision
- **Relaciona:** ADR-0005 de spine completo, ADR-0006 de KB/RAG, ADR-0016 de fuentes aprobadas, ADR-0017 de revision de fuentes, ADR-0018 de infografia y quiz

## Contexto

El branch `feature/labs` implementa la generacion real de laboratorios practicos para
los modulos de una ruta. Antes de este cambio, el componente `lab` existia en la interfaz
de contenido, pero no tenia un pipeline dedicado de generacion, grounding, persistencia y
regeneracion comparable al de lecciones, quizzes o infografias.

El uso real del laboratorio es editorial: las autoras de Xertica copian el contenido
generado y lo publican como tarea en Google Classroom. Por eso, el output no debe
optimizarse como una experiencia interactiva para el alumno dentro de la plataforma, sino
como una pieza de texto clara, compacta, dinamica y lista para pegarse en Classroom.

El laboratorio debe seguir conectado al contexto de la ruta y del modulo. No puede ser una
actividad generica. Si el modulo ensena Gemini, Canva, BigQuery u otra herramienta, la
actividad debe pedir aplicar esa herramienta o tomar una decision practica sobre su uso.
Si el modulo es conceptual, el laboratorio puede ser una simulacion, caso guiado,
walkthrough o actividad de toma de decisiones.

Las fuentes de contexto obligatorias son:

1. Informacion general de la ruta.
2. Titulo, descripcion y objetivo de aprendizaje del modulo.
3. Customer Context de la ruta o empresa.
4. Knowledge Base consultada via RAG.
5. Fuentes aprobadas y verificadas de Deep Research.
6. Herramientas o tecnologias detectadas en el contenido del modulo.

No se deben usar fuentes rechazadas. Las fuentes no verificadas solo son admisibles si ya
fueron aprobadas por una persona y forman parte del corpus aprobado.

## Decision

1. Agregar un servicio backend dedicado para laboratorios:
   - `services/lab/interface.py`
   - `services/lab/service.py`
2. Registrar `LabService` en `config/dependencies.py` usando:
   - `OpenRouterLLMAdapter`
   - `KnowledgeBaseInterface`
3. Exponer un endpoint de regeneracion por modulo:
   - `POST /learning-paths/{route_id}/modules/{module_id}/lab/regenerate`
4. Obtener el contexto de generacion desde la ruta, modulo, objetivo del modulo,
   Customer Context, fuentes aprobadas y KB/RAG existente.
5. Detectar herramientas y tecnologias relevantes reutilizando `TOOL_REGISTRY` y
   `TECHNOLOGY_ALIASES` del servicio de research.
6. Pedir al LLM una respuesta JSON estructurada para mantener contrato interno, pero
   hacer que el campo principal sea `classroomText`.
7. Modelar el laboratorio como contenido editorial para Google Classroom:
   - introduccion breve;
   - desafio claro;
   - 4 o 5 pasos maximo;
   - prompt maestro o plantilla cuando aplique;
   - entregable evaluable;
   - 1 o 2 tips;
   - cierre o reflexion breve.
8. Mantener campos estructurados de soporte:
   - `title`
   - `objective`
   - `scenario`
   - `estimatedTimeMinutes`
   - `difficulty`
   - `tools`
   - `prerequisites`
   - `instructions`
   - `deliverable`
   - `reflectionQuestions`
   - `sourceReferences`
   - `safetyNotes`
9. Normalizar y validar la respuesta del LLM con limites de longitud para evitar labs
   demasiado largos o enciclopedicos.
10. Incluir fallback deterministico cuando la respuesta del LLM no sea parseable o no
    incluya instrucciones validas.
11. Persistir el laboratorio generado en la estructura existente de la ruta:
    - `target_module["lab"]`
    - `route.pack["lab"]`
12. Generar artefactos locales descargables para autoras:
    - TXT desde `classroomText`
    - PDF renderizado desde `classroomText`
    - JSON estructurado para inspeccion/debug
13. Servir los artefactos desde `/static/labs` usando el montaje `/static` ya existente.
14. No versionar artefactos generados en `apps/api/static/`; son outputs runtime.
15. Cambiar la UI de `LabView.tsx` para mostrar el texto listo para Google Classroom,
    con acciones de:
    - copiar texto;
    - descargar TXT;
    - descargar PDF.
16. Evitar una UI de checklist interactivo para el alumno, porque la plataforma es usada
    por las autoras para preparar el material, no por quienes realizan el laboratorio.
17. Mantener la regeneracion aislada del laboratorio para no afectar leccion, video,
    quiz, infografia u otros componentes del modulo.
18. Agregar cobertura enfocada en `apps/api/tests/test_lab.py`.

## Consecuencias

- Las autoras reciben un laboratorio listo para copiar y pegar en Google Classroom, sin
  tener que reconstruirlo desde tarjetas o pasos interactivos.
- El contenido conserva grounding en ruta, modulo, Customer Context, KB y fuentes
  aprobadas.
- Los laboratorios pueden ser especificos a herramientas como Gemini, Canva o BigQuery,
  en lugar de ser ejercicios genericos.
- La plataforma mantiene contrato estructurado para previews, persistencia y futuras
  mejoras, pero el output primario visible es `classroomText`.
- TXT y PDF cubren los flujos de descarga sin introducir un sistema nuevo de exportacion
  global.
- La generacion de PDF depende de Pillow, que ya forma parte de las dependencias usadas
  por otros flujos de assets.
- Los artefactos locales en `/static/labs` son temporales y deben excluirse de commits.
- Si la KB no responde, el servicio degrada con warning y continua con el resto del
  contexto disponible.
- Si el LLM devuelve JSON invalido, el fallback permite mantener el flujo funcional,
  aunque con menor especificidad.
- La regeneracion de labs queda desacoplada del resto del modulo, reduciendo el riesgo de
  borrar o reemplazar componentes ya aprobados.
