import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useEffect,
  type ReactNode,
} from 'react'
import type {
  ContentKind,
  ContentStatus,
  CustomerContext,
  LearningRoute,
  ProposalModule,
  RouteModule,
  Source,
} from '@/shared/lib/types'
import { INITIAL_PROPOSAL, ROUTES } from '@/shared/data/routes'
import { api, type JobState } from '@/shared/lib/api'
import type { GoogleDriveSelection } from '@/shared/lib/googleDrive'
import { toast } from 'sonner'

/** Clave estable para el estado de un contenido concreto. */
const contentKey = (routeId: string, moduleId: string, kind: ContentKind) =>
  `${routeId}:${moduleId}:${kind}` as const

type ApiLearningRoute = Omit<LearningRoute, 'id'> & { id: string }

const hasContentfulModules = (route: ApiLearningRoute) =>
  Array.isArray(route.modules) &&
  route.modules.length > 0 &&
  route.modules.some((module) => Array.isArray(module.contents) && module.contents.length > 0)

const hydrateRoute = (route: ApiLearningRoute): LearningRoute => {
  const mockRoute = ROUTES.find((item) => item.id === route.id)

  if (!mockRoute) {
    return route as LearningRoute
  }

  return {
    ...mockRoute,
    name: route.name || mockRoute.name,
    status: route.status || mockRoute.status,
    objective: route.objective || mockRoute.objective,
    sources: route.sources?.length ? route.sources : mockRoute.sources,
    pack: route.pack || mockRoute.pack,
    modules: hasContentfulModules(route) ? route.modules : mockRoute.modules,
  }
}

const hydrateRoutes = (apiRoutes: readonly ApiLearningRoute[]): readonly LearningRoute[] => {
  const apiById = new Map(apiRoutes.map((route) => [route.id, route]))
  const hydratedMocks = ROUTES.map((route) => {
    const apiRoute = apiById.get(route.id)
    return apiRoute ? hydrateRoute(apiRoute) : route
  })
  const newRoutes = apiRoutes.filter((route) => !ROUTES.some((mockRoute) => mockRoute.id === route.id))

  return [...hydratedMocks, ...newRoutes.map(hydrateRoute)]
}

export interface UploadedStructure {
  name: string
  kind: 'drive' | 'texto' | 'local'
  driveFile?: GoogleDriveSelection
  localFile?: File
}

export const mapRouteModulesToProposal = (modules: readonly RouteModule[]): ProposalModule[] => {
  return (modules || []).map((m) => {
    const comps: Record<ContentKind, boolean> = {
      lesson: false,
      video: false,
      infografia: false,
      quiz: false,
      lab: false,
    }
    
    if (Array.isArray(m.contents)) {
      m.contents.forEach((c) => {
        if (c.kind in comps) {
          comps[c.kind as ContentKind] = true
        }
      })
    }
    
    const desc = (m as any).description || (m as any).descripcion || (m.contents && m.contents[0]?.summary) || 'Módulo propuesto por IA.'
    
    const componentDurations: Record<ContentKind, number> = {
      lesson: 5,
      video: 3,
      infografia: 2,
      quiz: 4,
      lab: 15,
    }
    const computedMin = Array.isArray(m.contents)
      ? m.contents.reduce((sum, c) => sum + (componentDurations[c.kind as ContentKind] || 5), 0)
      : 5
    const min = (m as any).target_minutes || (m as any).duracion_objetivo_min || (m as any).min || computedMin

    return {
      id: m.id,
      title: m.name,
      desc,
      min,
      comps,
      type: m.type,
      alt: {
        title: `Alternativa: ${m.name}`,
        desc: `Enfoque alternativo para: ${desc}`,
      },
    }
  })
}

export const mapProposalToRouteModules = (proposal: readonly ProposalModule[]): RouteModule[] => {
  return (proposal || []).map((p, i) => {
    const contents = Object.entries(p.comps)
      .filter(([, enabled]) => enabled)
      .map(([kind]) => ({
        kind: kind as ContentKind,
        status: 'borrador' as ContentStatus,
        summary: p.desc || 'Contenido propuesto',
      }))
    return {
      id: p.id,
      num: String(i + 1).padStart(2, '0'),
      name: p.title,
      type: p.type || 'capsula',
      status: 'borrador' as ContentStatus,
      contents,
      description: p.desc,
      descripcion: p.desc,
      target_minutes: p.min,
      duracion_objetivo_min: p.min,
    } as any
  })
}

