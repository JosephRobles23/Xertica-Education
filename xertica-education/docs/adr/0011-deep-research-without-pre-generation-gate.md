# ADR-0011: Deep Research sin gate previo a la generación

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Ámbito:** Sourcing, Knowledge Base y Video Assets
- **Relacionado:** ADR-0001 (pgvector como KB), ADR-0005 (Spine completo)
- **Amplía:** ADR-0006 (video final como Asset persistido)

## Contexto

El flujo actual mezcla bajo el nombre `Source` dos resultados con propósitos
distintos:

1. referencias documentales que podrían fundamentar la generación mediante la
   Knowledge Base;
2. videos encontrados con YouTube API que pueden sustituir la producción de un
   video propio o generado con IA.

Solicitar aprobación humana de todas las referencias antes de generar los
Módulos añade una intervención que el producto quiere evitar. Sin embargo,
permitir que material no verificado entre automáticamente a la KB haría que
contenido dudoso fundamente todos los Assets posteriores.

Además, ADR-0006 solo define como video final el MP4 renderizado y persistido.
No contempla un video externo aceptado para satisfacer un Componente `video`.

## Decisión

1. **Deep Research no introduce un gate humano previo a la generación de
   contenido.** El flujo avanza directamente a la creación de los Módulos y sus
   contenidos.
2. Deep Research separa sus resultados según su propósito:
   - Las referencias documentales de dominios oficiales incluidos en una
     allowlist y verificadas técnicamente se ingieren automáticamente en la KB.
   - Las referencias no verificadas no se usan para generar contenido ni se
     envían a la KB. Tampoco provocan un gate previo.
   - Los videos encontrados en YouTube son recomendaciones de **Video Asset
     Externo**; no son Fuentes para la KB.
3. La recomendación de YouTube se muestra junto con el resto del contenido ya
   generado durante la revisión del Módulo.
4. Al aceptar una recomendación, se persiste como **Video Asset Externo** del
   Componente `video`, con su URL y procedencia. El archivo no se copia ni se
   renderiza.
5. Un Video Asset Externo aceptado satisface el Componente `video` igual que un
   Video Asset Renderizado, aunque ambos conservan procedencias distintas.

## Consecuencias

- Se elimina una intervención humana antes de disponer de contenido revisable.
- La KB conserva una frontera de confianza automática y reproducible.
- Cuando no existan suficientes referencias oficiales, la generación tendrá
  menor amplitud en lugar de apoyarse en material no verificado.
- Los videos externos reducen costo y tiempo de producción, pero introducen
  dependencia de disponibilidad, permisos y licencias de terceros.
- La lectura de un Componente `video` debe admitir como resultado final tanto
  una URL externa como un MP4 renderizado.
- ADR-0006 sigue vigente para Videos Assets Renderizados y se amplía con la
  variante externa definida aquí.
- La implementación existente todavía no materializa esta decisión: hoy agrupa
  los resultados como `route.sources`, los conserva en memoria y la selección
  de YouTube solo vive en el estado local del frontend.
