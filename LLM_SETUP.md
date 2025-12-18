# LLM Enhancement Setup Guide

The Criteria Comparison feature now supports AI-powered enhancements using Large Language Models (LLMs) for better semantic matching and insights.

**🎉 ALL RECOMMENDED OPTIONS ARE FREE!**

## Features

1. **Semantic Similarity Detection**: Finds criteria that are conceptually similar even if named differently
2. **Intelligent Summaries**: Generates concise comparisons of how different frameworks define the same criterion
3. **Related Criteria Grouping**: Groups criteria that belong to the same conceptual category

## Supported LLM Providers (FREE Options First!)

### Option 1: Hugging Face Inference API (⭐ RECOMMENDED - FREE, Best Quality)

**Setup:**
1. Get a free API key from https://huggingface.co/settings/tokens
2. Set environment variable:
   ```bash
   export HUGGINGFACE_API_KEY="your-api-key-here"
   ```
   Or add to Django settings (`kg_quality/settings.py`):
   ```python
   HUGGINGFACE_API_KEY = "your-api-key-here"
   ```

**Models used:**
- `meta-llama/Llama-3.2-3B-Instruct` (default, high quality)
- Falls back to `google/flan-t5-large` if needed

**Cost:** FREE (generous free tier)

### Option 2: Ollama (Free, Local)

**Setup:**
1. Install Ollama: https://ollama.ai/
2. Pull a model:
   ```bash
   ollama pull llama3.2
   # or
   ollama pull mistral
   ```
3. Ensure Ollama is running (default: http://localhost:11434)

**Models recommended:**
- `llama3.2` (good balance)
- `mistral` (faster)
- `phi3` (lightweight)

**Cost:** Free (runs locally)

### Option 3: Sentence Transformers (Free, No API needed)

**Setup:**
1. Install dependencies (already in requirements.txt):
   ```bash
   pip install sentence-transformers scikit-learn numpy
   ```
2. Model downloads automatically on first use (~80MB)

**Models used:**
- `all-MiniLM-L6-v2` (lightweight, fast)

**Cost:** Free, runs locally

**Limitations:** 
- Only provides semantic similarity (no summaries)
- Requires scikit-learn and numpy

## Usage

1. Go to the Compare Frameworks page
2. Select frameworks to compare
3. Click "🤖 Enable AI Enhancement" button
4. The system will automatically detect and use the best available LLM provider

## Priority Order (FREE FIRST!)

The system tries providers in this order (prioritizing FREE options):
1. **Hugging Face** (FREE tier - if API key is configured) ⭐
2. **Ollama** (FREE - if available and running locally)
3. **Sentence Transformers** (FREE - always available if installed)
4. OpenAI (PAID - only if explicitly enabled with `USE_OPENAI=true`)
5. None (falls back to basic comparison without AI enhancements)

## Configuration

You can force a specific provider by setting in Django settings:

```python
# Force OpenAI
LLM_PROVIDER = 'openai'

# Force Ollama
LLM_PROVIDER = 'ollama'

# Force Sentence Transformers
LLM_PROVIDER = 'sentence_transformers'
```

## Troubleshooting

### OpenAI errors
- Check API key is set correctly
- Verify you have credits in your OpenAI account
- Check rate limits

### Ollama errors
- Ensure Ollama is running: `ollama serve`
- Verify model is downloaded: `ollama list`
- Check connection: `curl http://localhost:11434/api/tags`

### Sentence Transformers errors
- Install dependencies: `pip install sentence-transformers scikit-learn numpy`
- Check disk space (model is ~80MB)
- First run may take time to download model

## Performance

- **Sentence Transformers**: Fastest (~1-2 seconds), similarity only
- **Hugging Face**: Fast (~3-8 seconds), good quality
- **Ollama**: Medium speed (~5-15 seconds), best free quality
- **OpenAI**: Fastest paid option (~2-5 seconds), best quality (but costs money)

## Cost Estimation

For a comparison of 2 frameworks with 20 criteria:
- **Ollama**: FREE ✅
- **Hugging Face**: FREE ✅ (generous free tier)
- **Sentence Transformers**: FREE ✅
- OpenAI: ~$0.02-0.05 (PAID)

## Quick Start (Recommended - FREE)

**Easiest and Best Quality Setup (Hugging Face - recommended):**
```bash
# 1. Get free API key from https://huggingface.co/settings/tokens
# 2. Add to settings.py or environment variable
export HUGGINGFACE_API_KEY="your-token-here"

# That's it! Works immediately with high quality.
```

**Alternative: Sentence Transformers (works immediately, no API key needed):**
```bash
pip install sentence-transformers scikit-learn numpy
# That's it! Works immediately (but only provides similarity, no summaries).
```

**Local Setup (Ollama - if you prefer local processing):**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model (choose one)
ollama pull phi3        # Smallest (~2GB)
# or
ollama pull llama3.2    # Best quality (~2GB)

# Start Ollama (usually auto-starts)
ollama serve
```

**That's it!** The system will automatically detect and use the best available provider.
