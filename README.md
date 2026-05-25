# Gemma Video Project

This project explores and implements video understanding capabilities using Gemma 4 models.

## Research Findings: Gemma 4 Video Capabilities

Based on official documentation (https://ai.google.dev/gemma/docs/capabilities/vision/video):

### Supported Models
- `gemma-4-E2B-it`
- `gemma-4-31B-it`

### Capabilities
- **Video Description:** Describing content within a video.
- **Spatial Reasoning:** Interpreting relationships between objects in the video.
- **Situational Awareness:** Understanding the context and events in a video.
- **Temporal Analysis:** Analyzing changes over time across timestamps.

### Technical Implementation
- **Library:** Hugging Face `transformers`.
- **Primary Classes:** `AutoModelForMultimodalLM`, `AutoProcessor`.
- **Input Format:** Standard formats like MP4.
- **Workflow:** Videos can be passed as URLs directly into chat templates.

### Example Usage Pattern
```python
from transformers import AutoModelForMultimodalLM, AutoProcessor

model_id = "google/gemma-4-31b-it"
model = AutoModelForMultimodalLM.from_pretrained(model_id)
processor = AutoProcessor.from_pretrained(model_id)

# Process video and prompt
# ... (standard transformers multimodal workflow)
```
