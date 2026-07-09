const DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.file'

type GoogleScriptName = 'api' | 'gsi'

export interface GoogleDriveSelection {
  file_id: string
  name: string
  mime_type: string
  web_view_link?: string
  access_token: string
}

interface PickerDocument {
  id: string
  name: string
  mimeType: string
  url?: string
}

interface PickerResponse {
  action: string
  docs: PickerDocument[]
}

const scriptSources: Record<GoogleScriptName, string> = {
  api: 'https://apis.google.com/js/api.js',
  gsi: 'https://accounts.google.com/gsi/client',
}

function loadScript(name: GoogleScriptName) {
  const id = `google-${name}-script`
  return new Promise<void>((resolve, reject) => {
    if (document.getElementById(id)) {
      resolve()
      return
    }

    const script = document.createElement('script')
    script.id = id
    script.src = scriptSources[name]
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`No se pudo cargar Google ${name}`))
    document.head.appendChild(script)
  })
}

function loadPickerApi() {
  return new Promise<void>((resolve) => {
    window.gapi.load('picker', () => resolve())
  })
}

function requestDriveToken(clientId: string) {
  return new Promise<string>((resolve, reject) => {
    const tokenClient = window.google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: DRIVE_SCOPE,
      callback: (response) => {
        if (response.error || !response.access_token) {
          reject(new Error(response.error || 'No se pudo autorizar Google Drive'))
          return
        }
        resolve(response.access_token)
      },
    })
    tokenClient.requestAccessToken({ prompt: 'consent' })
  })
}

export async function pickGoogleDriveFile(): Promise<GoogleDriveSelection | null> {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_DRIVE_API_KEY
  const appId = process.env.NEXT_PUBLIC_GOOGLE_DRIVE_APP_ID

  if (!clientId || !apiKey) {
    throw new Error('Faltan NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID y NEXT_PUBLIC_GOOGLE_DRIVE_API_KEY')
  }

  await Promise.all([loadScript('api'), loadScript('gsi')])
  await loadPickerApi()
  const accessToken = await requestDriveToken(clientId)

  return new Promise((resolve) => {
    const view = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
      .setIncludeFolders(false)
      .setSelectFolderEnabled(false)

    const picker = new window.google.picker.PickerBuilder()
      .setOAuthToken(accessToken)
      .setDeveloperKey(apiKey)
      .addView(view)
      .setCallback((data: PickerResponse) => {
        if (data.action === window.google.picker.Action.PICKED) {
          const doc = data.docs[0] as PickerDocument
          resolve({
            file_id: doc.id,
            name: doc.name,
            mime_type: doc.mimeType,
            web_view_link: doc.url,
            access_token: accessToken,
          })
        }
        if (data.action === window.google.picker.Action.CANCEL) {
          resolve(null)
        }
      })

    if (appId) picker.setAppId(appId)
    picker.build().setVisible(true)
  })
}

export async function authorizeGoogleDrive() {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID
  if (!clientId) {
    throw new Error('Falta NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID')
  }
  await loadScript('gsi')
  return requestDriveToken(clientId)
}
