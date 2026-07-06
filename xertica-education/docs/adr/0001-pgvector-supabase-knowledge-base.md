# ADR-0001: pgvector en Supabase como Knowledge Base

- **Estado:** Aceptado
- **Ámbito:** Knowledge Base (KB) / RAG

## Contexto

El MVP necesita búsquedas semánticas con citas (RAG) sobre las fuentes validadas, sin sumar infraestructura dedicada de vector store.

## Decisión

Se selecciona PostgreSQL con la extensión **pgvector** integrada de **Supabase** como base de conocimiento, reutilizando la base de datos principal para las búsquedas semánticas del MVP.

## Consecuencias

- Simplicidad de infraestructura: una sola base de datos para persistencia y búsqueda vectorial.
- Menor flexibilidad frente a un vector store especializado si el volumen crece más allá del MVP.
