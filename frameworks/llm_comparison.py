"""
LLM-enhanced criteria comparison for better semantic matching and insights.
Supports multiple LLM providers: OpenAI, Ollama, or sentence transformers.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
try:
    from django.conf import settings
except ImportError:
    # For testing outside Django
    settings = None

logger = logging.getLogger(__name__)

# Try to import LLM libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Hugging Face Inference API (free tier)
try:
    from huggingface_hub import InferenceClient
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class LLMComparisonEngine:
    """Engine for LLM-enhanced criteria comparison"""
    
    def __init__(self):
        self.provider = self._detect_provider()
        self.model = None
        self.ollama_model = None
        self.hf_model = None
        
        if self.provider == 'openai':
            self._init_openai()
        elif self.provider == 'ollama':
            self._init_ollama()
        elif self.provider == 'huggingface':
            self._init_huggingface()
        elif self.provider == 'sentence_transformers':
            self._init_sentence_transformers()
    
    def _detect_provider(self) -> str:
        """Detect which LLM provider to use - PRIORITIZES FREE OPTIONS"""
        logger.info("=== Detecting LLM Provider ===")
        
        # Check if provider is forced in settings
        if settings:
            forced_provider = getattr(settings, 'LLM_PROVIDER', None)
            if forced_provider:
                logger.info(f"Provider forced in settings: {forced_provider}")
                return forced_provider
        
        # PRIORITY 1: Hugging Face Inference API (FREE tier available)
        # Works without API key, but better rate limits with free key
        # Prioritize Hugging Face since user provided API key
        if HUGGINGFACE_AVAILABLE:
            logger.info("Hugging Face is available, using it as primary provider")
            return 'huggingface'
        
        # PRIORITY 2: Ollama (FREE, Local, Best quality for free)
        if OLLAMA_AVAILABLE:
            try:
                logger.info("Checking Ollama availability...")
                # Test if Ollama is actually running
                if REQUESTS_AVAILABLE:
                    try:
                        requests.get('http://localhost:11434/api/tags', timeout=2)
                        logger.info("Ollama is running, but Hugging Face is preferred")
                        # Don't return here, continue to check Hugging Face first
                    except:
                        logger.debug("Ollama not reachable via HTTP")
                        pass
                # Try with ollama client directly
                try:
                    ollama.list()
                    logger.info("Ollama is available, but Hugging Face is preferred")
                    # Don't return here, continue to check Hugging Face first
                except:
                    logger.debug("Ollama client not working")
                    pass
            except Exception as e:
                logger.debug(f"Ollama check failed: {e}")
                pass
        
        # PRIORITY 3: Sentence Transformers (FREE, Always available if installed)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.info("Sentence Transformers available as fallback")
            return 'sentence_transformers'
        
        # PRIORITY 4: OpenAI (PAID - only if explicitly configured and free options not available)
        openai_key = os.getenv('OPENAI_API_KEY') or (getattr(settings, 'OPENAI_API_KEY', None) if settings else None)
        if OPENAI_AVAILABLE and openai_key:
            # Only use OpenAI if user explicitly wants it (not default)
            use_openai = os.getenv('USE_OPENAI', 'false').lower() == 'true'
            if use_openai:
                logger.info("OpenAI explicitly enabled")
                return 'openai'
        
        logger.warning("No LLM provider available")
        return 'none'
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        if OPENAI_AVAILABLE:
            try:
                api_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
                if api_key:
                    openai.api_key = api_key
                    self.client = openai.OpenAI(api_key=api_key)
                else:
                    logger.warning("OpenAI API key not found")
                    self.provider = 'none'
                    self.client = None
            except Exception as e:
                logger.warning(f"OpenAI initialization failed: {e}")
                self.provider = 'none'
                self.client = None
    
    def _init_ollama(self):
        """Initialize Ollama client"""
        if OLLAMA_AVAILABLE:
            try:
                # Test connection
                models_response = ollama.list()
                self.client = ollama
                
                # Get available models - handle different response formats
                available_models = []
                if hasattr(models_response, 'models'):
                    # Response object with .models attribute
                    for model in models_response.models:
                        model_name = getattr(model, 'model', None) or getattr(model, 'name', '')
                        if model_name:
                            available_models.append(model_name)
                elif isinstance(models_response, dict) and 'models' in models_response:
                    available_models = [m.get('model') or m.get('name', '') for m in models_response['models']]
                elif isinstance(models_response, list):
                    available_models = [m.get('model') or m.get('name', '') for m in models_response]
                
                # Prefer smaller, faster models in order
                preferred_models = ['phi3', 'mistral', 'llama3.2', 'llama3.1', 'llama3']
                self.ollama_model = 'phi3'  # Default to phi3 (smallest)
                
                # Find the best available model
                for preferred in preferred_models:
                    for available in available_models:
                        if available and preferred in available.lower():
                            # Extract base model name (remove :latest tag)
                            self.ollama_model = preferred
                            logger.info(f"Using Ollama model: {preferred}")
                            return
                
                # If no preferred model found, use first available
                if available_models:
                    first_model = available_models[0]
                    # Remove :latest or other tags
                    self.ollama_model = first_model.split(':')[0] if ':' in first_model else first_model
                    logger.info(f"Using available Ollama model: {self.ollama_model}")
                else:
                    logger.warning("No Ollama models found. Pull a model with: ollama pull phi3")
                    
            except Exception as e:
                logger.warning(f"Ollama not available: {e}")
                self.provider = 'none'
                self.client = None
                self.ollama_model = None
    
    def _init_huggingface(self):
        """Initialize Hugging Face client"""
        if HUGGINGFACE_AVAILABLE:
            try:
                logger.info("Initializing Hugging Face client...")
                hf_token = os.getenv('HUGGINGFACE_API_KEY') or (getattr(settings, 'HUGGINGFACE_API_KEY', None) if settings else None)
                
                if hf_token:
                    logger.info("Hugging Face API key found")
                else:
                    logger.warning("No Hugging Face API key found, using without key (limited rate)")
                
                # Use a free model that works well for text generation
                # This model works without API key, but better rate limits with free key
                # Options (in order of preference):
                # 1. meta-llama/Llama-3.2-3B-Instruct - Good quality, widely available
                # 2. google/flan-t5-large - Reliable, works well
                # 3. microsoft/Phi-3-mini-4k-instruct - Good but may have availability issues
                # 4. HuggingFaceH4/zephyr-7b-beta - Good quality
                
                # Try Llama 3.2 first as it's more reliable
                self.hf_model = 'meta-llama/Llama-3.2-3B-Instruct'
                logger.info(f"Using Hugging Face model: {self.hf_model}")
                
                # Initialize client (works without token, but better with free token)
                logger.info("Creating InferenceClient...")
                self.client = InferenceClient(token=hf_token) if hf_token else InferenceClient()
                
                if not hasattr(self, 'client') or self.client is None:
                    raise ValueError("Hugging Face client not initialized")
                
                logger.info(f"Hugging Face initialized successfully with model: {self.hf_model}" + (" (with API key)" if hf_token else " (without API key - limited rate)"))
            except Exception as e:
                logger.error(f"Hugging Face initialization failed: {e}", exc_info=True)
                self.provider = 'none'
                self.client = None
                self.hf_model = None
    
    def _init_sentence_transformers(self):
        """Initialize sentence transformers model"""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Use a lightweight model for semantic similarity
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence transformers model loaded")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformers: {e}")
                self.provider = 'none'
                self.model = None
    
    def find_semantic_similarities(self, criteria_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Find criteria that are semantically similar even if named differently.
        Returns a dict mapping criterion names to lists of similar criterion names.
        """
        if self.provider == 'none':
            return {}
        
        similarities = {}
        
        try:
            if self.provider == 'sentence_transformers':
                return self._find_similarities_embeddings(criteria_list)
            elif self.provider in ['openai', 'ollama', 'huggingface']:
                return self._find_similarities_llm(criteria_list)
        except Exception as e:
            logger.error(f"Error finding semantic similarities: {e}")
            return {}
        
        return similarities
    
    def _find_similarities_embeddings(self, criteria_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Find similarities using sentence embeddings"""
        if not self.model:
            return {}
        
        try:
            # Create embeddings for all criteria names and descriptions
            texts = []
            criterion_map = {}
            
            for criterion in criteria_list:
                name = criterion.get('name', '')
                desc = criterion.get('description', '') or ''
                # Combine name and description for better semantic understanding
                text = f"{name}. {desc}" if desc else name
                texts.append(text)
                criterion_map[len(texts) - 1] = name
            
            if not texts:
                return {}
            
            # Generate embeddings
            embeddings = self.model.encode(texts)
            
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(embeddings)
        except Exception as e:
            logger.error(f"Error in embeddings calculation: {e}")
            return {}
        
        # Find similar criteria (threshold: 0.7)
        similarities = {}
        threshold = 0.7
        
        for i, criterion in enumerate(criteria_list):
            name = criterion.get('name', '')
            similar = []
            
            for j, other_criterion in enumerate(criteria_list):
                if i != j:
                    similarity_score = similarity_matrix[i][j]
                    if similarity_score >= threshold:
                        similar.append({
                            'name': other_criterion.get('name', ''),
                            'similarity': float(similarity_score)
                        })
            
            if similar:
                # Sort by similarity score
                similar.sort(key=lambda x: x['similarity'], reverse=True)
                similarities[name] = [s['name'] for s in similar[:3]]  # Top 3 most similar
        
        return similarities
    
    def _find_similarities_llm(self, criteria_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Find similarities using LLM"""
        if len(criteria_list) < 2:
            return {}
        
        # Prepare criteria data for LLM
        criteria_text = "\n".join([
            f"- {c.get('name', '')}: {c.get('description', '')[:100]}"
            for c in criteria_list[:20]  # Limit to avoid token limits
        ])
        
        prompt = f"""Analyze these knowledge graph quality criteria and identify which ones are semantically similar or conceptually related, even if they have different names.

Criteria:
{criteria_text}

Return a JSON object where keys are criterion names and values are lists of similar criterion names. Only include criteria that are genuinely similar (same concept, different wording). Format:
{{"Criterion Name": ["Similar Criterion 1", "Similar Criterion 2"]}}

Return only valid JSON, no other text."""

        try:
            if self.provider == 'openai':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("OpenAI client not initialized")
                    return {}
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",  # Using mini for cost efficiency
                        messages=[
                            {"role": "system", "content": "You are an expert in knowledge graph quality frameworks. Analyze criteria and identify semantic similarities."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=1000
                    )
                    result_text = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.error(f"OpenAI API error: {e}")
                    return {}
            elif self.provider == 'ollama':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("Ollama client not initialized")
                    return {}
                model = getattr(self, 'ollama_model', 'llama3.2')
                if not model:
                    logger.error("Ollama model not set")
                    return {}
                try:
                    response = self.client.generate(
                        model=model,
                        prompt=prompt,
                        options={'temperature': 0.3}
                    )
                    # Handle different response formats
                    if isinstance(response, dict):
                        result_text = response.get('response', '').strip()
                    elif hasattr(response, 'response'):
                        result_text = response.response.strip()
                    else:
                        result_text = str(response).strip()
                except Exception as e:
                    logger.error(f"Ollama API error: {e}")
                    return {}
            elif self.provider == 'huggingface':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("Hugging Face client not initialized")
                    return {}
                model = getattr(self, 'hf_model', 'meta-llama/Llama-3.2-3B-Instruct')
                logger.info(f"Calling Hugging Face API with model: {model}")
                logger.debug(f"Prompt length: {len(prompt)} characters")
                try:
                    import time
                    api_start = time.time()
                    # Try chat completion API first (more reliable)
                    try:
                        logger.debug("Trying chat completion API...")
                        messages = [{"role": "user", "content": prompt}]
                        response = self.client.chat_completion(
                            model=model,
                            messages=messages,
                            max_tokens=500,
                            temperature=0.3
                        )
                        # Extract text from chat completion response
                        if hasattr(response, 'choices') and len(response.choices) > 0:
                            result_text = response.choices[0].message.content.strip()
                        elif isinstance(response, dict) and 'choices' in response:
                            result_text = response['choices'][0]['message']['content'].strip()
                        else:
                            result_text = str(response).strip()
                        api_time = time.time() - api_start
                        logger.info(f"Hugging Face chat API call completed in {api_time:.2f}s")
                    except Exception as chat_error:
                        logger.debug(f"Chat API failed: {chat_error}, trying text generation...")
                        # Fallback to text generation
                        try:
                            response = self.client.text_generation(
                                prompt,
                                model=model,
                                max_new_tokens=500,
                                temperature=0.3,
                                do_sample=True
                            )
                            result_text = response.strip() if isinstance(response, str) else str(response).strip()
                            api_time = time.time() - api_start
                            logger.info(f"Hugging Face text generation completed in {api_time:.2f}s")
                        except Exception as text_error:
                            logger.warning(f"Text generation also failed: {text_error}")
                            raise text_error
                except Exception as e:
                    logger.error(f"Hugging Face API error with {model}: {e}", exc_info=True)
                    # Try fallback model if main model fails
                    try:
                        logger.info("Trying fallback model: google/flan-t5-large")
                        response = self.client.text_generation(
                            prompt,
                            model='google/flan-t5-large',
                            max_new_tokens=500,
                            temperature=0.3
                        )
                        result_text = response.strip() if isinstance(response, str) else str(response).strip()
                        logger.info("Fallback model succeeded")
                    except Exception as e2:
                        logger.error(f"Hugging Face fallback also failed: {e2}", exc_info=True)
                        return {}
            else:
                return {}
            
            # Parse JSON response
            # Try to extract JSON from response (in case LLM adds extra text)
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
            similarities = json.loads(result_text)
            return similarities
            
        except Exception as e:
            logger.error(f"Error in LLM similarity detection: {e}")
            return {}
    
    def generate_comparison_summary(self, criterion_name: str, framework_data: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generate an intelligent summary comparing how different frameworks define a criterion.
        """
        if self.provider == 'none':
            return None
        
        # Collect all definitions and descriptions
        definitions = []
        for i, fw_data in enumerate(framework_data):
            if fw_data.get('has_criterion'):
                desc = fw_data.get('description', '')
                defs = fw_data.get('definitions', [])
                if desc or defs:
                    definitions.append({
                        'framework_index': i,
                        'description': desc,
                        'definitions': defs[:2]  # Limit to first 2 definitions
                    })
        
        if len(definitions) < 2:
            return None  # Need at least 2 frameworks to compare
        
        # Build prompt
        definitions_text = "\n\n".join([
            f"Framework {i+1}:\nDescription: {d['description']}\nDefinitions: {'; '.join(d['definitions'])}"
            for i, d in enumerate(definitions)
        ])
        
        prompt = f"""Compare how different knowledge graph quality frameworks define the criterion "{criterion_name}".

Definitions:
{definitions_text}

Provide a concise 2-3 sentence summary highlighting:
1. Key similarities in how frameworks define this criterion
2. Notable differences or unique perspectives
3. Any important nuances

Be specific and factual. Return only the summary text, no markdown formatting."""

        try:
            if self.provider == 'openai':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("OpenAI client not initialized")
                    return None
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert in knowledge graph quality frameworks. Provide concise, factual comparisons."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.4,
                        max_tokens=200
                    )
                    summary = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.error(f"OpenAI API error: {e}")
                    return None
            elif self.provider == 'ollama':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("Ollama client not initialized")
                    return None
                model = getattr(self, 'ollama_model', 'llama3.2')
                if not model:
                    logger.error("Ollama model not set")
                    return None
                try:
                    response = self.client.generate(
                        model=model,
                        prompt=prompt,
                        options={'temperature': 0.4, 'num_predict': 200}
                    )
                    # Handle different response formats
                    if isinstance(response, dict):
                        summary = response.get('response', '').strip()
                    elif hasattr(response, 'response'):
                        summary = response.response.strip()
                    else:
                        summary = str(response).strip()
                except Exception as e:
                    logger.error(f"Ollama API error: {e}")
                    return None
            elif self.provider == 'huggingface':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("Hugging Face client not initialized")
                    return None
                model = getattr(self, 'hf_model', 'meta-llama/Llama-3.2-3B-Instruct')
                try:
                    # Hugging Face InferenceClient API: model is passed to text_generation
                    # Try with instruction format first (for Phi-3 and similar models)
                    try:
                        formatted_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
                        response = self.client.text_generation(
                            formatted_prompt,
                            model=model,
                            max_new_tokens=200,
                            temperature=0.4,
                            do_sample=True
                        )
                        summary = response.strip() if isinstance(response, str) else str(response).strip()
                    except Exception as format_error:
                        # Fallback to simple prompt format
                        logger.debug(f"Instruction format failed, trying simple format: {format_error}")
                        response = self.client.text_generation(
                            prompt,
                            model=model,
                            max_new_tokens=200,
                            temperature=0.4,
                            do_sample=True
                        )
                        summary = response.strip() if isinstance(response, str) else str(response).strip()
                except Exception as e:
                    logger.error(f"Hugging Face API error with {model}: {e}")
                    # Try fallback model if main model fails
                    try:
                        logger.info("Trying fallback model: google/flan-t5-large")
                        response = self.client.text_generation(
                            prompt,
                            model='google/flan-t5-large',
                            max_new_tokens=200,
                            temperature=0.4
                        )
                        summary = response.strip() if isinstance(response, str) else str(response).strip()
                    except Exception as e2:
                        logger.error(f"Hugging Face fallback also failed: {e2}")
                        return None
            else:
                return None
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating comparison summary: {e}")
            return None
    
    def generate_criterion_insights(self, criterion_name: str, framework_data: List[Dict[str, Any]], 
                                    selected_frameworks: List) -> Optional[str]:
        """
        Generate detailed insights about how different frameworks handle a criterion.
        """
        if self.provider == 'none':
            return None
        
        # Collect all definitions and descriptions
        framework_info = []
        for i, fw_data in enumerate(framework_data):
            if fw_data.get('has_criterion'):
                framework_name = selected_frameworks[i].name if i < len(selected_frameworks) else f"Framework {i+1}"
                desc = fw_data.get('description', '')
                defs = fw_data.get('definitions', [])
                category = fw_data.get('category', '')
                
                info_text = f"{framework_name}:"
                if category:
                    info_text += f" Category: {category}. "
                if desc:
                    info_text += f" Description: {desc}. "
                if defs:
                    info_text += f" Definitions: {'; '.join(defs[:2])}"
                
                framework_info.append(info_text)
        
        if len(framework_info) < 2:
            return None
        
        prompt = f"""Analyze how different knowledge graph quality frameworks approach the criterion "{criterion_name}".

Framework approaches:
{chr(10).join(f'- {info}' for info in framework_info)}

Provide 2-3 sentences highlighting:
1. Key differences in how frameworks implement or measure this criterion
2. Which framework has the most comprehensive approach
3. Any practical implications or recommendations

Be concise and actionable. Return only the insight text, no markdown."""
        
        try:
            if self.provider == 'huggingface':
                if not hasattr(self, 'client') or self.client is None:
                    return None
                model = getattr(self, 'hf_model', 'meta-llama/Llama-3.2-3B-Instruct')
                try:
                    formatted_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
                    response = self.client.text_generation(
                        formatted_prompt,
                        model=model,
                        max_new_tokens=150,
                        temperature=0.5,
                        do_sample=True
                    )
                    return response.strip() if isinstance(response, str) else str(response).strip()
                except:
                    response = self.client.text_generation(
                        prompt,
                        model=model,
                        max_new_tokens=150,
                        temperature=0.5,
                        do_sample=True
                    )
                    return response.strip() if isinstance(response, str) else str(response).strip()
        except Exception as e:
            logger.debug(f"Error generating criterion insights: {e}")
            return None
        
        return None
    
    def generate_enhanced_description(self, criterion_name: str, fw_data: Dict[str, Any], 
                                      framework, all_framework_data: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generate an LLM-enhanced description for a criterion in a specific framework.
        This provides a more comprehensive, AI-generated description that is framework-specific.
        """
        if self.provider == 'none':
            logger.debug(f"LLM provider is 'none', skipping enhanced description for {criterion_name} in {framework.name}")
            return None
        
        desc = fw_data.get('description', '')
        defs = fw_data.get('definitions', [])
        category = fw_data.get('category', '')
        
        # Build framework-specific context
        framework_context = f"Framework: {framework.name}"
        if framework.year:
            framework_context += f" ({framework.year})"
        if category:
            framework_context += f"\nCategory: {category}"
        if desc:
            framework_context += f"\nOriginal description: {desc}"
        if defs:
            framework_context += f"\nDefinitions in this framework: {'; '.join(defs[:2])}"
        
        # Build prompt that emphasizes framework-specificity
        prompt = f"""You are analyzing knowledge graph quality frameworks. Provide a clear, comprehensive 2-3 sentence description of the criterion "{criterion_name}" SPECIFICALLY as it is used in the framework "{framework.name}".

{framework_context}

IMPORTANT: Your description must be specific to how {framework.name} defines and uses this criterion. Do not provide a generic description. Focus on:
1. How THIS SPECIFIC FRAMEWORK ({framework.name}) defines or measures this criterion
2. What makes this criterion's interpretation unique or notable in {framework.name}
3. The practical significance of this criterion within {framework.name}'s approach

Return only the description text, no markdown, no labels, no quotes."""
        
        try:
            if self.provider == 'openai':
                if not hasattr(self, 'client') or self.client is None:
                    logger.warning("OpenAI client not initialized")
                    return None
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": f"You are an expert in knowledge graph quality frameworks. Provide framework-specific descriptions for criteria as used in {framework.name}."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.4,
                        max_tokens=150
                    )
                    result = response.choices[0].message.content.strip()
                    logger.debug(f"Generated enhanced description for {criterion_name} in {framework.name} (OpenAI)")
                    return result
                except Exception as e:
                    logger.error(f"OpenAI API error generating enhanced description: {e}")
                    return None
            elif self.provider == 'ollama':
                if not hasattr(self, 'client') or self.client is None:
                    logger.warning("Ollama client not initialized")
                    return None
                model = getattr(self, 'ollama_model', 'llama3.2')
                if not model:
                    logger.warning("Ollama model not set")
                    return None
                try:
                    response = self.client.generate(
                        model=model,
                        prompt=prompt,
                        options={'temperature': 0.4, 'num_predict': 150}
                    )
                    if isinstance(response, dict):
                        result = response.get('response', '').strip()
                    elif hasattr(response, 'response'):
                        result = response.response.strip()
                    else:
                        result = str(response).strip()
                    logger.debug(f"Generated enhanced description for {criterion_name} in {framework.name} (Ollama)")
                    return result
                except Exception as e:
                    logger.error(f"Ollama API error generating enhanced description: {e}")
                    return None
            elif self.provider == 'huggingface':
                if not hasattr(self, 'client') or self.client is None:
                    logger.warning("Hugging Face client not initialized")
                    return None
                model = getattr(self, 'hf_model', 'meta-llama/Llama-3.2-3B-Instruct')
                try:
                    # Use chat completion API for conversational models
                    messages = [{"role": "user", "content": prompt}]
                    response = self.client.chat_completion(
                        model=model,
                        messages=messages,
                        max_tokens=150,
                        temperature=0.4
                    )
                    # Extract text from chat completion response
                    if hasattr(response, 'choices') and len(response.choices) > 0:
                        result = response.choices[0].message.content.strip()
                    elif isinstance(response, dict) and 'choices' in response:
                        result = response['choices'][0]['message']['content'].strip()
                    else:
                        result = str(response).strip()
                    logger.debug(f"Generated enhanced description for {criterion_name} in {framework.name} (HuggingFace)")
                    return result
                except Exception as chat_error:
                    logger.debug(f"Chat completion failed: {chat_error}, trying text generation...")
                    try:
                        # Fallback to text generation with a simpler model
                        response = self.client.text_generation(
                            prompt,
                            model='google/flan-t5-large',
                            max_new_tokens=150,
                            temperature=0.4,
                            do_sample=True
                        )
                        result = response.strip() if isinstance(response, str) else str(response).strip()
                        logger.debug(f"Generated enhanced description for {criterion_name} in {framework.name} (HuggingFace, fallback)")
                        return result
                    except Exception as simple_error:
                        logger.warning(f"All methods failed for {criterion_name} in {framework.name}: {simple_error}")
                        return None
            else:
                logger.warning(f"Unsupported provider for enhanced description: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"Error generating enhanced description for {criterion_name} in {framework.name}: {e}", exc_info=True)
            return None
        
        return None
    
    def generate_unique_criterion_insight(self, criterion_name: str, framework_data: List[Dict[str, Any]], 
                                         selected_frameworks: List) -> Optional[str]:
        """
        Generate insight for a criterion that appears in only one framework.
        """
        if self.provider == 'none':
            return None
        
        # Find which framework has this criterion
        framework_idx = None
        for i, fw_data in enumerate(framework_data):
            if fw_data.get('has_criterion'):
                framework_idx = i
                break
        
        if framework_idx is None or framework_idx >= len(selected_frameworks):
            return None
        
        framework = selected_frameworks[framework_idx]
        fw_data = framework_data[framework_idx]
        
        desc = fw_data.get('description', '')
        defs = fw_data.get('definitions', [])
        category = fw_data.get('category', '')
        
        other_frameworks = [fw.name for i, fw in enumerate(selected_frameworks) if i != framework_idx]
        
        prompt = f"""The criterion "{criterion_name}" appears only in the framework "{framework.name}" but not in: {', '.join(other_frameworks)}.

Details from {framework.name}:
- Category: {category or 'Not specified'}
- Description: {desc or 'Not provided'}
- Definitions: {'; '.join(defs[:2]) if defs else 'Not provided'}

Provide a brief 1-2 sentence insight about:
1. Why this criterion might be unique to this framework
2. Its potential importance or relevance

Be concise. Return only the insight text."""
        
        try:
            if self.provider == 'huggingface':
                if not hasattr(self, 'client') or self.client is None:
                    return None
                model = getattr(self, 'hf_model', 'meta-llama/Llama-3.2-3B-Instruct')
                try:
                    formatted_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
                    response = self.client.text_generation(
                        formatted_prompt,
                        model=model,
                        max_new_tokens=100,
                        temperature=0.5,
                        do_sample=True
                    )
                    return response.strip() if isinstance(response, str) else str(response).strip()
                except:
                    response = self.client.text_generation(
                        prompt,
                        model=model,
                        max_new_tokens=100,
                        temperature=0.5,
                        do_sample=True
                    )
                    return response.strip() if isinstance(response, str) else str(response).strip()
        except Exception as e:
            logger.debug(f"Error generating unique criterion insight: {e}")
            return None
        
        return None
    
    def generate_overall_insights(self, comparison_data: List[Dict[str, Any]], 
                                  selected_frameworks: List,
                                  semantic_similarities: Dict,
                                  summaries: Dict) -> Optional[str]:
        """
        Generate overall insights about the comparison between frameworks.
        """
        if self.provider == 'none':
            return None
        
        framework_names = [fw.name for fw in selected_frameworks]
        total_criteria = len(comparison_data)
        common_criteria = sum(1 for c in comparison_data 
                            if all(fw.get('has_criterion') for fw in c.get('framework_data', [])))
        unique_criteria = sum(1 for c in comparison_data 
                            if sum(1 for fw in c.get('framework_data', []) if fw.get('has_criterion')) == 1)
        similar_pairs = len(semantic_similarities)
        
        prompt = f"""Analyze this comparison of {len(selected_frameworks)} knowledge graph quality frameworks: {', '.join(framework_names)}.

Statistics:
- Total unique criteria: {total_criteria}
- Criteria in all frameworks: {common_criteria}
- Criteria unique to one framework: {unique_criteria}
- Semantically similar criteria pairs: {similar_pairs}

Provide 3-4 sentences with overall insights:
1. Key strengths of each framework
2. Major differences in approach
3. Recommendations for choosing or combining frameworks
4. Notable gaps or overlaps

Be insightful and practical. Return only the insight text, no markdown."""
        
        try:
            if self.provider == 'huggingface':
                if not hasattr(self, 'client') or self.client is None:
                    return None
                model = getattr(self, 'hf_model', 'meta-llama/Llama-3.2-3B-Instruct')
                try:
                    formatted_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
                    response = self.client.text_generation(
                        formatted_prompt,
                        model=model,
                        max_new_tokens=250,
                        temperature=0.5,
                        do_sample=True
                    )
                    return response.strip() if isinstance(response, str) else str(response).strip()
                except:
                    response = self.client.text_generation(
                        prompt,
                        model=model,
                        max_new_tokens=250,
                        temperature=0.5,
                        do_sample=True
                    )
                    return response.strip() if isinstance(response, str) else str(response).strip()
        except Exception as e:
            logger.debug(f"Error generating overall insights: {e}")
            return None
        
        return None
    
    def group_related_criteria(self, criteria_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Group criteria that are conceptually related or belong to the same category.
        Returns a dict mapping group names to lists of criterion names.
        """
        if self.provider == 'none' or len(criteria_list) < 2:
            return {}
        
        # Use embeddings to cluster related criteria
        if self.provider == 'sentence_transformers' and self.model:
            return self._group_criteria_embeddings(criteria_list)
        elif self.provider in ['openai', 'ollama', 'huggingface']:
            return self._group_criteria_llm(criteria_list)
        
        return {}
    
    def _group_criteria_embeddings(self, criteria_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group criteria using embeddings and clustering"""
        from sklearn.cluster import DBSCAN
        
        if not self.model:
            return {}
        
        try:
            # Create embeddings
            texts = [f"{c.get('name', '')}. {c.get('description', '')[:100]}" for c in criteria_list]
            if not texts:
                return {}
            
            embeddings = self.model.encode(texts)
            
            # Cluster using DBSCAN
            clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine')
            labels = clustering.fit_predict(embeddings)
            
            # Group by cluster
            groups = {}
            for i, label in enumerate(labels):
                if label >= 0:  # Ignore noise points (label -1)
                    group_name = f"Group {label + 1}"
                    if group_name not in groups:
                        groups[group_name] = []
                    groups[group_name].append(criteria_list[i].get('name', ''))
            
            return groups
        except Exception as e:
            logger.error(f"Error in clustering criteria: {e}")
            return {}
    
    def _group_criteria_llm(self, criteria_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group criteria using LLM"""
        criteria_text = "\n".join([
            f"- {c.get('name', '')}: {c.get('description', '')[:80]}"
            for c in criteria_list[:15]
        ])
        
        prompt = f"""Group these knowledge graph quality criteria into related categories based on their conceptual similarity.

Criteria:
{criteria_text}

Return a JSON object with category names as keys and lists of criterion names as values. Use meaningful category names like "Completeness-related", "Accuracy-related", etc.

Format: {{"Category Name": ["Criterion 1", "Criterion 2"]}}

Return only valid JSON."""

        try:
            if self.provider == 'openai':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("OpenAI client not initialized")
                    return {}
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert in knowledge graph quality frameworks. Group related criteria."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    result_text = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.error(f"OpenAI API error: {e}")
                    return {}
            elif self.provider == 'ollama':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("Ollama client not initialized")
                    return {}
                model = getattr(self, 'ollama_model', 'llama3.2')
                if not model:
                    logger.error("Ollama model not set")
                    return {}
                try:
                    response = self.client.generate(
                        model=model,
                        prompt=prompt,
                        options={'temperature': 0.3}
                    )
                    # Handle different response formats
                    if isinstance(response, dict):
                        result_text = response.get('response', '').strip()
                    elif hasattr(response, 'response'):
                        result_text = response.response.strip()
                    else:
                        result_text = str(response).strip()
                except Exception as e:
                    logger.error(f"Ollama API error: {e}")
                    return {}
            elif self.provider == 'huggingface':
                if not hasattr(self, 'client') or self.client is None:
                    logger.error("Hugging Face client not initialized")
                    return {}
                model = getattr(self, 'hf_model', 'meta-llama/Llama-3.2-3B-Instruct')
                try:
                    # Hugging Face InferenceClient API: model is passed to text_generation
                    # Try with instruction format first (for Phi-3 and similar models)
                    try:
                        formatted_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
                        response = self.client.text_generation(
                            formatted_prompt,
                            model=model,
                            max_new_tokens=800,
                            temperature=0.3,
                            do_sample=True
                        )
                        result_text = response.strip() if isinstance(response, str) else str(response).strip()
                    except Exception as format_error:
                        # Fallback to simple prompt format
                        logger.debug(f"Instruction format failed, trying simple format: {format_error}")
                        response = self.client.text_generation(
                            prompt,
                            model=model,
                            max_new_tokens=800,
                            temperature=0.3,
                            do_sample=True
                        )
                        result_text = response.strip() if isinstance(response, str) else str(response).strip()
                except Exception as e:
                    logger.error(f"Hugging Face API error with {model}: {e}")
                    # Try fallback model if main model fails
                    try:
                        logger.info("Trying fallback model: google/flan-t5-large")
                        response = self.client.text_generation(
                            prompt,
                            model='google/flan-t5-large',
                            max_new_tokens=800,
                            temperature=0.3
                        )
                        result_text = response.strip() if isinstance(response, str) else str(response).strip()
                    except Exception as e2:
                        logger.error(f"Hugging Face fallback also failed: {e2}")
                        return {}
            else:
                return {}
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
            groups = json.loads(result_text)
            return groups
            
        except Exception as e:
            logger.error(f"Error grouping criteria: {e}")
            return {}


def enhance_comparison_with_llm(comparison_data: List[Dict[str, Any]], 
                                selected_frameworks: List) -> Dict[str, Any]:
    """
    Enhance comparison data with LLM-generated insights.
    Returns enhanced comparison data with semantic similarities, summaries, and groupings.
    """
    import time
    start_time = time.time()
    logger.info(f"=== LLM Enhancement Started ===")
    logger.info(f"Number of criteria to process: {len(comparison_data)}")
    logger.info(f"Number of frameworks: {len(selected_frameworks)}")
    
    try:
        logger.info("Initializing LLM engine...")
        engine = LLMComparisonEngine()
        logger.info(f"LLM Provider detected: {engine.provider}")
        
        if engine.provider == 'none':
            logger.warning("No LLM provider available, skipping enhancement")
            return {
                'enhanced': False,
                'comparison_data': comparison_data,
                'semantic_similarities': {},
                'summaries': {},
                'groups': {}
            }
        
        # Find semantic similarities
        logger.info("Step 1/3: Finding semantic similarities...")
        try:
            similarity_start = time.time()
            semantic_similarities = engine.find_semantic_similarities(comparison_data)
            similarity_time = time.time() - similarity_start
            logger.info(f"Semantic similarities found: {len(semantic_similarities)} in {similarity_time:.2f}s")
        except Exception as e:
            logger.error(f"Error finding semantic similarities: {e}", exc_info=True)
            semantic_similarities = {}
        
        # Generate LLM-enhanced descriptions for each criterion in each framework
        logger.info("Step 2/3: Generating LLM-enhanced descriptions and insights...")
        summaries = {}
        insights = {}
        enhanced_descriptions = {}  # Map: (criterion_name, framework_index) -> enhanced_description
        summary_count = 0
        try:
            summary_start = time.time()
            
            # Generate enhanced descriptions for each criterion-framework combination
            total_combinations = sum(
                sum(1 for fw_data in criterion.get('framework_data', []) if fw_data.get('has_criterion'))
                for criterion in comparison_data
            )
            logger.info(f"Generating LLM-enhanced descriptions for {total_combinations} criterion-framework combinations...")
            
            combination_count = 0
            success_count = 0
            for criterion in comparison_data:
                criterion_name = criterion.get('name', '')
                framework_data = criterion.get('framework_data', [])
                
                for fw_idx, fw_data in enumerate(framework_data):
                    if fw_data.get('has_criterion') and fw_idx < len(selected_frameworks):
                        framework = selected_frameworks[fw_idx]
                        key = f"{criterion_name}__{fw_idx}"
                        combination_count += 1
                        
                        try:
                            # Generate enhanced description using LLM
                            enhanced_desc = engine.generate_enhanced_description(
                                criterion_name, 
                                fw_data, 
                                framework,
                                framework_data  # Pass all framework data for context
                            )
                            if enhanced_desc:
                                enhanced_descriptions[key] = enhanced_desc
                                success_count += 1
                                logger.debug(f"✓ Enhanced description for '{criterion_name}' in '{framework.name}' ({len(enhanced_desc)} chars)")
                            else:
                                logger.debug(f"✗ No enhanced description generated for '{criterion_name}' in '{framework.name}'")
                        except Exception as e:
                            logger.warning(f"Error generating enhanced description for '{criterion_name}' in '{framework.name}': {e}")
                            continue
            
            logger.info(f"Enhanced descriptions: {success_count}/{combination_count} successful")
            
            # Generate summaries for criteria present in multiple frameworks
            criteria_to_summarize = [c for c in comparison_data 
                                   if sum(1 for fw in c.get('framework_data', []) if fw.get('has_criterion')) >= 2]
            logger.info(f"Found {len(criteria_to_summarize)} criteria to summarize")
            
            for idx, criterion in enumerate(criteria_to_summarize, 1):
                criterion_name = criterion.get('name', '')
                framework_data = criterion.get('framework_data', [])
                
                try:
                    logger.debug(f"Generating summary {idx}/{len(criteria_to_summarize)}: {criterion_name}")
                    summary = engine.generate_comparison_summary(criterion_name, framework_data)
                    if summary:
                        summaries[criterion_name] = summary
                        summary_count += 1
                        logger.debug(f"Summary generated for {criterion_name} ({len(summary)} chars)")
                    
                    # Generate additional insights for criteria in multiple frameworks
                    insight = engine.generate_criterion_insights(criterion_name, framework_data, selected_frameworks)
                    if insight:
                        insights[criterion_name] = insight
                except Exception as e:
                    logger.warning(f"Error generating summary for {criterion_name}: {e}")
                    continue
            
            # Generate insights for unique criteria (only in one framework)
            logger.info("Generating insights for unique criteria...")
            unique_criteria = [c for c in comparison_data 
                             if sum(1 for fw in c.get('framework_data', []) if fw.get('has_criterion')) == 1]
            logger.info(f"Found {len(unique_criteria)} unique criteria")
            
            for idx, criterion in enumerate(unique_criteria[:10], 1):  # Limit to 10 to avoid too many API calls
                criterion_name = criterion.get('name', '')
                framework_data = criterion.get('framework_data', [])
                
                try:
                    logger.debug(f"Generating insight for unique criterion {idx}/{min(10, len(unique_criteria))}: {criterion_name}")
                    insight = engine.generate_unique_criterion_insight(criterion_name, framework_data, selected_frameworks)
                    if insight:
                        insights[criterion_name] = insight
                except Exception as e:
                    logger.warning(f"Error generating insight for {criterion_name}: {e}")
                    continue
                    
            summary_time = time.time() - summary_start
            logger.info(f"Generated {len(enhanced_descriptions)} enhanced descriptions, {summary_count} summaries and {len(insights)} insights in {summary_time:.2f}s")
        except Exception as e:
            logger.error(f"Error generating summaries: {e}", exc_info=True)
        
        # Group related criteria
        logger.info("Step 3/3: Grouping related criteria...")
        try:
            group_start = time.time()
            groups = engine.group_related_criteria(comparison_data)
            group_time = time.time() - group_start
            logger.info(f"Created {len(groups)} groups in {group_time:.2f}s")
        except Exception as e:
            logger.error(f"Error grouping criteria: {e}", exc_info=True)
            groups = {}
        
        total_time = time.time() - start_time
        logger.info(f"=== LLM Enhancement Completed in {total_time:.2f}s ===")
        logger.info(f"Provider: {engine.provider}, Similarities: {len(semantic_similarities)}, Summaries: {len(summaries)}, Groups: {len(groups)}")
        
        # Generate overall comparison insights
        logger.info("Generating overall comparison insights...")
        overall_insights = None
        try:
            overall_insights = engine.generate_overall_insights(comparison_data, selected_frameworks, semantic_similarities, summaries)
            if overall_insights:
                logger.info(f"Overall insights generated ({len(overall_insights)} chars)")
        except Exception as e:
            logger.warning(f"Error generating overall insights: {e}")
            overall_insights = None
        
        # Update comparison_data with enhanced descriptions
        enhanced_comparison_data = []
        for criterion in comparison_data:
            criterion_name = criterion.get('name', '')
            enhanced_framework_data = []
            
            for fw_idx, fw_data in enumerate(criterion.get('framework_data', [])):
                enhanced_fw_data = fw_data.copy()
                key = f"{criterion_name}__{fw_idx}"
                
                # Add LLM-enhanced description if available
                if key in enhanced_descriptions:
                    enhanced_fw_data['llm_description'] = enhanced_descriptions[key]
                    enhanced_fw_data['has_llm_enhancement'] = True
                else:
                    enhanced_fw_data['has_llm_enhancement'] = False
                
                enhanced_framework_data.append(enhanced_fw_data)
            
            enhanced_criterion = criterion.copy()
            enhanced_criterion['framework_data'] = enhanced_framework_data
            enhanced_comparison_data.append(enhanced_criterion)
        
        return {
            'enhanced': True,
            'comparison_data': enhanced_comparison_data,
            'semantic_similarities': semantic_similarities,
            'summaries': summaries,
            'insights': insights,
            'overall_insights': overall_insights,
            'groups': groups,
            'provider': engine.provider
        }
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"=== LLM Enhancement Failed after {total_time:.2f}s ===")
        logger.error(f"Error enhancing comparison with LLM: {e}", exc_info=True)
        return {
            'enhanced': False,
            'comparison_data': comparison_data,
            'semantic_similarities': {},
            'summaries': {},
            'groups': {},
            'error': str(e)
        }
