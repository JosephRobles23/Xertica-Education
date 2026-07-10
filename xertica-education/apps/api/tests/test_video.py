import asyncio
import copy
import os
import tempfile
import time
import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch
from uuid import UUID, uuid4
from main import app
from config.dependencies import get_jobs_service, get_knowledge_base, get_video_service
from models.dto.requests import StoryboardRequest
from models.domain.kb import Citation, GroundedChunk
from services.video.service import VideoService
from services.video.executor import RenderExecutor
from services.video.transformer import transform_storyboard_to_edit_decisions


class _FakeTableQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = {}

    def select(self, *_args):
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def execute(self):
        rows = [
            row
            for row in self._rows
            if all(str(row.get(key)) == str(value) for key, value in self._filters.items())
        ]
        return type("FakeResult", (), {"data": rows})()


class _FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _FakeTableQuery(self._tables.get(name, []))


class _FakeLLM:
    def __init__(self):
        self.prompts = []

    async def chat_completion(self, role, prompt):
        self.prompts.append(prompt)
        is_teaching_first = all(
            marker in prompt
            for marker in [
                "OBJETIVO PEDAGOGICO DEL MODULO",
                "KB Grounding aporta evidencia, ejemplos y vocabulario",
                "5 a 7 escenas",
                "teaching_pattern",
                "visual_rationale",
            ]
        )
        if not is_teaching_first:
            return """
            {
              "title": "Resumen generico de IA",
              "total_word_budget": 300,
              "scenes": [
                {
                  "scene_number": 1,
                  "narration": "Vemos luces azules conectandose mientras aparece el tema.",
                  "visual_type": "ai_video",
                  "visual_config": {"prompt": "blue technology network intro"}
                }
              ]
            }
            """

        return """
        {
          "title": "Razonamiento avanzado para decisiones de negocio",
          "total_word_budget": 300,
          "scenes": [
            {
              "scene_number": 1,
              "narration": "Antes de automatizar una respuesta, necesitamos saber que decision de negocio estamos protegiendo.",
              "visual_type": "callout",
              "visual_config": {"callout_style": "info", "text": "La calidad empieza por la decision, no por la velocidad."},
              "teaching_point": "Conectar el razonamiento avanzado con una decision de negocio concreta.",
              "pedagogical_intent": "Abrir con el Objetivo Pedagogico del Modulo para evitar un resumen aleatorio de la KB.",
              "teaching_pattern": "framing_question",
              "visual_rationale": "Un callout concentra la pregunta guia sin usar una intro decorativa.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 2,
              "narration": "La evidencia recuperada recomienda verificar supuestos antes de aceptar una salida automatica.",
              "visual_type": "comparison",
              "visual_config": {"leftLabel": "Respuesta rapida", "leftValue": "Acepta supuestos", "rightLabel": "Razonamiento avanzado", "rightValue": "Verifica supuestos"},
              "teaching_point": "Distinguir una respuesta rapida de una respuesta verificable.",
              "pedagogical_intent": "Usar la KB como evidencia para corregir un malentendido frecuente.",
              "teaching_pattern": "misconception_correction",
              "visual_rationale": "La comparacion muestra el contraste central sin inventar metricas.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 3,
              "narration": "El proceso se vuelve manejable cuando separamos objetivo, evidencia, restricciones y decision final.",
              "visual_type": "progress_bar",
              "visual_config": {"title": "Ruta de razonamiento", "progress": 50, "steps": ["Objetivo", "Evidencia", "Restricciones", "Decision"]},
              "teaching_point": "Presentar el flujo mental del razonamiento avanzado.",
              "pedagogical_intent": "Convertir el modulo en una secuencia que el estudiante pueda repetir.",
              "teaching_pattern": "process_explanation",
              "visual_rationale": "Una barra de progreso ayuda a seguir la secuencia paso a paso.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 4,
              "narration": "En la practica, cada evidencia debe responder a la pregunta que mueve el resultado de negocio.",
              "visual_type": "text_card",
              "visual_config": {"title": "Filtro practico", "subtitle": "Si no cambia la decision, no es evidencia prioritaria."},
              "teaching_point": "Priorizar evidencia que afecta la decision.",
              "pedagogical_intent": "Dar una regla de decision aplicable.",
              "teaching_pattern": "decision_rule",
              "visual_rationale": "Una tarjeta de texto vuelve memorable la regla sin fingir datos.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 5,
              "narration": "El checkpoint final es explicar que se sabe, que falta y que riesgo queda abierto.",
              "visual_type": "callout",
              "visual_config": {"callout_style": "tip", "text": "Buen razonamiento = conclusion + incertidumbre visible."},
              "teaching_point": "Cerrar con una verificacion de incertidumbre.",
              "pedagogical_intent": "Evitar que el estudiante confunda confianza con certeza.",
              "teaching_pattern": "checkpoint",
              "visual_rationale": "El callout resalta el habito que el estudiante debe recordar.",
              "grounding_status": "kb_grounded"
            }
          ]
        }
        """


class _FakeKB:
    def __init__(self, chunks):
        self._chunks = chunks
        self.queries = []

    async def query(self, learning_path_id, text, k=8, verified_only=False):
        self.queries.append({"learning_path_id": learning_path_id, "text": text, "k": k})
        return self._chunks


