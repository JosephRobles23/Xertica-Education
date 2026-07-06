import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useEffect,
  type ReactNode,
} from 'react'
import type { ContentKind, ContentStatus, ProposalModule, LearningRoute } from '@/lib/types'
import { INITIAL_PROPOSAL, ROUTES } from '@/data/routes'
import { api, type JobState } from '@/lib/api'

/** Clave estable para el estado de un contenido concreto. */
const contentKey = (routeId: string, moduleId: string, kind: ContentKind) =>
  `${routeId}:${moduleId}:${kind}` as const

export interface UploadedStructure {
  name: string
  kind: 'archivo' | 'texto'
}

interface AppStore {
  /* Gate 0 · Nueva ruta */
  briefText: string
  setBriefText: (v: string) => void
  deepResearch: boolean
  setDeepResearch: (v: boolean) => void
  uploadedStructure: UploadedStructure | null
  setUploadedStructure: (v: UploadedStructure | null) => void

  /* Gate 0 · Estructura propuesta */
  proposal: readonly ProposalModule[]
  reorderProposal: (activeId: string, overId: string) => void
  refineProposal: (id: string) => void
  editProposal: (id: string, title: string, desc: string) => void
  removeProposal: (id: string) => void
  toggleProposalComp: (id: string, key: ContentKind) => void
  addProposal: () => void

  /* Flujo por ruta */
  contentStatusOf: (
    routeId: string,
    moduleId: string,
    kind: ContentKind,
    fallback: ContentStatus,
  ) => ContentStatus
  approveContent: (routeId: string, moduleId: string, kind: ContentKind) => void
  refineContent: (routeId: string, moduleId: string, kind: ContentKind) => void

  isCorpusApproved: (routeId: string) => boolean
  approveCorpus: (routeId: string) => void
  discardedSources: (routeId: string) => readonly number[]
  discardSource: (routeId: string, index: number) => void

  isStoryboardApproved: (routeId: string) => boolean
  approveStoryboard: (routeId: string) => void

  isLabGuideApproved: (routeId: string) => boolean
  approveLabGuide: (routeId: string) => void

  isGenerated: (routeId: string) => boolean
  markGenerated: (routeId: string) => void

  /* Routes */
  routes: readonly LearningRoute[]
  fetchRoutes: () => Promise<void>
  updateRoute: (id: string, data: Partial<LearningRoute>) => Promise<void>

  /* Jobs */
  activeJobs: Record<string, JobState>
  trackJob: (jobId: string) => Promise<JobState>
}

const Ctx = createContext<AppStore | null>(null)

let idSeed = 100
const nextId = () => `p${++idSeed}`

