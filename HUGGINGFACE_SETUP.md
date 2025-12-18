# Hugging Face Setup Guide

## Quick Setup (Works Without API Key!)

The system is now configured to use **Hugging Face Inference API** with a free model that works **without an API key**.

### Current Configuration

- **Model**: `microsoft/Phi-3-mini-4k-instruct` (high-quality free model)
- **Fallback**: `google/flan-t5-base` (if main model fails)
- **Works without API key**: ✅ Yes, but with limited rate limits
- **Better with API key**: ✅ Yes, for higher rate limits

## Do You Need an API Key?

### Without API Key (Current Setup)
- ✅ Works immediately
- ✅ Completely free
- ⚠️ Limited rate limits (may be slower with many requests)
- ⚠️ Some models may not be available

### With Free API Key (Recommended)
- ✅ Higher rate limits
- ✅ Access to more models
- ✅ Better reliability
- ✅ Still completely free!

## How to Get a Free Hugging Face API Key

1. **Create a free account**:
   - Go to: https://huggingface.co/join
   - Sign up with email or GitHub

2. **Get your API token**:
   - Go to: https://huggingface.co/settings/tokens
   - Click "New token"
   - Name it (e.g., "kg-quality-app")
   - Select "Read" permissions (sufficient for Inference API)
   - Click "Generate token"
   - **Copy the token** (you'll only see it once!)

3. **Add the token to your Django app**:

   **Option A: Environment Variable (Recommended)**
   ```bash
   export HUGGINGFACE_API_KEY="your-token-here"
   ```
   
   Or add to your shell profile (`~/.bashrc` or `~/.zshrc`):
   ```bash
   echo 'export HUGGINGFACE_API_KEY="your-token-here"' >> ~/.bashrc
   source ~/.bashrc
   ```

   **Option B: Django Settings**
   Add to `kg_quality/settings.py`:
   ```python
   HUGGINGFACE_API_KEY = "your-token-here"
   ```

4. **Restart the server**:
   ```bash
   # Kill existing gunicorn processes
   pkill -f "gunicorn.*kg_quality"
   
   # Restart
   cd /root/seminer
   source venv/bin/activate
   nohup gunicorn --bind 0.0.0.0:8002 --workers 3 --timeout 120 \
       --access-logfile /root/seminer/logs/access.log \
       --error-logfile /root/seminer/logs/error.log \
       kg_quality.wsgi:application > /dev/null 2>&1 &
   ```

## Current Model Information

### Primary Model: `microsoft/Phi-3-mini-4k-instruct`
- **Quality**: Excellent for text generation
- **Size**: Small and fast
- **Free Tier**: ✅ Yes
- **API Key Required**: ❌ No (but recommended)

### Fallback Model: `google/flan-t5-base`
- **Quality**: Good for structured tasks
- **Size**: Very small and fast
- **Free Tier**: ✅ Yes
- **API Key Required**: ❌ No

## Testing

After setup, test the AI enhancement:
1. Go to Compare Frameworks page
2. Select 2+ frameworks
3. Click "🤖 Enable AI Enhancement"
4. Check the logs if there are issues:
   ```bash
   tail -f /root/seminer/logs/django.log
   ```

## Troubleshooting

### "Hugging Face not available" error
- Check if `huggingface-hub` is installed: `pip install huggingface-hub`
- Check logs: `tail -50 /root/seminer/logs/django.log`

### Rate limit errors
- Get a free API key (see above)
- The free tier is very generous, but without a key, limits are stricter

### Model not found errors
- The system will automatically fallback to `google/flan-t5-base`
- Check logs to see which model is being used

## Priority Order

The system tries providers in this order:
1. **Ollama** (if running locally) - Best free quality
2. **Hugging Face** (current setup) - Good quality, works immediately
3. **Sentence Transformers** - Fast similarity only
4. **OpenAI** - Paid option (only if explicitly enabled)

## Cost

- **Hugging Face Inference API**: **FREE** ✅
- **Free tier limits**: Very generous (thousands of requests per month)
- **No credit card required**
