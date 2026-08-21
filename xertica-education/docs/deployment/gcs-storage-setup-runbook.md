# Runbook — Habilitar storage en GCS (cuenta `gavynenita@gmail.com`)

Pasos concretos para crear el bucket de GCS, sus permisos y las variables de
entorno, ejecutados con la cuenta **`gavynenita@gmail.com`**. Resuelve el error
`HTTP 413 "The object exceeded the maximum allowed size"` que da Supabase Free
(tope de 50 MiB) al subir los videos renderizados (~50 MB).

Para la explicación genérica del backend ver [`gcs-storage-setup.md`](./gcs-storage-setup.md).

---

## Contexto de proyectos (importante)

| Recurso | Proyecto | Notas |
| :-- | :-- | :-- |
| Owner de deploy | `gavynenita@gmail.com` | **owner** de `xertica-staging` (nº 22577018525) |
| Cloud Run (API) | `xertica-staging` | genera lesson/quiz/lab |
| SA del render (sube el video) | `xertica-agent-courses` | `xertica-tts@xertica-agent-courses.iam.gserviceaccount.com` (JSON de Veo) |

> El bucket se crea en **`xertica-staging`** (donde gavynenita es owner) y se le
> da permiso **cross-project** a la SA del render, que vive en
> `xertica-agent-courses`. Es válido: el nombre de bucket es global y el acceso
> se controla por IAM.
>
> ⚠️ Si tu project ID real no es `xertica-staging`, ajusta `PROJECT` abajo.

---

## 0. Variables

```bash
export ACCOUNT=gavynenita@gmail.com
export PROJECT=xertica-staging                 # ⚠️ cambia si tu project ID es otro
export BUCKET=xertica-education-assets          # nombre global único en GCS
export REGION=us-central1                       # misma región que Veo/Cloud Run
export RENDER_SA=xertica-tts@xertica-agent-courses.iam.gserviceaccount.com
```

## 1. Autenticarse como gavynenita y fijar proyecto

```bash
gcloud auth login $ACCOUNT
gcloud config set account $ACCOUNT
gcloud config set project $PROJECT
```

## 2. Habilitar la API de Storage

```bash
gcloud services enable storage.googleapis.com --project $PROJECT
```

## 3. Crear el bucket

```bash
gcloud storage buckets create gs://$BUCKET --project=$PROJECT --location=$REGION --uniform-bucket-level-access
```

> Si da `409 conflict`, ese nombre ya está tomado en GCS (namespace global):
> usa otro, p. ej. `xertica-education-assets-staging`, y ajusta `BUCKET` y
> `STORAGE_BUCKET` en consecuencia.

## 4. Lectura pública

Las URLs devueltas son `https://storage.googleapis.com/<bucket>/<path>`, que
requieren lectura pública (igual que las URLs públicas de Supabase):

```bash
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=allUsers --role=roles/storage.objectViewer
```

> Si una org policy de *domain restricted sharing* bloquea `allUsers`, hay que
> cambiar el adapter a **signed URLs** (config + ajuste en `adapters/storage/gcs.py`).

## 5. Permiso de escritura para la SA del render (cross-project)

```bash
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=serviceAccount:$RENDER_SA --role=roles/storage.objectAdmin
```

---

## 6. Variables de entorno (activar GCS en el código)

El código soporta ambos backends vía `settings.storage_backend`. Activar GCS:

| Variable | Valor |
| :-- | :-- |
| `STORAGE_BACKEND` | `gcs` |
| `STORAGE_BUCKET` | `xertica-education-assets` (el mismo `$BUCKET`) |

- **Modal** (render del video): añadir ambas al Secret `xertica-secrets-staging`
  en el dashboard de Modal. La imagen ya instala `google-cloud-storage`
  (`apps/api/pyproject.toml`) y ya materializa la SA desde
  `GOOGLE_APPLICATION_CREDENTIALS_JSON` (ver `modal_render.py`).
- **Cloud Run** (`xertica-staging`): mismas dos para que lesson/quiz/lab también
  vayan a GCS y las URLs sean consistentes.

  Primero obtén el nombre real del servicio (no uses `<...>`, bash lo interpreta
  como redirección):

  ```bash
  gcloud run services list --project $PROJECT --region $REGION --format="value(SERVICE)"
  ```

  Luego, con el nombre real:

  ```bash
  gcloud run services update NOMBRE_DEL_SERVICIO --project $PROJECT --region $REGION --update-env-vars STORAGE_BACKEND=gcs,STORAGE_BUCKET=$BUCKET
  ```

---

## 7. Verificar

```bash
# El bucket existe y es tuyo
gcloud storage buckets describe gs://$BUCKET --project $PROJECT --format="value(name,location)"
```

**Opción A — como tu cuenta** (eres owner del bucket; verifica que escribe):

```bash
echo "ping" | gcloud storage cp - gs://$BUCKET/_healthcheck.txt && gcloud storage rm gs://$BUCKET/_healthcheck.txt
```

**Opción B — como la SA del render** (prueba end-to-end, usando su propia key,
sin impersonar; es como se autentica el render en Modal):

```bash
gcloud auth activate-service-account --key-file=/home/user/Projects/Xertica-Education/xertica-education/apps/api/xertica-agent-courses-7350cabab6e4.json
echo "ping" | gcloud storage cp - gs://$BUCKET/_healthcheck.txt && gcloud storage rm gs://$BUCKET/_healthcheck.txt
gcloud config set account gavynenita@gmail.com
```

> No uses `--impersonate-service-account=$RENDER_SA`: requiere que tu cuenta tenga
> `roles/iam.serviceAccountTokenCreator` sobre esa SA (vive en `xertica-agent-courses`,
> donde gavynenita no tiene permisos). El render NO impersona — usa la key JSON
> directamente — así que esto no afecta al funcionamiento.

Tras redeploy (Modal + Cloud Run), lanza un render de video: en los logs de Modal
la subida debe pasar sin el 413 y la URL final debe ser
`https://storage.googleapis.com/...`. Si algo falla, el job ahora marca **FAILED
con la causa** en vez de devolver una URL `http://localhost` inalcanzable.

---

## Alternativa sin cross-project

Crear el bucket en `xertica-agent-courses` (donde ya vive la SA del render) y
omitir el paso 5. Requiere que la cuenta que ejecuta tenga permisos en ese
proyecto — según los docs, `gavynenita@gmail.com` **no** los tiene (solo es owner
de `xertica-staging`), por eso este runbook usa la ruta cross-project.
