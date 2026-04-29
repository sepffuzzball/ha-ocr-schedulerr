# Open-Weight Vision Models for Schedule Parsing

This document lists recommended open-weight vision-capable models that work with OpenAI-compatible endpoints (e.g., LM Studio, vLLM, Ollama).

## Quick Start with LM Studio

1. Install [LM Studio](https://lmstudio.ai/) on a remote machine
2. Search and download one of the models below
3. Start the server: `lmstudio --server` (default port 1234)
4. Set in `.env`:
   ```env
   OPENAI_BASE_URL=http://<remote-host>:1234/v1
   OPENAI_API_KEY=local-key
   OPENAI_MODEL=<model-name>
   ```

## Recommended Models

### Best Quality (Large, 7B+)

| Model | Size | Notes |
|---|---|---|
| **Qwen2.5-VL-7B-Instruct** | 7B | Excellent vision understanding, strong JSON output |
| **LLaVA-NeXT-7B** | 7B | Good general-purpose vision, widely tested |
| **Phi-3.5-vision-instruct** | 4B | Microsoft's compact model with solid vision capabilities |

### Lightweight (Faster, Lower VRAM)

| Model | Size | Notes |
|---|---|---|
| **Qwen2-VL-2B-Instruct** | 2B | Very fast, decent accuracy for simple schedules |
| **LLaVA-1.6-Mistral-7B** | 7B | Good balance of speed and quality |

### For High Accuracy (Large)

| Model | Size | Notes |
|---|---|---|
| **Qwen2.5-VL-72B-Instruct** | 72B | Best accuracy, requires significant VRAM |
| **InternVL2-8B** | 8B | Strong OCR and table parsing capabilities |

## Model Selection Tips

1. **For schedule screenshots**: Qwen2.5-VL-7B or Phi-3.5-vision-instruct offer the best balance
2. **For low VRAM (<8GB)**: Use Qwen2-VL-2B or LLaVA-1.6-Mistral-7B with quantization
3. **For maximum accuracy**: Qwen2.5-VL-72B if you have 48GB+ VRAM

## LM Studio Model Names

When using LM Studio, the model name in `OPENAI_MODEL` should match what LM Studio reports (usually the filename without `.gguf`). Example:
```env
OPENAI_MODEL=Qwen/Qwen2.5-VL-7B-Instruct-GGUF
```

## Testing Your Setup

After configuring a model, send a test schedule image and check logs for:
- `AI parser response:` showing valid JSON
- 5 entries parsed (for the example schedule)
- No fallback to OCR in logs

If you see "AI parser failed; falling back to OCR", verify:
1. The endpoint is reachable (`curl http://<host>:1234/v1/models`)
2. The model name matches exactly what LM Studio loaded
3. The API key (if required) is correct

## Quantization for Lower VRAM

For 7B models, use Q4_K_M or Q5_K_M quantization:
- Reduces VRAM from ~16GB to ~6GB
- Minimal accuracy loss for schedule parsing tasks

## Model Download Links

- **Hugging Face**: https://huggingface.co/collections/Qwen/qwen25-vl-67c... (Qwen2.5-VL)
- **LLaVA**: https://huggingface.co/llava-hf (LLaVA-NeXT variants)
- **Phi-3.5 Vision**: https://huggingface.co/microsoft/Phi-3.5-vision-instruct
