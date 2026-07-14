# Guía de deploy — staging (Vercel + Cloud Run + Modal)

Paso a paso, **desde la terminal**, para dejar corriendo el CI/CD de la rama
`staging`. Complementa a [`SETUP.md`](../../../SETUP.md) (raíz del repo) con los
comandos exactos.

> ⚠️ **Windows: usa Git Bash, NO `cmd.exe` ni PowerShell.**
> Todos los comandos usan sintaxis bash (`export VAR=...`, `$VAR`, bucles
> `for`). En `cmd.exe` las variables son `%VAR%`, así que `$PROJECT_ID` se pasa
> **literal** y gcloud falla con `Bad value [$PROJECT_ID]`. Abre **Git Bash**
> (menú Inicio → escribe «Git Bash»; viene con Git for Windows) y corre TODO
> ahí. Los `gcloud`, `gh` y `modal` que instalaste funcionan igual dentro de
> Git Bash.
>
> Si prefieres PowerShell: define variables con `$env:PROJECT_ID = "xertica-staging"`
> y úsalas como `$env:PROJECT_ID`, pero los bucles `for` de esta guía no
> funcionan igual — Git Bash es el camino sin fricción.

**Arquitectura (Opción B):**

| Pieza | Host | Se despliega con |
|---|---|---|
| Web (`apps/web`) | Vercel | Integración Git nativa |
| API (`apps/api`) | Google Cloud Run | GitHub Actions (`deploy-api`, auth WIF) |
| Render (`modal_render.py`) | Modal | GitHub Actions (`deploy-render`) |
| Estado + Storage | Supabase | Compartido con dev |

> Variables que usaremos (ajústalas): repo `JosephRobles23/Xertica-Education`,
> región Cloud Run `southamerica-west1`, app Modal `xertica-render-staging`.

---

## 0. Prerrequisitos (instalar CLIs)

```bash
# Google Cloud CLI
#   https://cloud.google.com/sdk/docs/install  (instálalo según tu SO)
gcloud version

# GitHub CLI (para setear secrets desde la terminal)
#   https://cli.github.com/
gh --version
gh auth login          # loguéate una vez

# Modal CLI
pip install modal
modal --version
```

Cuentas necesarias (créalas en el navegador si no las tienes): **Google Cloud**
(con una cuenta de facturación activa — el free tier de Cloud Run no cobra, pero
GCP exige billing vinculado), **GitHub**, **Modal**, **Vercel**, **Supabase**.

---

## 1. Google Cloud — crear proyecto y configurar todo

### 1.1 Login y variables base

> Recuerda: esto va en **Git Bash** (ver aviso arriba). En `cmd.exe` fallaría
> con `Bad value [$PROJECT_ID]`.

```bash
gcloud auth login              # abre el navegador para autenticarte

# Elige un PROJECT_ID único a nivel global (añade un sufijo si está tomado,
# p.ej. xertica-staging-2). Debe ser lowercase, 6–30 chars, empezar con letra.
export PROJECT_ID="xertica-staging"
export REPO="JosephRobles23/Xertica-Education"
export REGION="southamerica-west1"
```

### 1.2 Crear el proyecto

> **¿`Cloud billing quota exceeded` al vincular facturación (§1.3)?** Tu cuenta
> de facturación llegó al límite de proyectos que puede tener vinculados (común
> en cuentas nuevas/free-trial). Lo más rápido: **reutiliza un proyecto que ya
> tenga billing**, p.ej. tu proyecto de IA `xertica-agent-courses`. Salta la
> creación y el vínculo de billing, y usa:
> ```bash
> export PROJECT_ID="xertica-agent-courses"
> gcloud config set project "$PROJECT_ID"
> ```
> Luego continúa directo en **§1.4**. El servicio de Cloud Run se sigue llamando
> `xertica-api-staging`; solo vive dentro de ese proyecto. (Tradeoff: mezclas
> staging con tu proyecto de IA — aceptable para un MVP, igual que compartir
> Supabase.)

```bash
gcloud projects create "$PROJECT_ID" --name="Xertica Education Staging"
gcloud config set project "$PROJECT_ID"
```

### 1.3 Vincular facturación

