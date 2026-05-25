import urllib.request
import json
import time
import os

api_key = "REDACTED_ELEVEN_KEY"
voice_id = "JBFqnCBsd6RMkjVDRZzb"  # George (Premade Warm Resonant Male Voice)
model_id = "eleven_v3"

url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

payload = {
    "text": "Hello! This is George, testing the brand-new Eleven v3 model by ElevenLabs. Doesn't this voice sound incredibly warm and natural in English?",
    "model_id": model_id,
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "accept": "audio/mpeg"
    },
    method="POST"
)

output_path = "/Users/a84513/.gemini/antigravity/brain/12f712b1-84e7-40f4-b31d-22550371771a/scratch/test_eleven_v3_english.mp3"

print(f"[DEBUG] Synthesizing speech using model '{model_id}' (Male voice: George)...")
try:
    start_time = time.time()
    with urllib.request.urlopen(req) as response:
        audio_data = response.read()
    duration = time.time() - start_time
    print(f"[DEBUG] TTS request successful in {duration:.2f}s, received {len(audio_data)} bytes.")
    
    with open(output_path, "wb") as f:
        f.write(audio_data)
    print(f"[SUCCESS] Audio saved to {output_path}")
    print(f"File exists: {os.path.exists(output_path)}, Size: {os.path.getsize(output_path)} bytes")
except Exception as e:
    print(f"[ERROR] Failed to synthesize speech: {e}")
    if hasattr(e, 'read'):
        try:
            print(f"Error response: {e.read().decode('utf-8')}")
        except Exception:
            pass
