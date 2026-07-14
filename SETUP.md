# Setup de deploy — staging (Opción B)

Guía para dejar corriendo el CI/CD de la rama **`staging`**:

| Pieza | Dónde corre | Cómo se despliega |
|---|---|---|
| **Web** (`apps/web`) | Vercel | Integración Git nativa de Vercel (no pasa por GitHub Actions) |
| **API** (`apps/api`) | Google Cloud Run | `deploy-api` en `.github/workflows/deploy.yml` (auth WIF) |
| **Render** (`modal_render.py` + composer) | Modal | `deploy-render` → `modal deploy` |
| **Estado + Storage** | Supabase | Compartido con dev (mismo proyecto) |

> El API es liviano y solo **dispara** el render en Modal con `.spawn()`. En dev
> local, sin `MODAL_RENDER_APP` configurado, el render sigue corriendo
> in-process como siempre — no necesitas Modal para desarrollar.

---

## 1. Secrets de GitHub (Settings → Secrets and variables → Actions)

| Secret | Qué es |
|---|---|
| `GCP_WIF_PROVIDER` | Ruta del provider de Workload Identity (paso 2) |
| `GCP_SERVICE_ACCOUNT` | Email de la service account deployer (paso 2) |
| `GCP_PROJECT_ID` | ID del proyecto GCP (p.ej. `xertica-staging`) |
| `SUPABASE_URL` | URL de tu proyecto Supabase |
| `SUPABASE_KEY` | Service-role key de Supabase |
| `OPENROUTER_KEY` | Key de OpenRouter (LLM) |
| `MODAL_TOKEN_ID` | Token de Modal para CI (paso 3) |
| `MODAL_TOKEN_SECRET` | Token de Modal para CI (paso 3) |

> Son **secrets de CI** (para desplegar). Los **secrets de runtime** de la app
> viven en cada plataforma: Cloud Run env (los inyecta el workflow) y el Modal
> Secret `xertica-secrets-staging` (paso 3).

---

## 2. GCP + Workload Identity Federation (keyless)

Corre esto una vez con `gcloud` (necesitas la CLI de Google Cloud instalada y
logueada con una cuenta con permisos de facturación/owner):

```bash
export PROJECT_ID=xertica-staging
export REPO=JosephRobles23/Xertica-Education

# Crear el proyecto (o usa uno existente) y seleccionarlo
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
# (asocia una cuenta de facturación desde la consola si el proyecto es nuevo)

# Habilitar APIs necesarias
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com iamcredentials.googleapis.com

# Service account que usará GitHub Actions para desplegar
gcloud iam service-accounts create gh-deployer --display-name="GitHub Actions deployer"
export SA_EMAIL=gh-deployer@$PROJECT_ID.iam.gserviceaccount.com

# Roles para construir (Cloud Build) y desplegar a Cloud Run desde --source
for ROLE in run.admin cloudbuild.builds.editor artifactregistry.admin \
            iam.serviceAccountUser storage.admin; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" --role="roles/$ROLE"
done

# Pool + provider de Workload Identity, restringido a TU repo
gcloud iam workload-identity-pools create github-pool \
  --location=global --display-name="GitHub pool"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global --workload-identity-pool=github-pool \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='$REPO'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Permitir que el repo impersone la service account
export POOL_ID=$(gcloud iam workload-identity-pools describe github-pool \
  --location=global --format="value(name)")
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/$REPO"

# Valores para los secrets de GitHub:
echo "GCP_SERVICE_ACCOUNT = $SA_EMAIL"
echo "GCP_PROJECT_ID      = $PROJECT_ID"
echo -n "GCP_WIF_PROVIDER    = "
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global --workload-identity-pool=github-pool \
  --format="value(name)"
```

Pega esos tres valores en los secrets de GitHub.

> Si el primer deploy falla en el build por permisos, agrega el rol que pida el
> error a `$SA_EMAIL` y reintenta.

---

## 3. Modal (render)

```bash
pip install modal
modal token new            # login local (una vez, para deploy manual y pruebas)
```

**Tokens para CI:** en modal.com → *Settings → API Tokens* crea un token y pega
`MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` en los secrets de GitHub.

**Secret de runtime** (todo lo que la app necesita en el render). Créalo con TODO
tu `apps/api/.env` real. Ejemplo mínimo:

```bash
modal secret create xertica-secrets-staging \
  SUPABASE_URL="https://xxxx.supabase.co" \
  SUPABASE_KEY="<service-role-key>" \
  OPENROUTER_KEY="<...>" \
  PIXABAY_API_KEY="<...>" \
  GOOGLE_CLOUD_PROJECT="xertica-agent-courses" \
  GOOGLE_CLOUD_LOCATION="us-central1" \
  GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat ruta/a/tu/vertex-sa.json)"
```

> El render usa **Vertex AI** (Veo/Imagen). Por eso incluye
> `GOOGLE_APPLICATION_CREDENTIALS_JSON` con el JSON de la service account de
> Vertex; `modal_render.py` lo materializa a un archivo automáticamente.

Primer deploy manual (opcional, para validar la imagen):

```bash
cd xertica-education && modal deploy modal_render.py
```

---

## 4. Vercel (web)

En el proyecto de Vercel → *Settings*:

- **Root Directory:** `xertica-education/apps/web`
- **Ignored Build Step** (para no reconstruir cuando cambia solo el API/render):

  ```bash
  git diff --quiet HEAD^ HEAD -- xertica-education/apps/web/
  ```

- **Environment Variables:** la URL pública del API en Cloud Run (p.ej.
  `NEXT_PUBLIC_API_URL`) una vez que exista tras el primer deploy.

Con eso, cada push a `staging` genera un preview y cada merge a la rama de
producción de Vercel despliega la web.

---

## 5. Primer deploy

1. Completa los pasos 1–4.
2. Haz push de la rama `staging`:
   ```bash
   git push -u origin staging
   ```
3. En GitHub → *Actions* verás correr `deploy-staging`. La primera vez corren
   **ambos** jobs (todo cambió); deja que terminen los dos antes de probar
   (el API hace `.spawn()` a la función Modal, así que Modal debe estar
   desplegado). El build de la imagen del render tarda unos minutos.
4. Configura `NEXT_PUBLIC_API_URL` en Vercel con la URL de Cloud Run y prueba
   un render end-to-end.

## Dev local (sin cambios)

Nada de esto afecta tu flujo local: sin `MODAL_RENDER_APP` en tu `.env`, el
render corre in-process como hasta ahora.