class _BadVisualStoryboardLLM:
    async def chat_completion(self, role, prompt):
        return """
        {
          "title": "Razonamiento visual",
          "total_word_budget": 260,
          "scenes": [
            {
              "scene_number": 1,
              "narration": "Primero abrimos con una intro llamativa.",
              "visual_type": "ai_video",
              "visual_config": {"prompt": "blue network intro with glowing particles"},
              "teaching_point": "Presentar el tema.",
              "pedagogical_intent": "Abrir con energia.",
              "teaching_pattern": "framing_question",
              "visual_rationale": "Se ve moderno.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 2,
              "narration": "Luego repetimos otra intro similar.",
              "visual_type": "ai_video",
              "visual_config": {"prompt": "another blue network intro"},
              "teaching_point": "Mantener interes.",
              "pedagogical_intent": "Seguir con dinamismo.",
              "teaching_pattern": "framing_question",
              "visual_rationale": "Tambien se ve moderno.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 3,
              "narration": "Una separacion visual del tema.",
              "visual_type": "hero_title",
              "visual_config": {"text": "Razonamiento avanzado"},
              "teaching_point": "Nombrar el concepto.",
              "pedagogical_intent": "Separar visualmente.",
              "teaching_pattern": "framing_question",
              "visual_rationale": "Funciona como titulo.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 4,
              "narration": "Este grafico muestra una diferencia importante.",
              "visual_type": "bar_chart",
              "visual_config": {"title": "Madurez del proceso", "chartData": [{"label": "Equipo A"}, {"label": "Equipo B"}]},
              "teaching_point": "Comparar dos enfoques.",
              "pedagogical_intent": "Mostrar diferencia de resultados.",
              "teaching_pattern": "misconception_correction",
              "visual_rationale": "Un grafico siempre ayuda.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 5,
              "narration": "Aqui vemos la herramienta directamente.",
              "visual_type": "screenshot_scene",
              "visual_config": {"url": "https://example.com/console", "title": "Consola"},
              "teaching_point": "Observar la interfaz.",
              "pedagogical_intent": "Hacer un walkthrough.",
              "teaching_pattern": "worked_example",
              "visual_rationale": "Abrir la web lo hace mas real.",
              "grounding_status": "kb_grounded"
            },
            {
              "scene_number": 6,
              "narration": "Terminamos con una imagen bonita del concepto.",
              "visual_type": "ai_illustration",
              "visual_config": {"prompt": "futuristic educational background"},
              "teaching_point": "Cerrar con una imagen memorable.",
              "pedagogical_intent": "Dejar una impresion final.",
              "teaching_pattern": "synthesis",
              "visual_rationale": "Hace el video mas bonito.",
              "grounding_status": "kb_grounded"
            }
          ]
        }
        """


class _SlowTTSAdapter:
    async def text_to_speech_with_timestamps(self, text: str, output_path: str) -> object:
        await asyncio.sleep(0.2)
        with open(output_path, "wb") as handle:
            handle.write(b"fake-mp3")
        return type(
            "FakeTTSResult",
            (),
            {
                "audio_path": output_path,
                "duration_seconds": 1.0,
                "captions": [{"word": text, "startMs": 0, "endMs": 1000}],
            },
        )()


def _video_service_with_context(route_id, module_id, llm, include_modules_table=True):
    module_row = (
        [
            {
                "id": str(module_id),
                "learning_path_id": str(route_id),
                "titulo": "Ruta de Inteligencia Avanzada",
                "descripcion": "Conectar tecnicas de razonamiento con decisiones de negocio verificables.",
                "tipo": "capsula",
            }
        ]
        if include_modules_table
        else []
    )
    service = VideoService(llm_adapter=llm)
    service._supabase = _FakeSupabase(
        {
            "modules": module_row,
            "learning_paths": [
                {
                    "id": str(route_id),
                    "titulo": "Impulso 2026",
                    "tema": "IA aplicada a operaciones",
                    "brief": "Capacitar equipos para evaluar salidas de IA con criterio de negocio.",
                    "details": {
                        "objective": "Capacitar equipos para evaluar salidas de IA con criterio de negocio.",
                        "modules": [
                            {
                                "id": str(module_id),
                                "name": "Ruta de Inteligencia Avanzada",
                                "description": "Conectar tecnicas de razonamiento con decisiones de negocio verificables.",
                                "type": "capsula",
                            }
                        ],
                    },
                }
            ],
        }
    )
    return service

class TestVideoAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides.clear()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_render_executor_parallelizes_tts_scene_work_and_emits_incremental_progress(self):
        """Scene TTS should overlap instead of blocking one-by-one for every narration clip."""
        progress_updates = []

        class FakeVideoService:
            def __init__(self):
                self.tts_adapter = _SlowTTSAdapter()

            async def _update_job(self, job_id, status, progress, result=None, error=None):
                progress_updates.append(progress)

        executor = RenderExecutor(FakeVideoService())
        executor._concat_audio_files = lambda _audio_paths, output_path: open(output_path, "wb").close()

        scenes = [
            {"scene_number": 1, "narration": "escena uno"},
            {"scene_number": 2, "narration": "escena dos"},
            {"scene_number": 3, "narration": "escena tres"},
        ]
        temp_dir = f"/tmp/test_render_executor_{uuid4()}"
        os.makedirs(temp_dir, exist_ok=True)

        started = time.perf_counter()
        try:
            asyncio.run(executor._stage_tts(uuid4(), scenes, temp_dir))
        finally:
            for filename in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, filename))
            os.rmdir(temp_dir)

        elapsed = time.perf_counter() - started

        self.assertLess(
            elapsed,
            1.3,
            "TTS scene generation still looks serialized; expected overlapping scene synthesis.",
        )
        self.assertEqual(len(executor.audio_paths), 3)
        self.assertEqual(len(executor.durations), 3)
        self.assertGreaterEqual(len(progress_updates), 3)
        self.assertTrue(
            any(progress > 5 for progress in progress_updates),
            "Expected progress after a scene completes.",
        )
        self.assertIn(24, progress_updates)

    def test_remotion_render_keeps_api_event_loop_responsive(self):
        """A long Remotion subprocess must not block job polling or other requests."""
        executor = RenderExecutor(object())
        executor.edit_decisions = {"cuts": []}

        with tempfile.TemporaryDirectory() as composer_dir:
            local_bin = os.path.join(composer_dir, "node_modules", ".bin", "remotion")
            os.makedirs(os.path.dirname(local_bin), exist_ok=True)
            open(local_bin, "wb").close()

            def slow_render(command, **_kwargs):
                time.sleep(0.25)
                open(command[4], "wb").close()

            async def render_and_measure_tick():
                started = time.perf_counter()
                task = asyncio.create_task(executor._stage_remotion_render(uuid4(), composer_dir))
                await asyncio.sleep(0.05)
                tick_delay = time.perf_counter() - started
                await task
                return tick_delay

            with patch("services.video.executor.settings.remotion_composer_path", composer_dir), patch(
                "services.video.executor.subprocess.run",
                side_effect=slow_render,
            ):
                tick_delay = asyncio.run(render_and_measure_tick())

        self.assertLess(tick_delay, 0.15)

    def test_generated_media_failures_fall_back_to_native_teaching_scenes(self):
        """Transient Veo/Imagen failures should not discard an otherwise valid video."""
        class FailingVeo:
            async def render_clip(self, *_args):
                raise RuntimeError("Veo unavailable")

        class FailingImagen:
            async def generate_illustration(self, *_args):
                raise RuntimeError("Imagen unavailable")

        class FakeVideoService:
            veo_adapter = FailingVeo()
            imagen_adapter = FailingImagen()

            async def _update_job(self, *_args, **_kwargs):
                return None

        scenes = [
            {
                "scene_number": 1,
                "narration": "Una metáfora muestra cómo la evidencia cambia la decisión.",
                "visual_type": "ai_video",
                "visual_config": {"prompt": "cinematic evidence metaphor"},
                "teaching_point": "La evidencia cambia decisiones.",
                "pedagogical_intent": "Hacer visible la relación causal.",
            },
            {
                "scene_number": 2,
                "narration": "El modelo mental conecta pregunta, evidencia y acción.",
                "visual_type": "ai_illustration",
                "visual_config": {"prompt": "educational mental model"},
                "teaching_point": "Pregunta, evidencia y acción forman un ciclo.",
                "pedagogical_intent": "Explicar el modelo mental.",
            },
            {
                "scene_number": 3,
                "narration": "La interfaz guía una verificación concreta.",
                "visual_type": "screenshot_scene",
                "visual_config": {"url": "https://example.invalid", "steps": []},
                "teaching_point": "Verificar antes de decidir.",
                "pedagogical_intent": "Mostrar la acción verificable.",
            },
        ]
        executor = RenderExecutor(FakeVideoService())
        executor.durations = [5.0, 5.0, 5.0]

        async def failed_capture(*_args):
            return False

        executor._capture_url_screenshot = failed_capture

        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(executor._stage_visual(uuid4(), scenes, temp_dir))

        self.assertEqual([scene["visual_type"] for scene in scenes], ["callout", "callout", "callout"])
        self.assertEqual(executor.visual_paths, ["", "", ""])
        self.assertIn("evidencia", scenes[0]["visual_config"]["text"].lower())
        fallbacks = sorted(executor.visual_fallbacks, key=lambda fallback: fallback["scene_number"])
        self.assertEqual(
            [fallback["original_visual_type"] for fallback in fallbacks],
            ["ai_video", "ai_illustration", "screenshot_scene"],
        )
        self.assertEqual(fallbacks[0]["scene_number"], 1)

    def test_generic_job_polling_can_resume_in_memory_video_jobs(self):
        """The shared frontend poll endpoint must find video jobs after page navigation."""
        class EmptyJobsService:
            async def get_job_status(self, _job_id):
                return None

        job_id = uuid4()
        service = VideoService()
        service._supabase = None
        service._fallback_jobs[job_id] = {
            "id": str(job_id),
            "type": "video_generation",
            "status": "running",
            "progress": 25,
            "created_at": "2026-07-10T00:00:00+00:00",
            "updated_at": "2026-07-10T00:00:00+00:00",
            "result": None,
            "error": None,
        }
        app.dependency_overrides[get_jobs_service] = lambda: EmptyJobsService()
        app.dependency_overrides[get_video_service] = lambda: service

        response = self.client.get(f"/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "running")

    def test_generate_video_mock_returns_job_id(self):
        """POST /videos/generate with custom storyboard returns a valid job ID."""
        payload = {
            "component_id": None,
            "custom_storyboard": {
                "title": "Test Title",
                "total_word_budget": 150,
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration": "Hello world.",
                        "visual_type": "text_card",
                        "visual_config": {"title": "Welcome", "bullets": ["First point"]}
                    }
                ]
            },
            "use_mock": True
        }
        response = self.client.post("/videos/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("job_id", data)
        # Verify it is a valid UUID string
        job_id_str = data["job_id"]
        job_id = UUID(job_id_str)
        self.assertIsInstance(job_id, UUID)

    def test_get_video_job_status(self):
        """GET /videos/jobs/{job_id} returns status and progress updates."""
        # First trigger generation to get a real job ID
        payload = {
            "component_id": None,
            "use_mock": True
        }
        gen_response = self.client.post("/videos/generate", json=payload)
        self.assertEqual(gen_response.status_code, 200)
        job_id = gen_response.json()["job_id"]
        
        # Poll status
        status_response = self.client.get(f"/videos/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.json()
        self.assertEqual(status_data["job_id"], job_id)
        self.assertIn("status", status_data)
        self.assertIn("progress", status_data)

    def test_generate_video_from_render_target_persists_retrievable_video_asset(self):
        """POST /videos/generate with route/module identity links the completed MP4 to the video Asset."""
        service = VideoService()
        service._supabase = None
        captured_tasks = []

        def capture_task(coro):
            captured_tasks.append(coro)
            return None

        async def fake_execute(self, plan):
            self.total_duration = 8.0
            self.stage_outputs["upload"] = {"url": "https://example.com/videos/route-module.mp4"}

        app.dependency_overrides[get_video_service] = lambda: service

        with patch("services.video.service.asyncio.create_task", side_effect=capture_task), patch(
            "services.video.executor.RenderExecutor.execute",
            new=fake_execute,
        ):
            response = self.client.post(
                "/videos/generate",
                json={
                    "route_id": "01",
                    "module_id": "r1m1",
                    "component_kind": "video",
                    "custom_storyboard": {
                        "title": "Video conectado al modulo",
                        "total_word_budget": 120,
                        "scenes": [
                            {
                                "scene_number": 1,
                                "narration": "Probamos que el render queda conectado al modulo real.",
                                "visual_type": "callout",
                                "visual_config": {"callout_style": "info", "text": "Render conectado"},
                            }
                        ],
                    },
                    "use_mock": False,
                },
            )
            self.assertEqual(response.status_code, 200)
            job_id = UUID(response.json()["job_id"])
            asyncio.run(captured_tasks[0])

        status = self.client.get(f"/videos/jobs/{job_id}").json()
        self.assertEqual(status["result"]["video_url"], "https://example.com/videos/route-module.mp4")

        asset_response = self.client.get(
            "/videos/assets",
            params={"route_id": "01", "module_id": "r1m1", "component_kind": "video"},
        )
        self.assertEqual(asset_response.status_code, 200)
        asset = asset_response.json()
        self.assertEqual(asset["storage_path"], "https://example.com/videos/route-module.mp4")
        self.assertEqual(asset["estado"], "generado")
        self.assertEqual(asset["provenance"]["storyboard_source"], "reviewed_storyboard")

    def test_transformer_normalizes_storyboard_steps_for_remotion_components(self):
        """String steps from the storyboard prompt should become Remotion component objects."""
        storyboard = {
            "title": "Componentes Remotion",
            "scenes": [
                {
                    "scene_number": 1,
                    "narration": "Primero vemos el resumen.",
                    "visual_type": "text_card",
                    "visual_config": {"title": "Resumen", "subtitle": "Punto A • Punto B"},
                },
                {
                    "scene_number": 2,
                    "narration": "Luego ejecutamos un comando.",
                    "visual_type": "terminal_scene",
                    "visual_config": {
                        "title": "CLI demo",
                        "steps": ["cmd: gcloud projects list", "out: PROJECT_ID  NAME", "pause: 1"],
                    },
                },
                {
                    "scene_number": 3,
                    "narration": "Finalmente hacemos click en la interfaz.",
                    "visual_type": "screenshot_scene",
                    "visual_config": {
                        "steps": [
                            "cursor_move: 0.3 0.5",
                            "click_pulse: 0.3 0.5",
                            "type_into: 0.15 0.2 0.4 0.08 mario kart competitivo",
                            "highlight_box: 0.2 0.2 0.5 0.2",
                            "callout_balloon: 0.4 0.4 Revisa esta zona",
                            "typing_dots: 0.6 0.7",
                        ],
                    },
                },
                {
                    "scene_number": 4,
                    "narration": "Despues vemos la tendencia.",
                    "visual_type": "line_chart",
                    "visual_config": {
                        "title": "Curva de mejora",
                        "chartSeries": [{"name": "Velocidad", "data": [10, 25, 45, 70, 90]}],
                    },
                },
            ],
        }

        edit_decisions = asyncio.run(
            transform_storyboard_to_edit_decisions(
                storyboard=storyboard,
                audio_paths=[],
                durations=[2.0, 3.0, 4.0, 4.0],
                visual_paths=["", "", "/tmp/screenshot.png", ""],
                visual_is_video=[False, False, False, False],
                music_path=None,
                captions=None,
                total_duration=13.0,
                job_id="job-1",
            )
        )

        text_cut, terminal_cut, screenshot_cut, line_cut = edit_decisions["cuts"]
        self.assertEqual(text_cut["subtitle"], "Punto A • Punto B")
        self.assertEqual(terminal_cut["terminalTitle"], "CLI demo")
        self.assertEqual(terminal_cut["steps"][0], {"kind": "cmd", "text": "gcloud projects list"})
        self.assertEqual(terminal_cut["steps"][1], {"kind": "out", "text": "PROJECT_ID  NAME"})
        self.assertEqual(terminal_cut["steps"][2], {"kind": "pause", "seconds": 1.0})
        self.assertEqual(screenshot_cut["screenshotSteps"][0]["kind"], "cursor_move")
        self.assertEqual(screenshot_cut["screenshotSteps"][0]["to"], [0.3, 0.5])
        self.assertEqual(screenshot_cut["screenshotSteps"][2]["kind"], "type_into")
        self.assertEqual(screenshot_cut["screenshotSteps"][2]["region"], {"x": 0.15, "y": 0.2, "w": 0.4, "h": 0.08})
        self.assertEqual(screenshot_cut["screenshotSteps"][4]["text"], "Revisa esta zona")
        self.assertEqual(screenshot_cut["screenshotSteps"][5]["kind"], "typing_dots")
        self.assertEqual(line_cut["chartSeries"][0]["label"], "Velocidad")
        self.assertEqual(line_cut["chartSeries"][0]["data"][0], {"x": 1.0, "y": 10.0})
        self.assertEqual(line_cut["chartSeries"][0]["data"][4], {"x": 5.0, "y": 90.0})

    def test_custom_storyboard_render_hydrates_sparse_visual_configs(self):
        """Sparse reviewed scenes keep their chosen visual type with illustrative config."""
        service = VideoService()
        storyboard = {
            "title": "Domina Mario Kart: Estrategias para Ganar",
            "scenes": [
                {
                    "scene_number": 1,
                    "narration": "Veamos esto en el entorno real.",
                    "visual_type": "screenshot_scene",
                    "visual_config": {},
                    "teaching_point": "Anclar la estrategia en una accion observable.",
                },
                {
                    "scene_number": 2,
                    "narration": "Resumimos los indicadores clave.",
                    "visual_type": "kpi_grid",
                    "visual_config": {},
                },
                {
                    "scene_number": 3,
                    "narration": "Distribuimos el foco de entrenamiento.",
                    "visual_type": "pie_chart",
                    "visual_config": {},
                },
                {
                    "scene_number": 4,
                    "narration": "Seguimos la curva de mejora por intento.",
                    "visual_type": "line_chart",
                    "visual_config": {
                        "chartSeries": [{"name": "Velocidad", "data": [12, 28, 49, 73]}],
                    },
                },
                {
                    "scene_number": 5,
                    "narration": "Ejecutamos una verificacion simple.",
                    "visual_type": "terminal_scene",
                    "visual_config": {},
                    "teaching_point": "Verificar el aprendizaje con una salida observable.",
                },
                {
                    "scene_number": 6,
                    "narration": "Representamos la estrategia como un diagrama técnico aplicable al juego.",
                    "visual_type": "ai_illustration",
                    "visual_config": {},
                    "teaching_point": "Mostrar el modelo mental de la estrategia con una ilustración concreta.",
                },
            ],
        }

        hydrated = service._hydrate_storyboard_for_render(copy.deepcopy(storyboard))

        self.assertEqual(hydrated["scenes"][0]["visual_type"], "screenshot_scene")
        self.assertGreaterEqual(len(hydrated["scenes"][0]["visual_config"]["steps"]), 2)

        self.assertEqual(hydrated["scenes"][1]["visual_type"], "kpi_grid")
        self.assertGreaterEqual(len(hydrated["scenes"][1]["visual_config"]["chartData"]), 2)

        self.assertEqual(hydrated["scenes"][2]["visual_type"], "pie_chart")
        self.assertEqual(sum(item["value"] for item in hydrated["scenes"][2]["visual_config"]["chartData"]), 100)

        line_config = hydrated["scenes"][3]["visual_config"]
        self.assertEqual(line_config["chartSeries"][0]["label"], "Velocidad")
        self.assertEqual(line_config["chartSeries"][0]["data"][0], {"x": 1, "y": 12})
        self.assertEqual(line_config["chartSeries"][0]["data"][3], {"x": 4, "y": 73})
        self.assertEqual(line_config["xLabel"], "Intento")
        self.assertEqual(line_config["yLabel"], "Velocidad")

        self.assertEqual(hydrated["scenes"][4]["visual_type"], "terminal_scene")
        self.assertEqual(hydrated["scenes"][4]["visual_config"]["steps"][0]["kind"], "out")

        illustration_config = hydrated["scenes"][5]["visual_config"]
        self.assertIn("prompt", illustration_config)
        self.assertIn("estrategia", illustration_config["prompt"].lower())
        self.assertIn("avoid biology", illustration_config["prompt"].lower())
        self.assertGreater(len(illustration_config["bullets"]), 0)

    def test_render_hydration_makes_every_visual_type_topic_specific(self):
        """Every supported scene type receives a complete topic-aligned render config."""
        service = VideoService()
        scene_types = [
            "text_card", "hero_title", "stat_card", "callout", "comparison",
            "bar_chart", "line_chart", "pie_chart", "kpi_grid", "progress_bar",
            "terminal_scene", "screenshot_scene", "ai_video", "ai_illustration",
        ]
        configs = {
            "stat_card": {"stat": "3 pasos", "subtitle": "Observar, decidir y verificar"},
            "bar_chart": {"chartData": [{"label": "Antes", "value": 2}, {"label": "Despues", "value": 5}]},
            "line_chart": {"chartSeries": [{"name": "Comprension", "data": [1, 3, 5]}]},
            "pie_chart": {"chartData": [{"label": "Practica", "value": 60}, {"label": "Revision", "value": 40}]},
            "kpi_grid": {"chartData": [{"label": "Pasos", "value": 3}, {"label": "Chequeos", "value": 2}]},
            "terminal_scene": {"steps": ["cmd: pytest -q", "out: 12 passed"]},
            "screenshot_scene": {
                "url": "https://example.com/lesson",
                "steps": ["cursor_move: 0.2 0.3", "callout_balloon: 0.4 0.5 Verifica el resultado"],
            },
        }
        scenes = [
            {
                "scene_number": index,
                "narration": "Aplicamos el ciclo observar, decidir y verificar con evidencia.",
                "visual_type": visual_type,
                "visual_config": configs.get(visual_type, {}),
                "teaching_point": "Aplicar el ciclo de decision con evidencia",
                "pedagogical_intent": "Convertir el concepto en una accion verificable",
                "visual_rationale": "La composicion muestra la relacion entre accion y evidencia",
            }
            for index, visual_type in enumerate(scene_types, start=1)
        ]

        hydrated = service._hydrate_storyboard_for_render({"title": "Decisiones con evidencia", "scenes": scenes})

        for scene in hydrated["scenes"]:
            self.assertTrue(scene["visual_config"])
        self.assertIn("decisiones con evidencia", hydrated["scenes"][12]["visual_config"]["prompt"].lower())
        self.assertIn("action and evidence", hydrated["scenes"][13]["visual_config"]["prompt"].lower())

    def test_render_hydration_degrades_malformed_chart_payloads_without_crashing(self):
        service = VideoService()
        storyboard = {
            "title": "Datos seguros",
            "scenes": [
                {
                    "scene_number": 1,
                    "narration": "No fingimos un reparto.",
                    "visual_type": "pie_chart",
                    "visual_config": {"chartData": 42},
                    "teaching_point": "Explicar el reparto solo con evidencia valida",
                },
                {
                    "scene_number": 2,
                    "narration": "No fingimos una tendencia.",
                    "visual_type": "line_chart",
                    "visual_config": {"chartSeries": [{"name": "Calidad", "data": ["N/A"]}]},
                    "teaching_point": "Explicar la tendencia solo con puntos validos",
                },
            ],
        }

        hydrated = service._hydrate_storyboard_for_render(storyboard)

        self.assertEqual([scene["visual_type"] for scene in hydrated["scenes"]], ["callout", "callout"])

    def test_transformer_emits_repository_owned_educational_visual_direction(self):
        storyboard = {
            "title": "Decisiones con evidencia",
            "scenes": [{
                "scene_number": 1,
                "narration": "Comparamos dos decisiones.",
                "visual_type": "comparison",
                "visual_config": {
                    "title": "Misma pregunta, distinto criterio",
                    "leftLabel": "Sin evidencia",
                    "leftValue": "Adivina",
                    "rightLabel": "Con evidencia",
                    "rightValue": "Verifica",
                },
            }],
        }

        edit_decisions = asyncio.run(transform_storyboard_to_edit_decisions(
            storyboard=storyboard,
            audio_paths=[],
            durations=[5.0],
            visual_paths=[""],
            visual_is_video=[False],
            music_path=None,
            captions=None,
            total_duration=5.0,
            job_id="job-theme",
        ))

        self.assertEqual(edit_decisions["theme"], "xertica-education")
        self.assertEqual(edit_decisions["themeConfig"]["accentColor"], "#F4B942")
        self.assertEqual(edit_decisions["cuts"][0]["title"], "Misma pregunta, distinto criterio")

    def test_generate_video_uses_reviewed_storyboard_as_render_source_of_truth(self):
        """POST /videos/generate renders from the reviewed storyboard and retains provenance."""
        component_id = uuid4()
        service = VideoService()
        service._supabase = None
        service._fallback_assets[component_id] = {
            "id": str(uuid4()),
            "componente_id": str(component_id),
            "tipo": "video",
            "estado": "borrador",
            "provenance": {"legacy_marker": "keep-me"},
        }

        reviewed_storyboard = {
            "title": "Razonamiento avanzado para decisiones de negocio",
            "total_word_budget": 180,
            "scenes": [
                {
                    "scene_number": 1,
                    "narration": "Empezamos por la decision que queremos proteger antes de hablar de herramientas.",
                    "visual_type": "callout",
                    "visual_config": {
                        "callout_style": "info",
                        "text": "La decision define la evidencia que importa.",
                    },
                    "teaching_point": "Conectar el modulo con una decision concreta.",
                    "pedagogical_intent": "Abrir con el objetivo del modulo, no con una intro decorativa.",
                    "teaching_pattern": "framing_question",
                    "visual_rationale": "El callout concentra la pregunta guia sin ruido visual.",
                    "grounding_status": "module_grounded",
                },
                {
                    "scene_number": 2,
                    "narration": "Luego comparamos una respuesta rapida con un razonamiento que verifica supuestos.",
                    "visual_type": "comparison",
                    "visual_config": {
                        "leftLabel": "Rapido",
                        "leftValue": "Acepta supuestos",
                        "rightLabel": "Verificable",
                        "rightValue": "Revisa evidencia",
                    },
                    "teaching_point": "Mostrar el contraste central del concepto.",
                    "pedagogical_intent": "Corregir el malentendido de que velocidad equivale a calidad.",
                    "teaching_pattern": "misconception_correction",
                    "visual_rationale": "La comparacion hace visible el trade-off pedagogico.",
                    "grounding_status": "module_grounded",
                },
            ],
        }
        captured_tasks = []
        render_capture = {}

        def capture_task(coro):
            captured_tasks.append(coro)
            return None

        async def fake_execute(self, plan):
            render_capture["storyboard"] = plan.storyboard.model_dump()
            self.total_duration = 12.5
            self.stage_outputs["upload"] = {"url": "https://example.com/videos/reviewed-storyboard.mp4"}

        app.dependency_overrides[get_video_service] = lambda: service

        with patch("services.video.service.asyncio.create_task", side_effect=capture_task), patch(
            "services.video.executor.RenderExecutor.execute",
            new=fake_execute,
        ):
            response = self.client.post(
                "/videos/generate",
                json={
                    "component_id": str(component_id),
                    "custom_storyboard": reviewed_storyboard,
                    "use_mock": False,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(captured_tasks), 1)
            job_id = UUID(response.json()["job_id"])
            asyncio.run(captured_tasks[0])

        self.assertEqual(render_capture["storyboard"], reviewed_storyboard)

        status_response = self.client.get(f"/videos/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200)
        result = status_response.json()["result"]
        self.assertEqual(result["video_url"], "https://example.com/videos/reviewed-storyboard.mp4")
        self.assertEqual(result["provenance"]["storyboard_source"], "reviewed_storyboard")
        self.assertEqual(result["provenance"]["storyboard"], reviewed_storyboard)
        self.assertEqual(result["provenance"]["render_profile"]["resolution"], "1280x720")
        self.assertEqual(result["provenance"]["render_profile"]["codec"], "h264")

        asset = service._fallback_assets[component_id]
        self.assertEqual(asset["storage_path"], "https://example.com/videos/reviewed-storyboard.mp4")
        self.assertEqual(asset["provenance"]["legacy_marker"], "keep-me")
        self.assertEqual(asset["provenance"]["storyboard"], reviewed_storyboard)
        self.assertEqual(asset["provenance"]["storyboard_source"], "reviewed_storyboard")

    def test_completed_video_job_keeps_only_final_mp4_and_lightweight_retention_metadata(self):
        """Completed video jobs clean intermediates and expose the MVP retention profile."""
        component_id = uuid4()
        service = VideoService()
        service._supabase = None
        service._fallback_assets[component_id] = {
            "id": str(uuid4()),
            "componente_id": str(component_id),
            "tipo": "video",
            "estado": "borrador",
        }

        captured_tasks = []
        composer_workspace = tempfile.TemporaryDirectory()
        self.addCleanup(composer_workspace.cleanup)

        def capture_task(coro):
            captured_tasks.append(coro)
            return None

        async def fake_execute(self, plan):
            temp_dir = f"/tmp/render_{plan.job_id}"
            remotion_dir = os.path.join(composer_workspace.name, "public", str(plan.job_id))
            os.makedirs(os.path.join(temp_dir, "tts"), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, "imagen"), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, "veo"), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, "remotion"), exist_ok=True)
            os.makedirs(remotion_dir, exist_ok=True)
            with open(os.path.join(remotion_dir, "output.mp4"), "wb") as handle:
                handle.write(b"temporary remotion output")

            for relative_path in (
                "tts/scene-1.wav",
                "imagen/scene-2.png",
                "veo/scene-3.mp4",
                "remotion/props.json",
            ):
                full_path = os.path.join(temp_dir, relative_path)
                with open(full_path, "w", encoding="utf-8") as handle:
                    handle.write("temp")

            self.total_duration = 9.75
            self.stage_outputs["upload"] = {"url": "https://example.com/videos/final-720p.mp4"}

        app.dependency_overrides[get_video_service] = lambda: service

        with patch("services.video.service.settings.remotion_composer_path", composer_workspace.name), patch(
            "services.video.service.asyncio.create_task", side_effect=capture_task
        ), patch(
            "services.video.executor.RenderExecutor.execute",
            new=fake_execute,
        ):
            response = self.client.post(
                "/videos/generate",
                json={
                    "component_id": str(component_id),
                    "custom_storyboard": {
                        "title": "Retencion MVP",
                        "total_word_budget": 120,
                        "scenes": [
                            {
                                "scene_number": 1,
                                "narration": "Explicamos la idea principal.",
                                "visual_type": "callout",
                                "visual_config": {
                                    "callout_style": "info",
                                    "text": "Idea principal",
                                },
                                "teaching_point": "Ensenar el concepto central.",
                                "pedagogical_intent": "Dar un punto de partida claro.",
                                "teaching_pattern": "framing_question",
                                "visual_rationale": "El callout concentra la atencion en la idea clave.",
                                "grounding_status": "module_grounded",
                            }
                        ],
                    },
                    "use_mock": False,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(captured_tasks), 1)
            job_id = UUID(response.json()["job_id"])
            asyncio.run(captured_tasks[0])

        temp_dir = f"/tmp/render_{job_id}"
        self.assertFalse(os.path.exists(temp_dir))
        self.assertFalse(os.path.exists(os.path.join(composer_workspace.name, "public", str(job_id))))

        status_response = self.client.get(f"/videos/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200)
        result = status_response.json()["result"]
        retention = result["provenance"]["artifact_retention"]

        self.assertEqual(result["video_url"], "https://example.com/videos/final-720p.mp4")
        self.assertEqual(result["provenance"]["render_profile"]["resolution"], "1280x720")
        self.assertEqual(result["provenance"]["render_profile"]["codec"], "h264")
        self.assertEqual(result["provenance"]["render_profile"]["container"], "mp4")
        self.assertEqual(retention["successful_render"]["retained_artifacts"], ["final_mp4", "render_provenance"])
        self.assertEqual(
            retention["successful_render"]["discarded_intermediates"],
            ["scene_tts", "playwright_screenshots", "imagen_pngs", "veo_clips", "remotion_workdir"],
        )
        self.assertEqual(retention["failed_render"]["ttl_hours"], 24)
        self.assertEqual(retention["debug_mode"]["ttl_hours"], 24)

        asset = service._fallback_assets[component_id]
        self.assertEqual(asset["storage_path"], "https://example.com/videos/final-720p.mp4")
        self.assertEqual(
            asset["provenance"]["artifact_retention"]["successful_render"]["retained_artifacts"],
            ["final_mp4", "render_provenance"],
        )

    def test_concept_explanation_smoke_flow_preserves_reviewed_storyboard_into_completed_job(self):
        """Module + KB -> storyboard review -> render job composes end to end with fakes."""
        route_id = uuid4()
        module_id = uuid4()
        component_id = uuid4()
        llm = _FakeLLM()
        kb = _FakeKB(
            [
                GroundedChunk(
                    content="El razonamiento avanzado conecta evidencia con decisiones de negocio.",
                    citation=Citation(
                        source_id=uuid4(),
                        title="Manual de evidencia",
                        url="https://example.com/evidencia",
                        snippet="conecta evidencia con decisiones",
                        score=0.95,
                        verificada_google=True,
                    ),
                )
            ]
        )
        service = _video_service_with_context(route_id, module_id, llm)
        service._fallback_assets[component_id] = {
            "id": str(uuid4()),
            "componente_id": str(component_id),
            "tipo": "video",
            "estado": "borrador",
        }

        app.dependency_overrides[get_video_service] = lambda: service
        app.dependency_overrides[get_knowledge_base] = lambda: kb

        storyboard_response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": str(route_id),
                "module_id": str(module_id),
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(storyboard_response.status_code, 200)
        storyboard_payload = storyboard_response.json()
        self.assertEqual(storyboard_payload["grounding"]["status"], "kb_grounded")
        generated_storyboard = storyboard_payload["storyboard"]
        original_teaching_point = generated_storyboard["scenes"][0]["teaching_point"]

        reviewed_storyboard = copy.deepcopy(generated_storyboard)
        reviewed_storyboard["scenes"][0]["narration"] = (
            "Antes de automatizar, revisamos la decision de negocio y la evidencia que realmente la cambia."
        )

        captured_tasks = []
        render_capture = {}

        def capture_task(coro):
            captured_tasks.append(coro)
            return None

        async def fake_execute(self, plan):
            render_capture["storyboard"] = plan.storyboard.model_dump()
            self.total_duration = 14.2
            self.stage_outputs["upload"] = {"url": "https://example.com/videos/concept-smoke.mp4"}

        with patch("services.video.service.asyncio.create_task", side_effect=capture_task), patch(
            "services.video.executor.RenderExecutor.execute",
            new=fake_execute,
        ):
            generate_response = self.client.post(
                "/videos/generate",
                json={
                    "component_id": str(component_id),
                    "custom_storyboard": reviewed_storyboard,
                    "use_mock": False,
                },
            )
            self.assertEqual(generate_response.status_code, 200)
            self.assertEqual(len(captured_tasks), 1)
            job_id = UUID(generate_response.json()["job_id"])
            asyncio.run(captured_tasks[0])

        self.assertEqual(render_capture["storyboard"], reviewed_storyboard)

        status_response = self.client.get(f"/videos/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200)
        result = status_response.json()["result"]

        self.assertEqual(result["video_url"], "https://example.com/videos/concept-smoke.mp4")
        self.assertEqual(result["provenance"]["storyboard_source"], "reviewed_storyboard")
        self.assertEqual(
            result["provenance"]["storyboard"]["scenes"][0]["teaching_point"],
            original_teaching_point,
        )
        self.assertEqual(
            result["provenance"]["storyboard"]["scenes"][0]["narration"],
            reviewed_storyboard["scenes"][0]["narration"],
        )
        self.assertEqual(
            result["provenance"]["artifact_retention"]["successful_render"]["retained_artifacts"],
            ["final_mp4", "render_provenance"],
        )

    def test_storyboard_response_exposes_reviewable_teaching_contract(self):
        """POST /videos/storyboard returns review metadata without breaking render input."""
        route_id = uuid4()
        module_id = uuid4()

        class FakeVideoService:
            async def generate_storyboard(self, **kwargs):
                return {
                    "storyboard": {
                        "title": "Razonamiento avanzado",
                        "total_word_budget": 300,
                        "scenes": [
                            {
                                "scene_number": 1,
                                "narration": "Primero distinguimos una respuesta automatica de un razonamiento verificable.",
                                "visual_type": "comparison",
                                "visual_config": {
                                    "left_title": "Respuesta rapida",
                                    "right_title": "Razonamiento verificable",
                                },
                                "teaching_point": "Distinguir velocidad de calidad de razonamiento.",
                                "pedagogical_intent": "Corregir el malentendido de que responder rapido equivale a razonar mejor.",
                                "teaching_pattern": "misconception_correction",
                                "visual_rationale": "Una comparacion muestra el contraste sin inventar metricas.",
                                "grounding_status": "kb_grounded",
                            }
                        ],
                    },
                    "grounding": {
                        "status": "kb_grounded",
                        "query": "Razonamiento avanzado",
                        "k": kwargs["k"],
                        "chunks": [
                            {
                                "content": "El razonamiento avanzado requiere verificar supuestos.",
                                "citation": {
                                    "source_id": str(uuid4()),
                                    "title": "Manual IA",
                                    "url": "https://example.com/manual",
                                    "score": 0.91,
                                    "verificada_google": True,
                                },
                            }
                        ],
                    },
                }

        app.dependency_overrides[get_video_service] = lambda: FakeVideoService()
        app.dependency_overrides[get_knowledge_base] = lambda: object()

        response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": str(route_id),
                "module_id": str(module_id),
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["grounding"]["status"], "kb_grounded")
        scene = data["storyboard"]["scenes"][0]
        self.assertEqual(scene["teaching_point"], "Distinguir velocidad de calidad de razonamiento.")
        self.assertEqual(scene["pedagogical_intent"], "Corregir el malentendido de que responder rapido equivale a razonar mejor.")
        self.assertEqual(scene["teaching_pattern"], "misconception_correction")
        self.assertEqual(scene["visual_rationale"], "Una comparacion muestra el contraste sin inventar metricas.")
        self.assertEqual(scene["grounding_status"], "kb_grounded")

        render_input = StoryboardRequest.model_validate(data["storyboard"])
        self.assertEqual(render_input.scenes[0].visual_type, "comparison")

    def test_storyboard_generation_uses_module_goal_as_spine_and_kb_as_evidence(self):
        """POST /videos/storyboard returns a KB-grounded Video de Explicacion Conceptual."""
        route_id = uuid4()
        module_id = uuid4()
        llm = _FakeLLM()
        kb = _FakeKB(
            [
                GroundedChunk(
                    content="El razonamiento avanzado requiere verificar supuestos antes de aceptar una conclusion automatica.",
                    citation=Citation(
                        source_id=uuid4(),
                        title="Manual de razonamiento",
                        url="https://example.com/razonamiento",
                        snippet="verificar supuestos",
                        score=0.94,
                        verificada_google=True,
                    ),
                )
            ]
        )

        app.dependency_overrides[get_video_service] = lambda: _video_service_with_context(route_id, module_id, llm)
        app.dependency_overrides[get_knowledge_base] = lambda: kb

        response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": str(route_id),
                "module_id": str(module_id),
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["grounding"]["status"], "kb_grounded")
        self.assertEqual(len(data["grounding"]["chunks"]), 1)
        self.assertIn("Ruta de Inteligencia Avanzada", kb.queries[0]["text"])
        self.assertIn("decisiones de negocio verificables", kb.queries[0]["text"])

        storyboard = data["storyboard"]
        self.assertIn("decisiones de negocio", storyboard["title"].lower())
        self.assertGreaterEqual(len(storyboard["scenes"]), 5)
        self.assertLessEqual(len(storyboard["scenes"]), 7)
        self.assertEqual(storyboard["scenes"][0]["visual_type"], "callout")
        visual_types = [scene["visual_type"] for scene in storyboard["scenes"]]
        self.assertNotIn("ai_video", visual_types)
        self.assertNotIn("ai_illustration", visual_types)

        for scene in storyboard["scenes"]:
            self.assertEqual(scene["grounding_status"], "kb_grounded")
            self.assertTrue(scene["teaching_point"])
            self.assertTrue(scene["pedagogical_intent"])
            self.assertTrue(scene["teaching_pattern"])
            self.assertTrue(scene["visual_rationale"])

        render_input = StoryboardRequest.model_validate(storyboard)
        self.assertEqual(len(render_input.scenes), 5)

    def test_storyboard_generation_supports_persisted_string_module_ids_from_route_details(self):
        """POST /videos/storyboard works for real routes whose module ids are persisted strings like r1m1."""
        route_id = uuid4()
        module_id = "r1m1"
        llm = _FakeLLM()
        kb = _FakeKB(
            [
                GroundedChunk(
                    content="El razonamiento avanzado requiere verificar supuestos antes de aceptar una conclusion automatica.",
                    citation=Citation(
                        source_id=uuid4(),
                        title="Manual de razonamiento",
                        url="https://example.com/razonamiento",
                        snippet="verificar supuestos",
                        score=0.94,
                        verificada_google=True,
                    ),
                )
            ]
        )

        app.dependency_overrides[get_video_service] = lambda: _video_service_with_context(
            route_id,
            module_id,
            llm,
            include_modules_table=False,
        )
        app.dependency_overrides[get_knowledge_base] = lambda: kb

        response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": str(route_id),
                "module_id": module_id,
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["grounding"]["status"], "kb_grounded")
        self.assertIn("Ruta de Inteligencia Avanzada", kb.queries[0]["text"])

    def test_storyboard_generation_supports_short_route_ids_used_by_existing_routes(self):
        """POST /videos/storyboard resolves route ids like 01 the same way RouteService does."""
        route_id = "01"
        module_id = "r1m1"
        llm = _FakeLLM()
        kb = _FakeKB([])

        app.dependency_overrides[get_video_service] = lambda: _video_service_with_context(
            UUID(int=1),
            module_id,
            llm,
            include_modules_table=False,
        )
        app.dependency_overrides[get_knowledge_base] = lambda: kb

        response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": route_id,
                "module_id": module_id,
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(kb.queries[0]["learning_path_id"], UUID(int=1))

    def test_storyboard_generation_uses_route_service_fallback_when_video_service_has_no_supabase(self):
        """Local dev without Supabase should still load route/module context from the shared route service."""
        llm = _FakeLLM()
        kb = _FakeKB([])
        service = VideoService(llm_adapter=llm)
        service._supabase = None

        app.dependency_overrides[get_video_service] = lambda: service
        app.dependency_overrides[get_knowledge_base] = lambda: kb

        response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": "01",
                "module_id": "r1m1",
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Introducción", kb.queries[0]["text"])
        self.assertNotEqual(response.json()["storyboard"]["title"], "Introducción a Xertica Education")

    def test_storyboard_generation_falls_back_honestly_when_kb_is_empty(self):
        """POST /videos/storyboard distinguishes Module-grounded fallback from KB-grounded output."""
        route_id = uuid4()
        module_id = uuid4()
        llm = _FakeLLM()
        kb = _FakeKB([])

        app.dependency_overrides[get_video_service] = lambda: _video_service_with_context(route_id, module_id, llm)
        app.dependency_overrides[get_knowledge_base] = lambda: kb

        response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": str(route_id),
                "module_id": str(module_id),
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["grounding"]["status"], "module_grounded")
        self.assertEqual(data["grounding"]["chunks"], [])

        storyboard = data["storyboard"]
        self.assertGreaterEqual(len(storyboard["scenes"]), 5)
        self.assertLessEqual(len(storyboard["scenes"]), 7)
        for scene in storyboard["scenes"]:
            self.assertEqual(scene["grounding_status"], "module_grounded")
            self.assertNotEqual(scene["visual_type"], "screenshot_scene")
            self.assertTrue(scene["teaching_point"])
            self.assertTrue(scene["visual_rationale"])

    def test_storyboard_generation_repairs_decorative_visuals_into_useful_teaching_scenes(self):
        """POST /videos/storyboard repairs decorative visuals that do not teach the concept."""
        route_id = uuid4()
        module_id = uuid4()
        llm = _BadVisualStoryboardLLM()
        kb = _FakeKB(
            [
                GroundedChunk(
                    content="La interfaz verificada se usa para revisar decisiones con contexto.",
                    citation=Citation(
                        source_id=uuid4(),
                        title="Guia verificada",
                        url="https://example.com/console",
                        snippet="revisar decisiones",
                        score=0.92,
                        verificada_google=True,
                    ),
                )
            ]
        )

        app.dependency_overrides[get_video_service] = lambda: _video_service_with_context(route_id, module_id, llm)
        app.dependency_overrides[get_knowledge_base] = lambda: kb

        response = self.client.post(
            "/videos/storyboard",
            json={
                "route_id": str(route_id),
                "module_id": str(module_id),
                "component_kind": "video",
                "k": 4,
            },
        )

        self.assertEqual(response.status_code, 200)
        storyboard = response.json()["storyboard"]
        visual_types = [scene["visual_type"] for scene in storyboard["scenes"]]

        self.assertLessEqual(visual_types.count("ai_video"), 1)
        self.assertNotIn("bar_chart", visual_types)
        self.assertNotIn("screenshot_scene", visual_types)
        self.assertNotIn("ai_illustration", visual_types)
        # The original decorative illustration was repaired rather than forced.
        self.assertNotEqual(storyboard["scenes"][5]["visual_type"], "ai_illustration")

        repaired_scene = storyboard["scenes"][4]
        self.assertIn(repaired_scene["visual_type"], {"callout", "text_card", "comparison", "terminal_scene"})
        self.assertIn("walkthrough", repaired_scene["visual_rationale"].lower())

        render_input = StoryboardRequest.model_validate(storyboard)
        self.assertEqual(len(render_input.scenes), 6)

if __name__ == "__main__":
    unittest.main()
