# Xertica Education · Estudio (Vite + React)

Migración del mockup HTML (`Xertica Education.dc.html`) a un proyecto **Vite + React**
con enrutamiento por `react-router-dom` y drag & drop con `@dnd-kit`.

## Correr

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # build de producción a /dist
npm run preview  # sirve el build
```

## Rutas (app router)

| Ruta | Página |
|------|--------|
| `/` | Dashboard · Rutas de aprendizaje |
| `/nueva-ruta` | Nueva ruta (brief + upload de estructura + deep research YouTube) |
| `/estructura-propuesta` | Estructura propuesta (drag & drop para reordenar) |
| `/ruta/:id` | Detalle de ruta (corpus + módulos + generar contenido) |
| `/ruta/:id/video-storyboard` | Revisar guion y storyboard (desde el Video) |
| `/ruta/:id/asset-final` | Revisar asset final (desde "Generar contenido") |
| `/publicado` | Publicado a Classroom |

Todas las páginas navegan entre sí y permiten volver atrás (topbar/sidebar/botones).

## Cambios aplicados respecto al mockup

1. **Botón "Generar contenido"** al final de Módulos en `/ruta` → genera el material de todos los módulos.
2. **Enrutamiento por app router** en todas las páginas.
3. **Eliminada** la página "Configurar generación".
4. **"Estructura propuesta"** movida a su propia página, fuera de "Nueva ruta".
5. **Upload de estructura** en "Nueva ruta": modal con DOCX / PDF / texto.
6. **Drag & drop** para reordenar módulos en "Estructura propuesta" (`@dnd-kit`).
7. **Eliminados todos los componentes de estimación de costos** (cajas de costo, cifras en cards, provenance, sidebar).
8. **Toggle de agente deep research** para buscar video de YouTube en "Nueva ruta".
9. Cada contenido (Lesson, Video, Infografía, Quiz, Laboratorio) es **colapsable** con
   **preview**, y botones **Aprobar** y **Refinar** (popover con prompt).
10. **Eliminado** el botón "Configurar módulo" (y su página).
11. **"Revisar corpus de fuentes"** ahora es una sección dentro de `/ruta`, debajo del
    objetivo y encima de Módulos.
12. **Botón "Generar contenido"** al final de la sección de Módulos.
13. **"Revisar guion y storyboard"** se abre desde el contenido **Video**; al aprobar vuelve a `/ruta`.
14. **"Revisar asset final"** aparece tras pulsar "Generar contenido".

## Estructura

```
src/
  main.jsx            # entry + BrowserRouter + store
  App.jsx             # definición de rutas
  store.jsx           # estado compartido (proposal, deep research, upload)
  theme.js            # tokens de diseño (colores, fuentes)
  data.js             # datos estáticos clonados del mockup
  components/
    Layout.jsx        # topbar + sidebar + breadcrumbs
    ui.jsx            # átomos (Eyebrow, StatusBadge, Card, ...)
    UploadModal.jsx   # modal de subida de estructura
    RefinePopover.jsx # popover de refinar contenido
  pages/
    Dashboard.jsx  NuevaRuta.jsx  EstructuraPropuesta.jsx
    Ruta.jsx  Storyboard.jsx  AssetFinal.jsx  Publicado.jsx
```
