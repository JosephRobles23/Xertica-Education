import {
  buildReviewedStoryboard,
  canRenderAiStoryboard,
  isValidRenderTargetModuleId,
  isValidUuid,
  sceneToReviewScene,
  updateSceneNarration,
  type StoryboardScene,
} from './Storyboard'

const backendScene: StoryboardScene = {
  scene_number: 1,
  narration: 'Explica por qué el objetivo del módulo importa.',
  visual_type: 'comparison',
  visual_config: { left: 'Sin criterio', right: 'Con criterio' },
  teaching_point: 'Distinguir actividad de aprendizaje de resultado observable.',
  pedagogical_intent: 'corrección de malentendido',
  teaching_pattern: 'regla de decisión',
  visual_rationale: 'La comparación permite ver el contraste antes/después.',
  grounding_status: 'kb_grounded',
}

const reviewScene = sceneToReviewScene(backendScene, { groundingStatus: 'module_grounded' })
const editedScene = updateSceneNarration(reviewScene, 'Narración revisada antes del render.')
const payload = buildReviewedStoryboard('Módulo de prueba', 180, [editedScene])

if (reviewScene.teachingPoint !== backendScene.teaching_point) {
  throw new Error('La revisión debe mostrar el teaching point real del backend.')
}

if (reviewScene.groundingStatus !== 'kb_grounded') {
  throw new Error('La escena debe preferir su grounding status sobre el fallback general.')
}

if (editedScene.narration !== 'Narración revisada antes del render.') {
  throw new Error('Editar narración debe modificar la escena revisada.')
}

if (payload.scenes[0]?.narration !== editedScene.narration) {
  throw new Error('El render debe usar la narración revisada.')
}

if (payload.scenes[0]?.visual_rationale !== backendScene.visual_rationale) {
  throw new Error('El render debe preservar la razón visual aprobada.')
}

if (!isValidRenderTargetModuleId('d781ba73-45b8-4c27-a1fe-5158787ef803')) {
  throw new Error('Un module_id UUID debe activar la carga del storyboard real.')
}

if (!isValidUuid('d781ba73-45b8-4c27-a1fe-5158787ef803')) {
  throw new Error('La validación UUID debe servir tanto para route_id como para module_id.')
}

if (isValidRenderTargetModuleId('p102')) {
  throw new Error('Un module_id local/mock no debe fingir que carga un Render Target real.')
}

if (canRenderAiStoryboard('fallback_error')) {
  throw new Error('El render IA debe bloquearse cuando no existe storyboard real del backend.')
}

if (!canRenderAiStoryboard('backend')) {
  throw new Error('El render IA solo debe permitirse con storyboard real del backend.')
}
