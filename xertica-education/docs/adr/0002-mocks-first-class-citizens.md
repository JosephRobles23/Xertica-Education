# ADR-0002: Mocks como first-class citizens

- **Estado:** Aceptado
- **Ámbito:** Todos los servicios de `apps/api/services/`

## Contexto

El desarrollo paralelo del MVP no puede bloquearse esperando integraciones de IA o APIs de pago, y los bugs de UI deben poder aislarse de fallas generativas.

## Decisión

La habilitación de una clase **`mock.py`** conforme al contrato es **obligatoria desde el inicio** para cada servicio. El frontend puede ejecutar el flujo de integración completo de forma local sin credenciales de APIs externas.

## Consecuencias

- Previene cuellos de botella entre desarrolladores (regla de oro del MVP: ninguna feature bloquea a otra).
- Aísla los bugs de UI de fallas de APIs generativas.
- Obliga a mantener el patrón `interface.py` + `service.py` + `mock.py` por servicio.
