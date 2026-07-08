# ADR-0010: OpenMontage como Git Submodule

- **Estado:** Aceptado
- **Fecha:** 2026-07-07
- **Deciden:** Video Production (sebas)

## Contexto

OpenMontage es un repositorio externo (github.com/calesthio/OpenMontage) que contiene 52 herramientas Python, 18 archivos de infraestructura, un proyecto Remotion (Node.js), 14 pipelines YAML, y 400+ skills Markdown. Necesitamos sus herramientas de audio, música, y composición Remotion para el pipeline de video.

Tres opciones de integración:

1. **`pip install` desde GitHub** — agrega OpenMontage a `requirements.txt`. Todos los desarrolladores lo instalan en su venv. El deployment lo incluye en la imagen. Las dependencias principales son livianas (pyyaml, pydantic, Pillow, numpy, etc.) pero el equipo tiene 4 desarrolladores y solo uno (sebas) trabaja en video.

2. **Git submodule** — OpenMontage vive en `openmontage/` en el árbol del repo. No toca `requirements.txt`. Los otros desarrolladores solo lo ven si hacen `git submodule update --init`. El deployment lo incluye si y solo si el servicio de video lo necesita.

3. **Copiar archivos específicos** — copiar solo `tools/audio/audio_mixer.py`, `remotion-composer/`, etc. en el código base. Máximo aislamiento, pero sin actualizaciones upstream.

## Decisión

Usar **git submodule** (Opción 2). OpenMontage se añade como submódulo en la raíz del repositorio, apuntado a un commit específico (no a una rama). El equipo de video es responsable de actualizar el submódulo cuando sea necesario.

**Justificación contra `pip install`:**
- Afecta el entorno de los otros 3 desarrolladores (deben reinstalar dependencias aunque no toquen video).
- Aumenta el tamaño del venv y la imagen de deployment con 52 herramientas que la mayoría del equipo no usa.

**Justificación contra copiar archivos:**
- OpenMontage evoluciona rápido (35k+ estrellas, commits semanales). Perder actualizaciones en `audio_mixer.py` o `remotion-composer/` significa mantener fixes manualmente.
- Las herramientas de OpenMontage heredan de `BaseTool` en `tools/base_tool.py` — copiar archivos requiere arrastrar también la clase base y el registro.

## Consecuencias

**Positivo:**
- Aislamiento completo para los otros desarrolladores — solo sebas y el deployment de video lo conocen.
- Actualizaciones disponibles: `git submodule update --remote` cuando se necesiten.
- El equipo puede bifurcar el submódulo si necesita modificar herramientas de OpenMontage.
- `requirements.txt` no cambia — las dependencias de OpenMontage se importan desde el submódulo.

**Negativo:**
- Cada clon del repo requiere `git submodule update --init --recursive`.
- El submódulo añade ~30MB al checkout (la mayoría YAML/Markdown, no Python).
- Las rutas de import (`from openmontage.tools.audio...`) requieren añadir `openmontage/` al `sys.path` o usar `PYTHONPATH`.
- El CI/CD debe configurarse para inicializar submódulos.

**Condicionado a:**
- ADR-0008 (Remotion Composition Engine) — el proyecto `remotion-composer/` vive dentro del submódulo.
- `apps/api/config/settings.py` debe configurar la ruta al submódulo y al proyecto Remotion.

## Instrucciones de setup

```bash
# Clonar el repo con submódulos
git clone git@github.com:xertica/xertica-education.git
cd xertica-education
git submodule update --init --recursive

# O añadir a un clon existente
git submodule add https://github.com/calesthio/OpenMontage.git openmontage
git submodule update --init --recursive
```
