import os
import asyncio
import time
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(
    vertexai=True,
    project="xertica-agent-courses",
    location="us-central1",
)

async def test():
    # Submit generation
    print("Submitting clip generation...")
    operation = client.models.generate_videos(
        model="veo-3.1-generate-001",
        prompt="A glowing blue digital node, cinematic.",
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=6,
        ),
    )
    
    # Poll until done
    while not operation.done:
        print("Waiting...")
        await asyncio.sleep(20)
        operation = client.operations.get(operation)
        
    generated_video = operation.response.generated_videos[0]
    print("\nGenerated Video attributes:")
    print(dir(generated_video))
    print("\nGenerated Video dict/vars:")
    try:
        print(vars(generated_video))
    except Exception as e:
        print("vars failed:", e)
        
    print("\nVideo object:")
    print(generated_video.video)
    print("\nVideo object attributes:")
    print(dir(generated_video.video))
    print("\nVideo object dict/vars:")
    try:
        print(vars(generated_video.video))
    except Exception as e:
        print("vars failed:", e)

asyncio.run(test())
