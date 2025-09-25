#!/usr/bin/env python3
"""
Multi-Model AI Manager
Supports multiple AI providers (OpenAI, Anthropic, Google, local models) with intelligent routing,
fallback mechanisms, and performance optimization.
"""

import os
import json
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import random

class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"

class ModelCapability(Enum):
    TEXT_GENERATION = "text_generation"
    CONVERSATION = "conversation"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"

@dataclass
class ModelConfig:
    """Configuration for an AI model"""
    provider: ModelProvider
    model_name: str
    api_key: Optional[str]
    endpoint: Optional[str]
    capabilities: List[ModelCapability]
    max_tokens: int
    cost_per_token: float
    response_time_avg: float
    reliability_score: float
    priority: int  # Lower number = higher priority
    rate_limit_per_minute: int
    context_window: int

@dataclass
class ModelResponse:
    """Response from an AI model"""
    content: str
    provider: ModelProvider
    model_name: str
    tokens_used: int
    response_time: float
    cost: float
    confidence: float
    metadata: Dict[str, Any]

class ModelPerformanceTracker:
    """Tracks model performance and reliability"""
    
    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.performance_file = os.path.join(data_dir, "model_performance.json")
        self.performance_data = self._load_performance_data()
    
    def _load_performance_data(self) -> Dict:
        """Load performance data from file"""
        if os.path.exists(self.performance_file):
            try:
                with open(self.performance_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_performance_data(self):
        """Save performance data to file"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.performance_file, 'w') as f:
                json.dump(self.performance_data, f, indent=2)
        except Exception as e:
            print(f"Error saving performance data: {e}")
    
    def record_response(self, provider: str, model: str, response_time: float, 
                       success: bool, tokens: int, cost: float):
        """Record model response performance"""
        key = f"{provider}:{model}"
        if key not in self.performance_data:
            self.performance_data[key] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_response_time": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        data = self.performance_data[key]
        data["total_requests"] += 1
        if success:
            data["successful_requests"] += 1
        data["total_response_time"] += response_time
        data["total_tokens"] += tokens
        data["total_cost"] += cost
        data["last_updated"] = datetime.utcnow().isoformat()
        
        self._save_performance_data()
    
    def get_model_stats(self, provider: str, model: str) -> Dict:
        """Get performance statistics for a model"""
        key = f"{provider}:{model}"
        if key not in self.performance_data:
            return {}
        
        data = self.performance_data[key]
        total_requests = data["total_requests"]
        
        if total_requests == 0:
            return data
        
        return {
            **data,
            "success_rate": data["successful_requests"] / total_requests,
            "avg_response_time": data["total_response_time"] / total_requests,
            "avg_tokens_per_request": data["total_tokens"] / total_requests,
            "avg_cost_per_request": data["total_cost"] / total_requests
        }

class MultiModelManager:
    """Manages multiple AI models with intelligent routing and fallback"""

    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.models: Dict[str, ModelConfig] = {}
        self.performance_tracker = ModelPerformanceTracker(data_dir)
        self.request_cache = {}
        self.cache_ttl = 300  # 5 minutes

        # Load model configurations
        self._load_model_configs()

        # Rate limiting
        self.rate_limits = {}

        # Fallback configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.circuit_breaker = {}  # Track failing models
        self.circuit_breaker_threshold = 5  # failures before opening circuit
        self.circuit_breaker_timeout = 300  # 5 minutes before retry
    
    def _load_model_configs(self):
        """Load model configurations"""
        # OpenAI Models
        if os.getenv("OPENAI_API_KEY"):
            self.models["gpt-4-turbo"] = ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4-turbo",
                api_key=os.getenv("OPENAI_API_KEY"),
                endpoint="https://api.openai.com/v1/chat/completions",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CONVERSATION, 
                            ModelCapability.ANALYSIS, ModelCapability.SUMMARIZATION],
                max_tokens=4096,
                cost_per_token=0.00003,
                response_time_avg=2.5,
                reliability_score=0.95,
                priority=1,
                rate_limit_per_minute=500,
                context_window=128000
            )
            
            self.models["gpt-3.5-turbo"] = ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key=os.getenv("OPENAI_API_KEY"),
                endpoint="https://api.openai.com/v1/chat/completions",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CONVERSATION],
                max_tokens=4096,
                cost_per_token=0.000002,
                response_time_avg=1.5,
                reliability_score=0.92,
                priority=2,
                rate_limit_per_minute=1000,
                context_window=16385
            )
        
        # Anthropic Models
        if os.getenv("ANTHROPIC_API_KEY"):
            self.models["claude-3-sonnet"] = ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-sonnet-20240229",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                endpoint="https://api.anthropic.com/v1/messages",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CONVERSATION,
                            ModelCapability.ANALYSIS, ModelCapability.CODE_GENERATION],
                max_tokens=4096,
                cost_per_token=0.000015,
                response_time_avg=3.0,
                reliability_score=0.94,
                priority=1,
                rate_limit_per_minute=300,
                context_window=200000
            )
        
        # Google Models
        if os.getenv("GOOGLE_API_KEY"):
            self.models["gemini-pro"] = ModelConfig(
                provider=ModelProvider.GOOGLE,
                model_name="gemini-pro",
                api_key=os.getenv("GOOGLE_API_KEY"),
                endpoint="https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CONVERSATION],
                max_tokens=2048,
                cost_per_token=0.000001,
                response_time_avg=2.0,
                reliability_score=0.88,
                priority=3,
                rate_limit_per_minute=600,
                context_window=32768
            )

            self.models["gemini-1.5-pro"] = ModelConfig(
                provider=ModelProvider.GOOGLE,
                model_name="gemini-1.5-pro",
                api_key=os.getenv("GOOGLE_API_KEY"),
                endpoint="https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CONVERSATION,
                            ModelCapability.ANALYSIS, ModelCapability.CODE_GENERATION],
                max_tokens=8192,
                cost_per_token=0.000002,
                response_time_avg=2.5,
                reliability_score=0.91,
                priority=2,
                rate_limit_per_minute=300,
                context_window=1000000  # 1M token context
            )
        
        # Local Ollama Models
        if os.getenv("OLLAMA_URL"):
            self.models["llama2"] = ModelConfig(
                provider=ModelProvider.OLLAMA,
                model_name="llama2",
                api_key=None,
                endpoint=f"{os.getenv('OLLAMA_URL')}/api/generate",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CONVERSATION],
                max_tokens=2048,
                cost_per_token=0.0,  # Free local model
                response_time_avg=5.0,
                reliability_score=0.85,
                priority=4,
                rate_limit_per_minute=100,
                context_window=4096
            )

            self.models["llama3"] = ModelConfig(
                provider=ModelProvider.OLLAMA,
                model_name="llama3",
                api_key=None,
                endpoint=f"{os.getenv('OLLAMA_URL')}/api/generate",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CONVERSATION,
                            ModelCapability.ANALYSIS],
                max_tokens=4096,
                cost_per_token=0.0,
                response_time_avg=4.0,
                reliability_score=0.88,
                priority=3,
                rate_limit_per_minute=120,
                context_window=8192
            )

            self.models["codellama"] = ModelConfig(
                provider=ModelProvider.OLLAMA,
                model_name="codellama",
                api_key=None,
                endpoint=f"{os.getenv('OLLAMA_URL')}/api/generate",
                capabilities=[ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION],
                max_tokens=4096,
                cost_per_token=0.0,
                response_time_avg=6.0,
                reliability_score=0.82,
                priority=5,
                rate_limit_per_minute=80,
                context_window=16384
            )
    
    def _get_cache_key(self, prompt: str, model_name: str, options: Dict) -> str:
        """Generate cache key for request"""
        cache_data = f"{prompt}:{model_name}:{json.dumps(options, sort_keys=True)}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        cache_time = datetime.fromisoformat(cache_entry["timestamp"])
        return datetime.utcnow() - cache_time < timedelta(seconds=self.cache_ttl)
    
    def _check_rate_limit(self, model_config: ModelConfig) -> bool:
        """Check if model is rate limited"""
        key = f"{model_config.provider.value}:{model_config.model_name}"
        now = time.time()
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # Clean old requests
        self.rate_limits[key] = [req_time for req_time in self.rate_limits[key] 
                                if now - req_time < 60]
        
        # Check limit
        if len(self.rate_limits[key]) >= model_config.rate_limit_per_minute:
            return False
        
        # Add current request
        self.rate_limits[key].append(now)
        return True
    
    def select_best_model(self, capability: ModelCapability, 
                         context_length: int = 0) -> Optional[ModelConfig]:
        """Select the best model for a given capability"""
        suitable_models = []
        
        for model_config in self.models.values():
            if capability in model_config.capabilities:
                if context_length == 0 or model_config.context_window >= context_length:
                    if self._check_rate_limit(model_config):
                        suitable_models.append(model_config)
        
        if not suitable_models:
            return None
        
        # Sort by priority, then by performance
        suitable_models.sort(key=lambda m: (
            m.priority,
            -m.reliability_score,
            m.response_time_avg
        ))
        
        return suitable_models[0]
    
    async def generate_response(self, prompt: str, capability: ModelCapability,
                              options: Dict = None, use_cache: bool = True) -> Optional[ModelResponse]:
        """Generate response using the best available model"""
        options = options or {}
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(prompt, str(capability), options)
            if cache_key in self.request_cache:
                cache_entry = self.request_cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    return ModelResponse(**cache_entry["response"])
        
        # Select best model
        model_config = self.select_best_model(capability, len(prompt))
        if not model_config:
            return None
        
        # Generate response
        start_time = time.time()
        try:
            response = await self._call_model(model_config, prompt, options)
            response_time = time.time() - start_time
            
            # Record performance
            self.performance_tracker.record_response(
                model_config.provider.value,
                model_config.model_name,
                response_time,
                True,
                response.tokens_used,
                response.cost
            )
            
            # Cache response
            if use_cache:
                self.request_cache[cache_key] = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "response": asdict(response)
                }
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            self.performance_tracker.record_response(
                model_config.provider.value,
                model_config.model_name,
                response_time,
                False,
                0,
                0
            )
            
            # Try fallback model
            return await self._try_fallback(prompt, capability, options, model_config)
    
    async def _call_model(self, model_config: ModelConfig, prompt: str, 
                         options: Dict) -> ModelResponse:
        """Call specific model API"""
        if model_config.provider == ModelProvider.OPENAI:
            return await self._call_openai(model_config, prompt, options)
        elif model_config.provider == ModelProvider.ANTHROPIC:
            return await self._call_anthropic(model_config, prompt, options)
        elif model_config.provider == ModelProvider.GOOGLE:
            return await self._call_google(model_config, prompt, options)
        elif model_config.provider == ModelProvider.OLLAMA:
            return await self._call_ollama(model_config, prompt, options)
        else:
            raise ValueError(f"Unsupported provider: {model_config.provider}")
    
    async def _call_openai(self, model_config: ModelConfig, prompt: str,
                          options: Dict) -> ModelResponse:
        """Call OpenAI API"""
        headers = {
            "Authorization": f"Bearer {model_config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": options.get("max_tokens", model_config.max_tokens),
            "temperature": options.get("temperature", 0.7)
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(model_config.endpoint,
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens_used = data["usage"]["total_tokens"]

                    return ModelResponse(
                        content=content,
                        provider=model_config.provider,
                        model_name=model_config.model_name,
                        tokens_used=tokens_used,
                        response_time=0,  # Will be set by caller
                        cost=tokens_used * model_config.cost_per_token,
                        confidence=0.9,
                        metadata={"usage": data["usage"]}
                    )
                else:
                    raise Exception(f"OpenAI API error: {response.status}")

    async def _call_anthropic(self, model_config: ModelConfig, prompt: str,
                             options: Dict) -> ModelResponse:
        """Call Anthropic API"""
        headers = {
            "x-api-key": model_config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": model_config.model_name,
            "max_tokens": options.get("max_tokens", model_config.max_tokens),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": options.get("temperature", 0.7)
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(model_config.endpoint,
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["content"][0]["text"]
                    tokens_used = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]

                    return ModelResponse(
                        content=content,
                        provider=model_config.provider,
                        model_name=model_config.model_name,
                        tokens_used=tokens_used,
                        response_time=0,
                        cost=tokens_used * model_config.cost_per_token,
                        confidence=0.9,
                        metadata={"usage": data["usage"]}
                    )
                else:
                    raise Exception(f"Anthropic API error: {response.status}")

    async def _call_google(self, model_config: ModelConfig, prompt: str,
                          options: Dict) -> ModelResponse:
        """Call Google Gemini API"""
        headers = {
            "Content-Type": "application/json"
        }

        url = f"{model_config.endpoint}?key={model_config.api_key}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": options.get("temperature", 0.7),
                "maxOutputTokens": options.get("max_tokens", model_config.max_tokens)
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 100)

                    return ModelResponse(
                        content=content,
                        provider=model_config.provider,
                        model_name=model_config.model_name,
                        tokens_used=tokens_used,
                        response_time=0,
                        cost=tokens_used * model_config.cost_per_token,
                        confidence=0.85,
                        metadata={"usage": data.get("usageMetadata", {})}
                    )
                else:
                    raise Exception(f"Google API error: {response.status}")

    async def _call_ollama(self, model_config: ModelConfig, prompt: str,
                          options: Dict) -> ModelResponse:
        """Call Ollama local API"""
        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": options.get("temperature", 0.7),
                "num_predict": options.get("max_tokens", model_config.max_tokens)
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(model_config.endpoint,
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["response"]
                    tokens_used = len(content.split()) * 1.3  # Rough estimate

                    return ModelResponse(
                        content=content,
                        provider=model_config.provider,
                        model_name=model_config.model_name,
                        tokens_used=int(tokens_used),
                        response_time=0,
                        cost=0.0,  # Local model is free
                        confidence=0.8,
                        metadata={"eval_count": data.get("eval_count", 0)}
                    )
                else:
                    raise Exception(f"Ollama API error: {response.status}")
    
    async def _try_fallback(self, prompt: str, capability: ModelCapability,
                           options: Dict, failed_model: ModelConfig) -> Optional[ModelResponse]:
        """Try fallback models with circuit breaker and retry logic"""
        # Record failure for circuit breaker
        self._record_failure(failed_model)

        fallback_models = self._get_available_fallback_models(capability, failed_model)

        for model_config in fallback_models:
            # Check circuit breaker
            if self._is_circuit_breaker_open(model_config):
                continue

            if self._check_rate_limit(model_config):
                try:
                    response = await self._call_model_with_retry(model_config, prompt, options)
                    if response:
                        # Reset circuit breaker on success
                        self._reset_circuit_breaker(model_config)
                        return response
                except Exception as e:
                    self._record_failure(model_config)
                    print(f"Fallback model {model_config.model_name} failed: {e}")
                    continue

        # All models failed, try template-based fallback
        return self._generate_template_response(prompt, capability)

    def _get_available_fallback_models(self, capability: ModelCapability,
                                     failed_model: ModelConfig) -> List[ModelConfig]:
        """Get available fallback models sorted by priority and reliability"""
        fallback_models = []

        for model_config in self.models.values():
            if model_config == failed_model or capability not in model_config.capabilities:
                continue

            # Skip models with open circuit breakers (unless enough time has passed)
            if self._is_circuit_breaker_open(model_config):
                continue

            fallback_models.append(model_config)

        # Sort by priority and reliability
        fallback_models.sort(key=lambda m: (
            m.priority,
            -self._get_reliability_score(m)
        ))

        return fallback_models

    async def _call_model_with_retry(self, model_config: ModelConfig, prompt: str,
                                   options: Dict) -> Optional[ModelResponse]:
        """Call model with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await self._call_model(model_config, prompt, options)

            except Exception as e:
                last_exception = e

                # Don't retry on certain types of errors
                if self._is_permanent_error(e):
                    break

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        # All retries failed
        raise last_exception or Exception("All retries exhausted")

    def _is_permanent_error(self, error: Exception) -> bool:
        """Determine if error is permanent (don't retry)"""
        error_str = str(error).lower()
        permanent_indicators = [
            "authentication", "unauthorized", "forbidden", "api key",
            "invalid request", "model not found", "bad request"
        ]
        return any(indicator in error_str for indicator in permanent_indicators)

    def _record_failure(self, model_config: ModelConfig):
        """Record model failure for circuit breaker"""
        model_key = f"{model_config.provider.value}:{model_config.model_name}"
        current_time = time.time()

        if model_key not in self.circuit_breaker:
            self.circuit_breaker[model_key] = {
                'failures': 0,
                'last_failure': current_time,
                'state': 'closed'  # closed, open, half-open
            }

        breaker = self.circuit_breaker[model_key]
        breaker['failures'] += 1
        breaker['last_failure'] = current_time

        # Open circuit if too many failures
        if breaker['failures'] >= self.circuit_breaker_threshold:
            breaker['state'] = 'open'
            print(f"Circuit breaker OPEN for {model_key} after {breaker['failures']} failures")

    def _is_circuit_breaker_open(self, model_config: ModelConfig) -> bool:
        """Check if circuit breaker is open for model"""
        model_key = f"{model_config.provider.value}:{model_config.model_name}"

        if model_key not in self.circuit_breaker:
            return False

        breaker = self.circuit_breaker[model_key]
        current_time = time.time()

        if breaker['state'] == 'open':
            # Check if enough time has passed to try again
            if current_time - breaker['last_failure'] > self.circuit_breaker_timeout:
                breaker['state'] = 'half-open'
                print(f"Circuit breaker HALF-OPEN for {model_key}")
                return False
            return True

        return breaker['state'] == 'open'

    def _reset_circuit_breaker(self, model_config: ModelConfig):
        """Reset circuit breaker after successful call"""
        model_key = f"{model_config.provider.value}:{model_config.model_name}"

        if model_key in self.circuit_breaker:
            self.circuit_breaker[model_key] = {
                'failures': 0,
                'last_failure': 0,
                'state': 'closed'
            }

    def _get_reliability_score(self, model_config: ModelConfig) -> float:
        """Get reliability score for model"""
        stats = self.performance_tracker.get_model_stats(
            model_config.provider.value,
            model_config.model_name
        )

        if not stats or stats.get("total_requests", 0) == 0:
            return model_config.reliability_score

        # Combine configured reliability with actual performance
        success_rate = stats.get("success_rate", 0)
        return (model_config.reliability_score + success_rate) / 2

    def _generate_template_response(self, prompt: str, capability: ModelCapability) -> Optional[ModelResponse]:
        """Generate simple template-based response as last resort"""
        templates = {
            ModelCapability.TEXT_GENERATION: [
                "I understand your message. Let me help you with that.",
                "I'm processing your request. Please give me a moment.",
                "Thank you for your message. I'll get back to you shortly."
            ],
            ModelCapability.CONVERSATION: [
                "I hear you. Let me think about that.",
                "That's interesting. Can you tell me more?",
                "I understand. How can I help you with this?"
            ],
            ModelCapability.ANALYSIS: [
                "Based on your message, this appears to be a neutral inquiry.",
                "Your message seems to express a need for assistance.",
                "I'm analyzing your request and will provide insights."
            ]
        }

        fallback_responses = templates.get(capability, [
            "I apologize, but I'm experiencing technical difficulties. Please try again later."
        ])

        response_text = random.choice(fallback_responses)

        return ModelResponse(
            content=response_text,
            provider=ModelProvider.OLLAMA,  # Mark as fallback
            model_name="template_fallback",
            tokens_used=len(response_text.split()),
            response_time=0.1,
            cost=0.0,
            confidence=0.3,  # Low confidence for template responses
            metadata={'fallback': True, 'template': True}
        )
    
    def get_model_performance_report(self) -> Dict:
        """Get comprehensive model performance report"""
        report = {}
        for model_key in self.models.keys():
            provider, model_name = model_key.split(":", 1) if ":" in model_key else ("unknown", model_key)
            stats = self.performance_tracker.get_model_stats(provider, model_name)
            if stats:
                report[model_key] = stats
        
        return report

# Global multi-model manager instance
_multi_model_manager = None

def get_multi_model_manager() -> MultiModelManager:
    """Get global multi-model manager instance"""
    global _multi_model_manager
    if _multi_model_manager is None:
        _multi_model_manager = MultiModelManager()
    return _multi_model_manager
