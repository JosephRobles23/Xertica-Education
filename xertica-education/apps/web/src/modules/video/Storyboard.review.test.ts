import {
  buildReviewedStoryboard,
  canRenderAiStoryboard,
  hasRenderTargetModuleId,
  isValidUuid,
  renderActionLabel,
  renderPhaseLabel,
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

if (!hasRenderTargetModuleId('r1m1')) {
  throw new Error('Un module_id persistido tipo r1m1 debe activar la carga del storyboard real si la ruta es real.')
}

if (!isValidUuid('d781ba73-45b8-4c27-a1fe-5158787ef803')) {
  throw new Error('La validación UUID debe servir tanto para route_id como para module_id.')
}

if (hasRenderTargetModuleId(undefined)) {
  throw new Error('Sin module_id no debe intentarse cargar un Render Target real.')
}

if (!canRenderAiStoryboard('fallback_error')) {
  throw new Error('Si el backend falla, el render debe seguir disponible con el borrador actual.')
}

if (!canRenderAiStoryboard('idle')) {
  throw new Error('El render IA debe permitir usar el borrador inicial antes de pedir una versión del backend.')
}

if (canRenderAiStoryboard('fallback_invalid_target')) {
  throw new Error('Sin render target válido, el render sí debe seguir bloqueado.')
}

if (!canRenderAiStoryboard('backend')) {
  throw new Error('El storyboard real del backend también debe poder renderizarse.')
}

if (renderActionLabel('success', true) !== 'Regenerar Video') {
  throw new Error('Si ya existe un video, la CTA debe permitir regenerarlo.')
}

if (renderActionLabel('idle', false) !== 'Renderizar Video') {
  throw new Error('Sin video previo, la CTA debe invitar a renderizar por primera vez.')
}

if (renderPhaseLabel(6) !== 'Sintetizando narración por escena...') {
  throw new Error('El progreso bajo debe explicar que la demora actual está en TTS.')
}

if (renderPhaseLabel(72) !== 'Renderizando video final en Remotion...') {
  throw new Error('El progreso medio debe explicar que el render final sigue en curso.')
}