export function AppStoreProvider({ children }: { children: ReactNode }) {
  const [briefText, setBriefText] = useState(
    'Formar a los equipos para diseñar, evaluar y desplegar sistemas de razonamiento avanzado con criterio — del concepto al laboratorio, cerrando con una evaluación de dominio. Público: equipos técnicos y de negocio.',
  )
  const [deepResearch, setDeepResearch] = useState(false)
  const [uploadedStructure, setUploadedStructure] = useState<UploadedStructure | null>(null)

  const [proposal, setProposal] = useState<readonly ProposalModule[]>(INITIAL_PROPOSAL)

  const [statusOverride, setStatusOverride] = useState<Record<string, ContentStatus>>({})
  const [corpusApproved, setCorpusApproved] = useState<Record<string, boolean>>({})
  const [discarded, setDiscarded] = useState<Record<string, readonly number[]>>({})
  const [storyboardOk, setStoryboardOk] = useState<Record<string, boolean>>({})
  const [labGuideOk, setLabGuideOk] = useState<Record<string, boolean>>({})
  const [generated, setGenerated] = useState<Record<string, boolean>>({})

  const [routes, setRoutes] = useState<readonly LearningRoute[]>(ROUTES)

  const fetchRoutes = useCallback(async () => {
    try {
      const data = await api.request<LearningRoute[]>('/learning-paths/')
      setRoutes(data)
    } catch (e) {
      console.error('Failed to fetch routes', e)
    }
  }, [])

  const updateRoute = useCallback(async (id: string, data: Partial<LearningRoute>) => {
    try {
      const updated = await api.request<LearningRoute>(`/learning-paths/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      })
      setRoutes((prev) => prev.map((r) => (r.id === id ? updated : r)))
    } catch (e) {
      console.error('Failed to update route', e)
    }
  }, [])

  useEffect(() => {
    fetchRoutes()
  }, [fetchRoutes])

  const [activeJobs, setActiveJobs] = useState<Record<string, JobState>>({})

  const trackJob = useCallback(async (jobId: string) => {
    try {
      const initialJob = await api.getJob(jobId)
      setActiveJobs((prev) => ({ ...prev, [jobId]: initialJob }))
    } catch (e) {
      console.error("Failed to fetch initial job state", e)
    }

    return api.pollJob(jobId, (job) => {
      setActiveJobs((prev) => ({ ...prev, [jobId]: job }))
    })
  }, [])

  /* ── Proposal ─────────────────────────────────────────────── */
  const reorderProposal = useCallback((activeId: string, overId: string) => {
    setProposal((prev) => {
      const from = prev.findIndex((m) => m.id === activeId)
      const to = prev.findIndex((m) => m.id === overId)
      if (from < 0 || to < 0 || from === to) return prev
      const next = prev.slice()
      const [moved] = next.splice(from, 1)
      if (!moved) return prev
      next.splice(to, 0, moved)
      return next
    })
  }, [])

  const refineProposal = useCallback((id: string) => {
    setProposal((prev) =>
      prev.map((m) =>
        m.id === id
          ? { ...m, title: m.alt.title, desc: m.alt.desc, alt: { title: m.title, desc: m.desc } }
          : m,
      ),
    )
  }, [])

  const editProposal = useCallback((id: string, title: string, desc: string) => {
    setProposal((prev) => prev.map((m) => (m.id === id ? { ...m, title, desc } : m)))
  }, [])

  const removeProposal = useCallback((id: string) => {
    setProposal((prev) => (prev.length <= 1 ? prev : prev.filter((m) => m.id !== id)))
  }, [])

  const toggleProposalComp = useCallback((id: string, key: ContentKind) => {
    setProposal((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, comps: { ...m.comps, [key]: !m.comps[key] } } : m,
      ),
    )
  }, [])

  const addProposal = useCallback(() => {
    setProposal((prev) => [
      ...prev,
      {
        id: nextId(),
        title: 'Nuevo módulo',
        desc: 'Describe el objetivo de este módulo.',
        min: 6,
        comps: { lesson: true, video: false, infografia: false, quiz: true, lab: false },
        alt: { title: 'Módulo alternativo', desc: 'Otro enfoque para este bloque.' },
      },
    ])
  }, [])

  /* ── Contenido por ruta ───────────────────────────────────── */
  const contentStatusOf = useCallback(
    (routeId: string, moduleId: string, kind: ContentKind, fallback: ContentStatus) =>
      statusOverride[contentKey(routeId, moduleId, kind)] ?? fallback,
    [statusOverride],
  )

  const approveContent = useCallback((routeId: string, moduleId: string, kind: ContentKind) => {
    setStatusOverride((prev) => ({ ...prev, [contentKey(routeId, moduleId, kind)]: 'aprobado' }))
  }, [])

  const refineContent = useCallback((routeId: string, moduleId: string, kind: ContentKind) => {
    setStatusOverride((prev) => ({ ...prev, [contentKey(routeId, moduleId, kind)]: 'en-revision' }))
  }, [])

  /* ── Gates ────────────────────────────────────────────────── */
  const isCorpusApproved = useCallback((routeId: string) => corpusApproved[routeId] ?? false, [corpusApproved])
  const approveCorpus = useCallback((routeId: string) => {
    setCorpusApproved((prev) => ({ ...prev, [routeId]: true }))
  }, [])

  const discardedSources = useCallback(
    (routeId: string) => discarded[routeId] ?? [],
    [discarded],
  )
  const discardSource = useCallback((routeId: string, index: number) => {
    setDiscarded((prev) => ({ ...prev, [routeId]: [...(prev[routeId] ?? []), index] }))
  }, [])

  const isStoryboardApproved = useCallback((routeId: string) => storyboardOk[routeId] ?? false, [storyboardOk])
  const approveStoryboard = useCallback((routeId: string) => {
    setStoryboardOk((prev) => ({ ...prev, [routeId]: true }))
  }, [])

  const isLabGuideApproved = useCallback((routeId: string) => labGuideOk[routeId] ?? false, [labGuideOk])
  const approveLabGuide = useCallback((routeId: string) => {
    setLabGuideOk((prev) => ({ ...prev, [routeId]: true }))
  }, [])

  const isGenerated = useCallback((routeId: string) => generated[routeId] ?? false, [generated])
  const markGenerated = useCallback((routeId: string) => {
    setGenerated((prev) => ({ ...prev, [routeId]: true }))
  }, [])

  const store = useMemo<AppStore>(
    () => ({
      briefText, setBriefText,
      deepResearch, setDeepResearch,
      uploadedStructure, setUploadedStructure,
      proposal, reorderProposal, refineProposal, editProposal, removeProposal, toggleProposalComp, addProposal,
      contentStatusOf, approveContent, refineContent,
      isCorpusApproved, approveCorpus, discardedSources, discardSource,
      isStoryboardApproved, approveStoryboard,
      isLabGuideApproved, approveLabGuide,
      isGenerated, markGenerated,
      routes, fetchRoutes, updateRoute,
      activeJobs, trackJob,
    }),
    [
      briefText, deepResearch, uploadedStructure, proposal,
      reorderProposal, refineProposal, editProposal, removeProposal, toggleProposalComp, addProposal,
      contentStatusOf, approveContent, refineContent,
      isCorpusApproved, approveCorpus, discardedSources, discardSource,
      isStoryboardApproved, approveStoryboard,
      isLabGuideApproved, approveLabGuide,
      isGenerated, markGenerated,
      routes, fetchRoutes, updateRoute,
      activeJobs, trackJob,
    ],
  )

  return <Ctx.Provider value={store}>{children}</Ctx.Provider>
}

export function useStore(): AppStore {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useStore must be used within AppStoreProvider')
  return ctx
}
