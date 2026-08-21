# Storage en Google Cloud Storage (GCS)

Motivo: **Supabase Free limita cada objeto a 50 MiB**, y los videos renderizados
(~50 MB) fallan al subir con `HTTP 413 "The object exceeded the maximum allowed size"`.
GCS no tiene ese tope pequeño. Este documento deja el storage de artefactos en GCS.

El código ya soporta ambos backends vía `settings.storage_backend` (`supabase` | `gcs`)
y el factory `adapters/storage/get_storage_adapter()`. Solo falta el setup de infra + env.

## 1. Crear el bucket (una vez)

Usa el mismo proyecto y la service account que ya usan Veo/Imagen.

```bash
export PROJECT_ID=<tu-project-id>
export BUCKET=xertica-education-assets            # debe ser único a nivel global
export REGION=us-central1

gcloud storage buckets create gs://$BUCKET --project=$PROJECT_ID --location=$REGION --uniform-bucket-level-access
```

## 2. Permitir lectura pública

El adapter devuelve URLs `https://storage.googleapis.com/<bucket>/<path>`, que
requieren lectura pública (igual que las URLs públicas de Supabase):

```bash
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=allUsers --role=roles/storage.objectViewer
```

> Si prefieres NO exponer el bucket públicamente, habría que cambiar el adapter a
> URLs firmadas (signed URLs). No es lo actual; abrir un issue si se requiere.

## 3. Permisos de escritura para la service account

La SA de `GOOGLE_APPLICATION_CREDENTIALS` (la misma de Veo/Imagen) debe poder subir:

```bash
export SA_EMAIL=<tu-sa>@$PROJECT_ID.iam.gserviceaccount.com

gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=serviceAccount:$SA_EMAIL --role=roles/storage.objectAdmin
```

## 4. Variables de entorno

Activar el backend GCS donde se generan artefactos:

| Variable | Valor |
| :-- | :-- |
| `STORAGE_BACKEND` | `gcs` |
| `STORAGE_BUCKET` | `xertica-education-assets` (el nombre del bucket GCS) |

- **Modal** (donde corre el render del video): añadir ambas al Secret
  `xertica-secrets-staging`. La imagen ya instala `google-cloud-storage`
  (está en `apps/api/pyproject.toml`) y ya materializa la SA desde
  `GOOGLE_APPLICATION_CREDENTIALS_JSON` (ver `modal_render.py`).
- **Cloud Run** (API que genera lesson/quiz/lab): añadir las mismas dos para que
  esos artefactos también vayan a GCS y las URLs sean consistentes.

## 5. Verificar

Tras redeploy (Modal + Cloud Run), lanza un render de video. En los logs de Modal
debe aparecer la subida sin el 413 y la URL final `https://storage.googleapis.com/...`.
Si algo falla, el job ahora marca **FAILED con la causa** en vez de devolver una URL
`http://localhost` inalcanzable (el fallback silencioso se eliminó).