```bash
# Lista tus cuentas de facturación y copia el ACCOUNT_ID (formato XXXXXX-XXXXXX-XXXXXX)
gcloud billing accounts list

export BILLING_ACCOUNT="0112A3-BB8374-5E031F"
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
```

> Si no tienes ninguna cuenta de facturación, créala una vez en la consola web:
> <https://console.cloud.google.com/billing> y repite el `link`.

### 1.4 Habilitar las APIs necesarias

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com
```

### 1.5 Service account que usará GitHub Actions

```bash
gcloud iam service-accounts create gh-deployer \
  --display-name="GitHub Actions deployer"

export SA_EMAIL="gh-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# Roles mínimos para construir (Cloud Build) y desplegar a Cloud Run desde --source
for ROLE in run.admin cloudbuild.builds.editor artifactregistry.admin \
            iam.serviceAccountUser storage.admin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/${ROLE}"
done
```

### 1.6 Workload Identity Federation (login keyless desde GitHub)

```bash
# Pool
gcloud iam workload-identity-pools create github-pool \
  --location=global --display-name="GitHub pool"

# Provider OIDC, restringido SOLO a tu repo
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Permitir que el repo impersone la service account
export POOL_ID=$(gcloud iam workload-identity-pools describe github-pool \
  --location=global --format="value(name)")

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${REPO}"
```

### 1.7 Obtener los 3 valores para GitHub

```bash
echo "GCP_PROJECT_ID      = $PROJECT_ID"
echo "GCP_SERVICE_ACCOUNT = $SA_EMAIL"
echo -n "GCP_WIF_PROVIDER    = "
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global --workload-identity-pool=github-pool \
  --format="value(name)"
```

Guárdalos; los pegas en el paso 2.

---

## 2. GitHub — secrets (desde la terminal con `gh`)

Corre esto en la raíz del repo (autenticado con `gh auth login`). Reemplaza los
valores reales:

```bash
gh secret set GCP_PROJECT_ID       --body "$PROJECT_ID"
gh secret set GCP_SERVICE_ACCOUNT  --body "$SA_EMAIL"
gh secret set GCP_WIF_PROVIDER     --body "$(gcloud iam workload-identity-pools providers describe github-provider --location=global --workload-identity-pool=github-pool --format='value(name)')"

gh secret set SUPABASE_URL         --body "https://XXXX.supabase.co"
gh secret set SUPABASE_KEY         --body "<service-role-key>"
gh secret set OPENROUTER_KEY       --body "<tu-openrouter-key>"

gh secret set MODAL_TOKEN_ID       --body "<modal-token-id>"      # ver paso 3
gh secret set MODAL_TOKEN_SECRET   --body "<modal-token-secret>"  # ver paso 3
```

Referencia de secrets:

| Secret | Qué es |
|---|---|
| `GCP_PROJECT_ID` | ID del proyecto GCP |
| `GCP_SERVICE_ACCOUNT` | Email de la SA deployer |
| `GCP_WIF_PROVIDER` | Ruta del provider WIF |
| `SUPABASE_URL` / `SUPABASE_KEY` | Proyecto Supabase (compartido con dev) |
| `OPENROUTER_KEY` | LLM principal de la app (scriptwriter, quiz, lesson, lab…) |
| `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` | Tokens de Modal para CI |

> Verifica con `gh secret list`.

---

## 3. Modal — tokens y secret de runtime

### 3.1 Login local

```bash
modal token new     # abre el navegador y guarda el token en ~/.modal.toml
```

### 3.2 Tokens para CI

Opción A — reutiliza el token local:

```bash
cat ~/.modal.toml   # copia token_id y token_secret → secrets de GitHub (paso 2)
```

Opción B — crea uno dedicado en el dashboard: <https://modal.com/settings/tokens>.

### 3.3 Crear el secret de runtime (`xertica-secrets-staging`)

Todo lo que la app necesita **dentro del render**. Incluye las credenciales de
Vertex AI (Veo/Imagen) como JSON inline:

```bash
modal secret create xertica-secrets-staging \
  SUPABASE_URL="https://XXXX.supabase.co" \
  SUPABASE_KEY="<service-role-key>" \
  OPENROUTER_KEY="<tu-openrouter-key>" \
  PIXABAY_API_KEY="<tu-pixabay-key>" \
  GOOGLE_CLOUD_PROJECT="xertica-agent-courses" \
  GOOGLE_CLOUD_LOCATION="us-central1" \
  GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat /ruta/a/tu/vertex-sa.json)"
