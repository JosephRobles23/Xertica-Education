import os
import sys
import asyncio
from uuid import UUID

# Ensure local imports work correctly
sys.path.insert(0, ".")

from services.video.service import VideoService
from models.dto.requests import StoryboardRequest, VideoScene

async def main():
    print("Initializing VideoService...")
    video_service = VideoService()

    # Define the storyboard about working as a Tech Lead with new people
    storyboard = StoryboardRequest(
        title="Claves para el Rol de Tech Lead",
        total_word_budget=200,
        scenes=[
            VideoScene(
                scene_number=1,
                narration="Convertirse en Tech Lead significa transicionar de escribir código a guiar personas. Tu principal objetivo es desbloquear a tu equipo y establecer estándares.",
                visual_type="ai_video",
                visual_config={
                    "prompt": "A professional cinematic abstract animation showing glowing connection nodes forming a network, technology background, deep blue and teal tones, clean lighting, 16:9 aspect ratio."
                }
            ),
            VideoScene(
                scene_number=2,
                narration="En un proyecto con personas nuevas, dedica las primeras semanas a escuchar y entender sus fortalezas y debilidades.",
                visual_type="comparison",
                visual_config={
                    "leftLabel": "Fortalezas",
                    "leftValue": "Escuchar y mapear capacidades",
                    "rightLabel": "Debilidades",
                    "rightValue": "Mapear cuellos de botella"
                }
            ),
            VideoScene(
                scene_number=3,
                narration="Establece rituales claros de revisión y asegura que todos tengan voz en las decisiones de diseño técnico.",
                visual_type="bar_chart",
                visual_config={
                    "title": "Adopción de ADRs",
                    "showValues": True,
                    "showGrid": True,
                    "chartData": [
                        {"label": "Semana 1", "value": 30},
                        {"label": "Semana 2", "value": 65},
                        {"label": "Semana 3", "value": 90}
                    ]
                }
            ),
            VideoScene(
                scene_number=4,
                narration="Utiliza tableros de control para monitorear el avance y los estándares de calidad del proyecto.",
                visual_type="screenshot_scene",
                visual_config={
                    "url": "https://google.com",
                    "steps": [
                        {"kind": "cursor_move", "to": [0.48, 0.42], "durationSeconds": 1.0},
                        {"kind": "click_pulse", "at": [0.48, 0.42], "durationSeconds": 0.3},
                        {"kind": "type_into", "region": {"x": 0.35, "y": 0.40, "w": 0.3, "h": 0.05}, "text": "Xertica Education", "typeSpeed": 0.03},
                        {"kind": "pause", "seconds": 0.2},
                        {"kind": "cursor_move", "to": [0.48, 0.52], "durationSeconds": 0.8},
                        {"kind": "click_pulse", "at": [0.48, 0.52], "durationSeconds": 0.3},
                        {"kind": "highlight_box", "region": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}, "durationSeconds": 2.0}
                    ]
                }
            ),
            VideoScene(
                scene_number=5,
                narration="En resumen, el éxito radica en la comunicación continua, la claridad de objetivos y el liderazgo empático.",
                visual_type="stat_card",
                visual_config={
                    "stat": "100%",
                    "subtitle": "Liderazgo Empático y Objetivos Claros"
                }
            )
        ]
    )

    print("\nTriggering video generation job...")
    # Use use_mock=False to run the real pipeline (which falls back gracefully to mocks if system packages are missing)
    job_id = await video_service.generate_video(
        component_id=None,
        custom_storyboard=storyboard,
        use_mock=False
    )
    print(f"Job successfully created! Job ID: {job_id}")

    print("\nPolling job progress...")
    while True:
        status = await video_service.get_video_job_status(job_id)
        if not status:
            print("Job not found!")
            break
            
        print(f"Status: {status.status.value} | Progress: {render_progress_bar(status.progress)}")
        
        if status.status.value == "completed":
            print("\n🎉 GENERATION SUCCESSFUL!")
            print(f"Video URL: {status.result.video_url}")
            print(f"Duration: {status.result.duration_seconds} seconds")
            print(f"Estimated Cost: ${status.result.cost_usd}")
            break
        elif status.status.value == "failed":
            print(f"\n❌ Job failed: {status.error}")
            break
            
        await asyncio.sleep(1.0)

def render_progress_bar(pct: int) -> str:
    filled = int(pct / 10)
    return "[" + "#" * filled + "-" * (10 - filled) + f"] {pct}%"

if __name__ == "__main__":
    asyncio.run(main())