interface AppStore {
  /* Gate 0 · Nueva ruta */
  briefText: string
  setBriefText: (v: string) => void
  deepResearch: boolean
  setDeepResearch: (v: boolean) => void
  customerContext: CustomerContext
  setCustomerContext: (v: CustomerContext) => void
  uploadedStructure: UploadedStructure | null
  setUploadedStructure: (v: UploadedStructure | null) => void

  /* Gate 0 · Estructura propuesta */
  proposal: readonly ProposalModule[]
  setProposal: (v: readonly ProposalModule[]) => void
  proposalLoadedRouteId: string | null
  setProposalLoadedRouteId: (v: string | null) => void
  structureJobId: string | null
  setStructureJobId: (v: string | null) => void
  pendingDeepResearch: boolean
  setPendingDeepResearch: (v: boolean) => void
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
  moduleStatusOf: (routeId: string, module: RouteModule) => ContentStatus
  approveModule: (routeId: string, module: RouteModule) => void
  routeStatusOf: (route: LearningRoute) => ContentStatus
  routeProgressOf: (route: LearningRoute) => { done: number; total: number; pct: number }

  isCorpusApproved: (routeId: string) => boolean
  approveCorpus: (routeId: string, aspect_ratio?: string) => Promise<void>
  discardedSources: (routeId: string) => readonly number[]
  discardSource: (routeId: string, index: number) => void

  isStoryboardApproved: (routeId: string) => boolean
  approveStoryboard: (routeId: string) => void
  storyboardVideoUrlOf: (routeId: string) => string
  setStoryboardVideoUrl: (routeId: string, videoUrl: string) => void
  storyboardJobIdOf: (routeId: string) => string | undefined
  setStoryboardJobId: (routeId: string, jobId: string) => void
  clearStoryboardJobId: (routeId: string) => void

  isLabGuideApproved: (routeId: string) => boolean
  approveLabGuide: (routeId: string) => void

  isGenerated: (routeId: string) => boolean
  markGenerated: (routeId: string) => void

  /* Routes */
  routes: readonly LearningRoute[]
  routesLoaded: boolean
  fetchRoutes: () => Promise<void>
  fetchRouteById: (id: string) => Promise<LearningRoute | null>
  updateRoute: (id: string, data: Partial<LearningRoute>) => Promise<void>
  replaceRouteSources: (id: string, sources: readonly Source[]) => void
  activeRouteId: string | null
  setActiveRouteId: (id: string | null) => void

  /* Jobs */
  activeJobs: Record<string, JobState>
  trackJob: (jobId: string) => Promise<JobState>
}

const Ctx = createContext<AppStore | null>(null)

const STORYBOARD_VIDEO_KEY = 'xertica.education.storyboard-video-url'
const STORYBOARD_JOB_KEY = 'xertica.education.storyboard-job-id'
const ACTIVE_ROUTE_ID_KEY = 'xertica.education.active-route-id'
const STRUCTURE_JOB_KEY = 'xertica.education.structure-job-id'
const PENDING_DEEP_RESEARCH_KEY = 'xertica.education.pending-deep-research'
const PROPOSAL_LOADED_ROUTE_ID_KEY = 'xertica.education.proposal-loaded-route-id'

const readJSON = <T,>(key: string, fallback: T): T => {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

const writeJSON = <T,>(key: string, value: T) => {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Ignore storage failures. App still works in memory.
  }
}

let idSeed = 100
const nextId = () => `p${++idSeed}`