```

> **¿No tienes el JSON de Vertex?** Es la service account que ya usas en local
> para Veo/Imagen (proyecto `xertica-agent-courses`). Si necesitas generarla:
> ```bash
> gcloud iam service-accounts create vertex-render \
>   --project=xertica-agent-courses --display-name="Vertex render"
> gcloud projects add-iam-policy-binding xertica-agent-courses \
>   --member="serviceAccount:vertex-render@xertica-agent-courses.iam.gserviceaccount.com" \
>   --role="roles/aiplatform.user"
> gcloud iam service-accounts keys create vertex-sa.json \
>   --iam-account="vertex-render@xertica-agent-courses.iam.gserviceaccount.com"
> ```

Deploy manual de la función (opcional, para validar la imagen antes del CI):

```bash
cd xertica-education
MODAL_RENDER_APP=xertica-render-staging modal deploy modal_render.py
```

---

## 4. Vercel — configurar la web

En <https://vercel.com> → tu proyecto → **Settings**:

- **Root Directory:** `xertica-education/apps/web`
- **Ignored Build Step** (no reconstruir si solo cambió API/render):
  ```bash
  git diff --quiet HEAD^ HEAD -- xertica-education/apps/web/
  ```
- **Environment Variables:** `NEXT_PUBLIC_API_URL` = la URL de Cloud Run (la
  obtienes tras el primer deploy del API, paso 5).

---

## 5. Primer deploy y verificación

```bash
# Estás en la rama staging con la infra ya commiteada
git push -u origin staging
```

1. **GitHub → Actions:** verás correr `deploy-staging`. La primera vez corren
   `deploy-api` y `deploy-render` (todo cambió). El build de la imagen de Modal
   tarda unos minutos.
2. **Verifica el API:**
   ```bash
   gcloud run services describe xertica-api-staging \
     --region "$REGION" --format="value(status.url)"
   curl "$(gcloud run services describe xertica-api-staging --region "$REGION" --format='value(status.url)')/"
   # → {"message":"Xertica Education API is active."}
   ```
3. **Verifica Modal:**
   ```bash
   modal app list        # debe aparecer xertica-render-staging
   ```
4. **Conecta la web:** pon esa URL en `NEXT_PUBLIC_API_URL` (Vercel, paso 4) y
   prueba un render end-to-end desde la UI.

> Deja terminar **ambos** jobs antes de probar: el API hace `.spawn()` a la
> función Modal, así que Modal debe estar desplegado primero.

---

## 6. Troubleshooting

| Síntoma | Causa probable / fix |
|---|---|
| `Cloud billing quota exceeded` al vincular billing | La cuenta de facturación llegó a su tope de proyectos. Reutiliza un proyecto ya facturado (`xertica-agent-courses`, ver §1.2), libera un proyecto viejo (`gcloud billing projects unlink …`), o pide aumento de cuota en el link del error. |
| `deploy-api` falla en el build por permisos | Agrega a `$SA_EMAIL` el rol que pida el error y reintenta. |
| `PERMISSION_DENIED` al autenticar WIF | La `attribute-condition` del provider no coincide con `$REPO`, o falta el binding `workloadIdentityUser`. |
| El render queda en `RUNNING` y no avanza | Revisa `modal app logs xertica-render-staging`; suele ser un secret de runtime faltante (Vertex/Supabase). |
| `.spawn()` falla con "function not found" | La función Modal aún no está desplegada; corre `deploy-render` o el `modal deploy` manual. |
| El API arranca pero no crea jobs | Falta `SUPABASE_URL`/`SUPABASE_KEY` en el `--set-env-vars` de Cloud Run. |

---

## Referencia rápida de recursos creados

- **GCP:** proyecto `xertica-staging`, SA `gh-deployer@…`, WIF pool `github-pool`.
- **Cloud Run:** servicio `xertica-api-staging` (`southamerica-west1`).
- **Modal:** app `xertica-render-staging`, secret `xertica-secrets-staging`.
- **GitHub:** 8 secrets (ver paso 2).
- **Vercel:** proyecto con Root Directory `xertica-education/apps/web`.
