# Models Used in KG Quality Framework

## Overview
This project uses multiple AI/ML models for enhancing knowledge graph quality framework comparisons. All models are **FREE** to use.

## Primary Models

### 1. Hugging Face Inference API
**Primary Model**: `meta-llama/Llama-3.2-3B-Instruct`
- **Purpose**: Text generation, summaries, and AI-powered insights
- **Usage**: LLM-enhanced criteria comparison, semantic similarity detection, intelligent summaries
- **Fallback Model**: `google/flan-t5-large` (used if primary model fails)
- **Cost**: FREE (generous free tier)
- **API Key**: Optional (works without key, but better rate limits with free key)

### 2. Sentence Transformers
**Model**: `all-MiniLM-L6-v2`
- **Purpose**: Semantic similarity calculations and embeddings
- **Usage**: Fast similarity detection between criteria (runs locally)
- **Cost**: FREE (runs locally, no API needed)
- **Size**: ~80MB (downloads automatically on first use)

## Model Priority Order

The system tries providers in this order:
1. **Hugging Face** (primary) - `meta-llama/Llama-3.2-3B-Instruct`
2. **Ollama** (if running locally) - Models like `phi3`, `mistral`, `llama3.2`
3. **Sentence Transformers** - `all-MiniLM-L6-v2` (similarity only)
4. **OpenAI** (paid, if explicitly enabled) - `gpt-4o-mini`

## Features Enabled by Models

- **Semantic Similarity Detection**: Finds criteria that are conceptually similar even if named differently
- **Intelligent Summaries**: Generates concise comparisons of how different frameworks define the same criterion
- **Related Criteria Grouping**: Groups criteria that belong to the same conceptual category
- **Enhanced Descriptions**: AI-generated framework-specific descriptions for criteria

## Configuration

Models are automatically detected and configured. No manual setup required, but:
- Hugging Face API key recommended for better rate limits (get free key at https://huggingface.co/settings/tokens)
- Sentence Transformers requires: `sentence-transformers`, `scikit-learn`, `numpy` (already in requirements.txt)

## Files

- Model implementation: `frameworks/llm_comparison.py`
- Setup guide: `HUGGINGFACE_SETUP.md`, `LLM_SETUP.md`