export function AppStoreProvider({ children }: { children: ReactNode }) {
  const [briefText, setBriefText] = useState('')
  const [deepResearch, setDeepResearch] = useState(false)
  const [customerContext, setCustomerContext] = useState<CustomerContext>({})
  const [uploadedStructure, setUploadedStructure] = useState<UploadedStructure | null>(null)

  const [proposal, setProposal] = useState<readonly ProposalModule[]>(INITIAL_PROPOSAL)
  const [proposalLoadedRouteId, setProposalLoadedRouteId] = useState<string | null>(
    () => readJSON<string | null>(PROPOSAL_LOADED_ROUTE_ID_KEY, null),
  )
  const [structureJobId, setStructureJobId] = useState<string | null>(
    () => readJSON<string | null>(STRUCTURE_JOB_KEY, null),
  )
  const [pendingDeepResearch, setPendingDeepResearch] = useState<boolean>(
    () => readJSON<boolean>(PENDING_DEEP_RESEARCH_KEY, false),
  )

  const [statusOverride, setStatusOverride] = useState<Record<string, ContentStatus>>({})
  const [corpusApproved, setCorpusApproved] = useState<Record<string, boolean>>({})
  const [discarded, setDiscarded] = useState<Record<string, readonly number[]>>({})
  const [storyboardOk, setStoryboardOk] = useState<Record<string, boolean>>({})
  const [storyboardVideoUrl, setStoryboardVideoUrlState] = useState<Record<string, string>>(
    () => readJSON(STORYBOARD_VIDEO_KEY, {}),
  )
  const [storyboardJobId, setStoryboardJobIdState] = useState<Record<string, string>>(
    () => readJSON(STORYBOARD_JOB_KEY, {}),
  )
  const [labGuideOk, setLabGuideOk] = useState<Record<string, boolean>>({})
  const [generated, setGenerated] = useState<Record<string, boolean>>({})

  const [routes, setRoutes] = useState<readonly LearningRoute[]>(ROUTES)
  const [routesLoaded, setRoutesLoaded] = useState(false)
  const [activeRouteId, setActiveRouteId] = useState<string | null>(
    () => readJSON<string | null>(ACTIVE_ROUTE_ID_KEY, null),
  )

  const fetchRoutes = useCallback(async () => {
    try {
      const data = await api.request<ApiLearningRoute[]>('/learning-paths/')
      setRoutes(hydrateRoutes(data))
    } catch (e) {
      console.error('Failed to fetch routes', e)
    } finally {
      setRoutesLoaded(true)
    }
  }, [])

  const fetchRouteById = useCallback(async (id: string) => {
    try {
      const data = await api.request<ApiLearningRoute>(`/learning-paths/${id}`)
      const hydrated = hydrateRoute(data)
      setRoutes((prev) => {
        const existingIndex = prev.findIndex((route) => route.id === id)
        if (existingIndex < 0) return [...prev, hydrated]
        return prev.map((route, index) => (index === existingIndex ? hydrated : route))
      })
      return hydrated
    } catch (e) {
      console.error(`Failed to fetch route ${id}`, e)
      return null
    }
  }, [])

  const updateRoute = useCallback(async (id: string, data: Partial<LearningRoute>) => {
    try {
      const updated = await api.request<ApiLearningRoute>(`/learning-paths/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      })
      setRoutes((prev) => prev.map((r) => (r.id === id ? hydrateRoute(updated) : r)))
    } catch (e) {
      console.error('Failed to update route', e)
    }
  }, [])

  const replaceRouteSources = useCallback((id: string, sources: readonly Source[]) => {
    setRoutes((prev) => prev.map((route) => (route.id === id ? { ...route, sources } : route)))
    setDiscarded((prev) => ({ ...prev, [id]: [] }))
    setCorpusApproved((prev) => ({ ...prev, [id]: false }))
  }, [])

  useEffect(() => {
    fetchRoutes()
  }, [fetchRoutes])

  useEffect(() => {
    writeJSON(STORYBOARD_VIDEO_KEY, storyboardVideoUrl)
  }, [storyboardVideoUrl])

  useEffect(() => {
    writeJSON(STORYBOARD_JOB_KEY, storyboardJobId)
  }, [storyboardJobId])

  useEffect(() => {
    writeJSON(ACTIVE_ROUTE_ID_KEY, activeRouteId)
  }, [activeRouteId])

  useEffect(() => {
    writeJSON(STRUCTURE_JOB_KEY, structureJobId)
  }, [structureJobId])

  useEffect(() => {
    writeJSON(PENDING_DEEP_RESEARCH_KEY, pendingDeepResearch)
  }, [pendingDeepResearch])

  useEffect(() => {
    writeJSON(PROPOSAL_LOADED_ROUTE_ID_KEY, proposalLoadedRouteId)
  }, [proposalLoadedRouteId])

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
    // Persistencia en backend (ADR-0021); el override local actúa como capa optimista.
    api.reviewContentApproval(routeId, moduleId, kind, 'aprobado').catch((e) => {
      console.error('Failed to persist content approval', e)
    })
  }, [])

  const refineContent = useCallback((routeId: string, moduleId: string, kind: ContentKind) => {
    setStatusOverride((prev) => ({ ...prev, [contentKey(routeId, moduleId, kind)]: 'en-revision' }))
    api.reviewContentApproval(routeId, moduleId, kind, 'en-revision').catch((e) => {
      console.error('Failed to persist content refinement', e)
    })
  }, [])

  /* ── Aprobación en cascada (módulo → ruta) ────────────────── */
  const moduleStatusOf = useCallback(
    (routeId: string, module: RouteModule): ContentStatus => {
      const contents = module.contents ?? []
      const allContentApproved =
        contents.length > 0 &&
        contents.every(
          (content) =>
            (statusOverride[contentKey(routeId, module.id, content.kind)] ?? content.status) === 'aprobado',
        )
      return allContentApproved ? 'aprobado' : module.status
    },
    [statusOverride],
  )

  const approveModule = useCallback((routeId: string, module: RouteModule) => {
    setStatusOverride((prev) => {
      const next = { ...prev }
      ;(module.contents ?? []).forEach((content) => {
        next[contentKey(routeId, module.id, content.kind)] = 'aprobado'
      })
      return next
    })
    ;(module.contents ?? []).forEach((content) => {
      api.reviewContentApproval(routeId, module.id, content.kind, 'aprobado').catch((e) => {
        console.error('Failed to persist module approval', e)
      })
    })
  }, [])

  const routeStatusOf = useCallback(
    (route: LearningRoute): ContentStatus => {
      const modules = route.modules ?? []
      const allModulesApproved =
        modules.length > 0 && modules.every((module) => moduleStatusOf(route.id, module) === 'aprobado')
      return allModulesApproved ? 'aprobado' : route.status
    },
    [moduleStatusOf],
  )

  const routeProgressOf = useCallback(
    (route: LearningRoute) => {
      const modules = route.modules ?? []
      const done = modules.filter((module) => moduleStatusOf(route.id, module) === 'aprobado').length
      const total = modules.length
      return { done, total, pct: total === 0 ? 0 : Math.round((done / total) * 100) }
    },
    [moduleStatusOf],
  )

  /* ── Gates ────────────────────────────────────────────────── */
  // Rehidratación (ADR-0021): el estado local es capa optimista sobre lo persistido.
  const routeApprovalsOf = useCallback(
    (routeId: string) => routes.find((route) => route.id === routeId)?.approvals ?? {},
    [routes],
  )
  const isCorpusApproved = useCallback(
    (routeId: string) =>
      corpusApproved[routeId] ??
      routes.find((route) => route.id === routeId)?.status === 'generado',
    [corpusApproved, routes],
  )
  const approveCorpus = useCallback(async (routeId: string, aspect_ratio?: string) => {
    try {
      const res = await api.request<{ ingestionJobId?: string }>(
        `/learning-paths/${routeId}/sourcing/approve`,
        {
          method: 'POST',
          body: JSON.stringify({ aspect_ratio: aspect_ratio || 'auto' }),
        },
      )
      setCorpusApproved((prev) => ({ ...prev, [routeId]: true }))
      await fetchRoutes()

      // Gate 1 advierte sin bloquear (ADR-0023): sigue la ingesta KB en background
      // y reporta el resultado — incluida una KB vacía — de forma honesta.
      if (res?.ingestionJobId) {
        api
          .pollJob(res.ingestionJobId)
          .then((job) => {
            const report = job.result as
              | { chunks_created?: number; sources_processed?: number }
              | undefined
            if (report?.chunks_created) {
              toast.success('Knowledge Base lista', {
                description: `${report.chunks_created} chunks indexados de ${report.sources_processed} documento(s) del cliente.`,
              })
            }
          })
          .catch((err: Error) => {
            toast.warning('Ruta sin grounding de KB', {
              description:
                err.message ||
                'Esta ruta no tiene documentos del cliente (Vía 2); el contenido se generará sin grounding de la KB.',
              duration: 10000,
            })
          })
      }
    } catch (e) {
      console.error('Failed to approve corpus', e)
      throw e
    }
  }, [fetchRoutes, routes])

  const discardedSources = useCallback(
    (routeId: string) => discarded[routeId] ?? [],
    [discarded],
  )
  const discardSource = useCallback((routeId: string, index: number) => {
    setDiscarded((prev) => ({ ...prev, [routeId]: [...(prev[routeId] ?? []), index] }))
  }, [])

  const isStoryboardApproved = useCallback(
    (routeId: string) => storyboardOk[routeId] ?? routeApprovalsOf(routeId).storyboard ?? false,
    [storyboardOk, routeApprovalsOf],
  )
  const approveStoryboard = useCallback((routeId: string) => {
    setStoryboardOk((prev) => ({ ...prev, [routeId]: true }))
    api.patchRouteApprovals(routeId, { storyboard: true }).catch((e) => {
      console.error('Failed to persist storyboard approval', e)
    })
  }, [])

  const storyboardVideoUrlOf = useCallback(
    (routeId: string) => storyboardVideoUrl[routeId] ?? '',
    [storyboardVideoUrl],
  )
  const setStoryboardVideoUrl = useCallback((routeId: string, videoUrl: string) => {
    setStoryboardVideoUrlState((prev) => ({ ...prev, [routeId]: videoUrl }))
  }, [])

  const storyboardJobIdOf = useCallback(
    (routeId: string) => storyboardJobId[routeId],
    [storyboardJobId],
  )
  const setStoryboardJobId = useCallback((routeId: string, jobId: string) => {
    setStoryboardJobIdState((prev) => ({ ...prev, [routeId]: jobId }))
  }, [])
  const clearStoryboardJobId = useCallback((routeId: string) => {
    setStoryboardJobIdState((prev) => {
      if (!(routeId in prev)) return prev
      const next = { ...prev }
      delete next[routeId]
      return next
    })
  }, [])

  const isLabGuideApproved = useCallback(
    (routeId: string) => labGuideOk[routeId] ?? routeApprovalsOf(routeId).labGuide ?? false,
    [labGuideOk, routeApprovalsOf],
  )
  const approveLabGuide = useCallback((routeId: string) => {
    setLabGuideOk((prev) => ({ ...prev, [routeId]: true }))
    api.patchRouteApprovals(routeId, { labGuide: true }).catch((e) => {
      console.error('Failed to persist lab guide approval', e)
    })
  }, [])

  const isGenerated = useCallback(
    (routeId: string) => generated[routeId] ?? routeApprovalsOf(routeId).generated ?? false,
    [generated, routeApprovalsOf],
  )
  const markGenerated = useCallback((routeId: string) => {
    setGenerated((prev) => ({ ...prev, [routeId]: true }))
    api.patchRouteApprovals(routeId, { generated: true }).catch((e) => {
      console.error('Failed to persist generated flag', e)
    })
  }, [])

  const store = useMemo<AppStore>(
    () => ({
      briefText, setBriefText,
      deepResearch, setDeepResearch,
      customerContext, setCustomerContext,
      uploadedStructure, setUploadedStructure,
      proposal, setProposal,
      proposalLoadedRouteId, setProposalLoadedRouteId,
      structureJobId, setStructureJobId,
      pendingDeepResearch, setPendingDeepResearch,
      reorderProposal, refineProposal, editProposal, removeProposal, toggleProposalComp, addProposal,
      contentStatusOf, approveContent, refineContent, moduleStatusOf, approveModule, routeStatusOf, routeProgressOf,
      isCorpusApproved, approveCorpus, discardedSources, discardSource,
      isStoryboardApproved, approveStoryboard, storyboardVideoUrlOf, setStoryboardVideoUrl, storyboardJobIdOf, setStoryboardJobId, clearStoryboardJobId,
      isLabGuideApproved, approveLabGuide,
      isGenerated, markGenerated,
      routes, routesLoaded, fetchRoutes, fetchRouteById, updateRoute, replaceRouteSources,
      activeRouteId, setActiveRouteId,
      activeJobs, trackJob,
    }),
    [
      briefText, deepResearch, customerContext, uploadedStructure, proposal,
      proposalLoadedRouteId, structureJobId, pendingDeepResearch,
      reorderProposal, refineProposal, editProposal, removeProposal, toggleProposalComp, addProposal,
      contentStatusOf, approveContent, refineContent, moduleStatusOf, approveModule, routeStatusOf, routeProgressOf,
      isCorpusApproved, approveCorpus, discardedSources, discardSource,
      isStoryboardApproved, approveStoryboard, storyboardVideoUrlOf, setStoryboardVideoUrl, storyboardJobIdOf, setStoryboardJobId, clearStoryboardJobId,
      isLabGuideApproved, approveLabGuide,
      isGenerated, markGenerated,
      routes, routesLoaded, fetchRoutes, fetchRouteById, updateRoute, replaceRouteSources,
      activeRouteId, setActiveRouteId,
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
