# ADR-0020: OpenMontage como código vendorizado

- **Estado:** Aceptado
- **Fecha:** 2026-07-10
- **Deciden:** Video Production (sebas)
- **Supersede:** ADR-0010

## Contexto

ADR-0010 integró OpenMontage como un submódulo apuntado al repositorio externo
`calesthio/OpenMontage`. El equipo de video necesita modificar los componentes de
Remotion que materializan los Videos de Explicación Conceptual, pero no tiene permisos
para publicar esos cambios en el repositorio externo. Como consecuencia, un commit
local del submódulo no puede ser recuperado por otros clones ni por CI/CD.

Se evaluaron tres opciones:

1. Solicitar acceso de escritura al repositorio externo.
2. Mantener un fork accesible y actualizar el remote del submódulo.
3. Incorporar el renderer de Remotion del snapshot actual como archivos normales del monorepo.

## Decisión

Usar **código vendorizado** (opción 3). Se elimina la relación de submódulo y se
versiona `openmontage/remotion-composer/` junto con la licencia upstream, incluyendo
las modificaciones locales a los componentes de Remotion. El resto del checkout
local de OpenMontage queda ignorado porque Xertica no lo importa ni lo ejecuta.

El snapshot de partida corresponde al commit local de OpenMontage
`1031a86dc7b003371b794ed3dc917ce755100fef`. Las actualizaciones futuras desde upstream
serán manuales y deberán preservar las adaptaciones de Xertica.

## Consecuencias

**Positivo:**

- Todos los clones y CI/CD reciben exactamente los componentes visuales usados por el render.
- El equipo puede modificar Remotion sin permisos sobre un repositorio externo.
- El checkout ya no requiere inicializar submódulos.

**Negativo:**

- Se pierde `git submodule update --remote`; integrar cambios upstream será manual.
- El monorepo almacena una copia del renderer y aumenta de tamaño.
- El equipo de video asume el mantenimiento de cualquier divergencia con OpenMontage.

**Condicionado a:**

- ADR-0008 (Remotion Composition Engine) sigue vigente; cambia la forma de incorporar
  el código, no el motor de composición.
- Las actualizaciones de OpenMontage deben entrar como commits explícitos y revisables
  del monorepo.
