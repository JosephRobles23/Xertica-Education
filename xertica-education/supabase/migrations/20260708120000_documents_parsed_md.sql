-- ADR-0013: parse-at-upload. El documento se parsea a Markdown verbatim en el
-- momento de la subida y se cachea en `parsed_md` (regenerable desde el binario).
-- Lo consumen generate-structure (contexto) y la ingesta de Gate 1 (sin re-parsear).

alter table public.documents
    add column if not exists parsed_md text;  -- null = parse pendiente o fallido

-- `use_as_source` queda deprecado (ADR-0013): todo upload entra a la KB por default.
-- Se mantiene la columna por compatibilidad; su default pasa a true.
alter table public.documents alter column use_as_source set default true;
