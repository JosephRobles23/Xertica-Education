// Ambient declarations for non-code side-effect imports (global stylesheets).
declare module '*.css'

interface Window {
  gapi: {
    load(api: string, callback: () => void): void
  }
  google: {
    accounts: {
      oauth2: {
        initTokenClient(config: {
          client_id: string
          scope: string
          callback: (response: { access_token?: string; error?: string }) => void
        }): {
          requestAccessToken(options?: { prompt?: string }): void
        }
      }
    }
    picker: {
      Action: { PICKED: string; CANCEL: string }
      DocsView: new (viewId: string) => {
        setIncludeFolders(value: boolean): any
        setSelectFolderEnabled(value: boolean): any
      }
      PickerBuilder: new () => {
        setOAuthToken(token: string): any
        setDeveloperKey(key: string): any
        setAppId(appId: string): any
        addView(view: any): any
        setCallback(callback: (data: { action: string; docs: unknown[] }) => void): any
        build(): { setVisible(value: boolean): void }
      }
      ViewId: { DOCS: string }
    }
  }
}
