#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================
# client.py
#
# ModelsLab API Client for PyGPT Integration
# Handles all ModelsLab API interactions with async support
# ================================================

import requests
import time
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Union, Iterator
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class ModelsLabClientError(Exception):
    """Custom exception for ModelsLab API errors"""
    pass


class ModelsLabClient:
    """
    ModelsLab API client with comprehensive multi-modal support.
    
    Supports:
    - Chat completion (OpenAI-compatible)
    - Image generation (Flux, SDXL, community models)
    - Video generation (CogVideoX, image-to-video)
    - Text-to-Speech (voice cloning, emotion control)
    - Speech-to-Text (transcription)
    """
    
    def __init__(self, api_key: str, base_url: str = "https://modelslab.com/api/"):
        """
        Initialize ModelsLab client.
        
        Args:
            api_key: ModelsLab API key
            base_url: Base API URL (default: https://modelslab.com/api/)
        """
        if not api_key:
            raise ModelsLabClientError("API key is required")
            
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        
        # HTTP session with default headers
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "PyGPT-ModelsLab/1.0",
            "Accept": "application/json"
        })
        
        # Async session (created when needed)
        self._async_session = None
        
        # Default timeouts
        self.request_timeout = 30
        self.polling_interval = 2
        self.max_polling_time = 300  # 5 minutes
    
    async def _get_async_session(self) -> aiohttp.ClientSession:
        """Get or create async HTTP session"""
        if self._async_session is None or self._async_session.closed:
            self._async_session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "PyGPT-ModelsLab/1.0",
                    "Accept": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=self.request_timeout)
            )
        return self._async_session
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make synchronous API request with error handling.
        
        Args:
            endpoint: API endpoint path
            data: Request payload
            
        Returns:
            API response data
            
        Raises:
            ModelsLabClientError: On API errors
        """
        # Add API key to request
        request_data = data.copy()
        request_data["key"] = self.api_key
        
        url = urljoin(self.base_url, endpoint)
        
        try:
            logger.debug(f"Making request to {url}")
            response = self.session.post(
                url, 
                json=request_data, 
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Response: {result.get('status', 'unknown')}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise ModelsLabClientError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise ModelsLabClientError(f"Invalid API response: {str(e)}")
    
    async def _make_async_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make asynchronous API request with error handling.
        
        Args:
            endpoint: API endpoint path
            data: Request payload
            
        Returns:
            API response data
            
        Raises:
            ModelsLabClientError: On API errors
        """
        # Add API key to request
        request_data = data.copy()
        request_data["key"] = self.api_key
        
        url = urljoin(self.base_url, endpoint)
        session = await self._get_async_session()
        
        try:
            logger.debug(f"Making async request to {url}")
            async with session.post(url, json=request_data) as response:
                response.raise_for_status()
                result = await response.json()
                logger.debug(f"Async response: {result.get('status', 'unknown')}")
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"Async request failed: {e}")
            raise ModelsLabClientError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise ModelsLabClientError(f"Invalid API response: {str(e)}")
    
    def _poll_async_task(self, task_id: str) -> Dict[str, Any]:
        """
        Poll async task until completion (synchronous).
        
        Args:
            task_id: Task ID to poll
            
        Returns:
            Final task result
            
        Raises:
            ModelsLabClientError: On task failure or timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.max_polling_time:
            try:
                result = self._make_request(f"v6/fetch/{task_id}", {})
                
                status = result.get("status", "unknown")
                if status == "success":
                    return result
                elif status == "failed":
                    error_msg = result.get("message", "Task failed")
                    raise ModelsLabClientError(f"Task failed: {error_msg}")
                elif status == "processing":
                    logger.debug(f"Task {task_id} still processing...")
                    time.sleep(self.polling_interval)
                    continue
                else:
                    logger.warning(f"Unknown task status: {status}")
                    time.sleep(self.polling_interval)
                    
            except ModelsLabClientError:
                raise
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(self.polling_interval)
        
        raise ModelsLabClientError(f"Task polling timeout after {self.max_polling_time}s")
    
    async def _poll_async_task_async(self, task_id: str) -> Dict[str, Any]:
        """
        Poll async task until completion (asynchronous).
        
        Args:
            task_id: Task ID to poll
            
        Returns:
            Final task result
            
        Raises:
            ModelsLabClientError: On task failure or timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.max_polling_time:
            try:
                result = await self._make_async_request(f"v6/fetch/{task_id}", {})
                
                status = result.get("status", "unknown")
                if status == "success":
                    return result
                elif status == "failed":
                    error_msg = result.get("message", "Task failed")
                    raise ModelsLabClientError(f"Task failed: {error_msg}")
                elif status == "processing":
                    logger.debug(f"Task {task_id} still processing...")
                    await asyncio.sleep(self.polling_interval)
                    continue
                else:
                    logger.warning(f"Unknown task status: {status}")
                    await asyncio.sleep(self.polling_interval)
                    
            except ModelsLabClientError:
                raise
            except Exception as e:
                logger.error(f"Async polling error: {e}")
                await asyncio.sleep(self.polling_interval)
        
        raise ModelsLabClientError(f"Task polling timeout after {self.max_polling_time}s")
    
    # ========================================
    # Chat Completion (LLM)
    # ========================================
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: str = "ModelsLab/Llama-3.1-8b-Uncensored-Dare",
                       stream: bool = False,
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = None,
                       **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Generate chat completion using ModelsLab uncensored chat API.
        
        Args:
            messages: OpenAI-format message list
            model: Model name (default: ModelsLab/Llama-3.1-8b-Uncensored-Dare)
            stream: Enable streaming responses
            temperature: Response randomness (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            API response or stream iterator
        """
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens is not None:
            data["max_tokens"] = max_tokens
        
        # Use uncensored-chat endpoint (OpenAI compatible)
        endpoint = "uncensored-chat/v1/chat/completions"
        
        if stream:
            # TODO: Implement streaming response handling
            raise NotImplementedError("Streaming not yet implemented")
        else:
            return self._make_request(endpoint, data)
    
    async def chat_completion_async(self, 
                                   messages: List[Dict[str, str]], 
                                   model: str = "ModelsLab/Llama-3.1-8b-Uncensored-Dare",
                                   temperature: float = 0.7,
                                   max_tokens: Optional[int] = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Generate chat completion asynchronously.
        
        Args:
            messages: OpenAI-format message list
            model: Model name
            temperature: Response randomness
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            API response
        """
        data = {
            "model": model,
            "messages": messages,
            "stream": False,  # Async doesn't support streaming yet
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens is not None:
            data["max_tokens"] = max_tokens
        
        return await self._make_async_request("uncensored-chat/v1/chat/completions", data)
    
    # ========================================
    # Image Generation
    # ========================================
    
    def generate_image(self, 
                      prompt: str,
                      model_id: str = "flux",
                      width: int = 1024,
                      height: int = 1024,
                      num_inference_steps: int = 20,
                      guidance_scale: float = 7.5,
                      negative_prompt: Optional[str] = None,
                      style_preset: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Generate image using ModelsLab API.
        
        Args:
            prompt: Text description of desired image
            model_id: Model to use (flux, sdxl, playground, etc.)
            width: Image width in pixels
            height: Image height in pixels  
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            negative_prompt: What to avoid in the image
            style_preset: Style preset name
            **kwargs: Additional parameters
            
        Returns:
            API response with image URLs
        """
        data = {
            "prompt": prompt,
            "model_id": model_id,
            "width": width,
            "height": height,
            "samples": 1,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            **kwargs
        }
        
        if negative_prompt:
            data["negative_prompt"] = negative_prompt
        if style_preset:
            data["style_preset"] = style_preset
        
        result = self._make_request("v6/images/text2img", data)
        
        # Handle async processing
        if result.get("status") == "processing":
            return self._poll_async_task(result["id"])
        
        return result
    
    async def generate_image_async(self, 
                                  prompt: str,
                                  model_id: str = "flux",
                                  width: int = 1024,
                                  height: int = 1024,
                                  **kwargs) -> Dict[str, Any]:
        """Generate image asynchronously."""
        data = {
            "prompt": prompt,
            "model_id": model_id,
            "width": width,
            "height": height,
            "samples": 1,
            **kwargs
        }
        
        result = await self._make_async_request("v6/images/text2img", data)
        
        if result.get("status") == "processing":
            return await self._poll_async_task_async(result["id"])
        
        return result
    
    # ========================================
    # Video Generation  
    # ========================================
    
    def generate_video(self,
                      prompt: str,
                      model: str = "cogvideo",
                      duration: int = 6,
                      fps: int = 8,
                      width: int = 720,
                      height: int = 480,
                      **kwargs) -> Dict[str, Any]:
        """
        Generate video using ModelsLab API.
        
        Args:
            prompt: Text description of desired video
            model: Video model to use (cogvideo, etc.)
            duration: Video duration in seconds
            fps: Frames per second
            width: Video width in pixels
            height: Video height in pixels
            **kwargs: Additional parameters
            
        Returns:
            API response with video URL
        """
        data = {
            "prompt": prompt,
            "model": model,
            "num_frames": duration * fps,
            "width": width,
            "height": height,
            **kwargs
        }
        
        result = self._make_request("v6/video/text2video", data)
        
        # Video generation is always async
        return self._poll_async_task(result["id"])
    
    def image_to_video(self,
                      image_url: str,
                      prompt: Optional[str] = None,
                      model: str = "cogvideo", 
                      **kwargs) -> Dict[str, Any]:
        """
        Convert image to video using ModelsLab API.
        
        Args:
            image_url: URL of source image
            prompt: Optional text prompt
            model: Video model to use
            **kwargs: Additional parameters
            
        Returns:
            API response with video URL
        """
        data = {
            "init_image": image_url,
            "model": model,
            **kwargs
        }
        
        if prompt:
            data["prompt"] = prompt
        
        result = self._make_request("v6/video/img2video", data)
        
        # Video generation is always async
        return self._poll_async_task(result["id"])
    
    # ========================================
    # Text-to-Speech
    # ========================================
    
    def text_to_speech(self,
                      text: str,
                      voice_id: str = "default",
                      language: str = "en",
                      speed: float = 1.0,
                      emotion: str = "neutral",
                      **kwargs) -> Dict[str, Any]:
        """
        Generate speech from text using ModelsLab TTS API.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice model identifier
            language: Language code (en, es, fr, etc.)
            speed: Speech speed multiplier
            emotion: Emotion preset (neutral, happy, sad, angry, etc.)
            **kwargs: Additional parameters
            
        Returns:
            API response with audio URL
        """
        data = {
            "text": text,
            "voice_id": voice_id,
            "language": language,
            "speed": speed,
            "emotion": emotion,
            **kwargs
        }
        
        result = self._make_request("v6/voice/text_to_speech", data)
        
        if result.get("status") == "processing":
            return self._poll_async_task(result["id"])
        
        return result
    
    # ========================================
    # Speech-to-Text
    # ========================================
    
    def speech_to_text(self,
                      audio_url: str,
                      language: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Transcribe speech to text using ModelsLab STT API.
        
        Args:
            audio_url: URL of audio file
            language: Language code (auto-detect if None)
            **kwargs: Additional parameters
            
        Returns:
            API response with transcription
        """
        data = {
            "audio": audio_url,
            **kwargs
        }
        
        if language:
            data["language"] = language
        
        result = self._make_request("v6/voice/speech_to_text", data)
        
        if result.get("status") == "processing":
            return self._poll_async_task(result["id"])
        
        return result
    
    # ========================================
    # Utility Methods
    # ========================================
    
    def close(self):
        """Close HTTP sessions."""
        if self.session:
            self.session.close()
    
    async def close_async(self):
        """Close async HTTP session."""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_async()


# ========================================
# Convenience Functions
# ========================================

def create_client(api_key: str, **kwargs) -> ModelsLabClient:
    """
    Create ModelsLab client with API key.
    
    Args:
        api_key: ModelsLab API key
        **kwargs: Additional client options
        
    Returns:
        ModelsLabClient instance
    """
    return ModelsLabClient(api_key=api_key, **kwargs)


# Model aliases for easier reference
MODELS = {
    # Chat models
    "uncensored": "ModelsLab/Llama-3.1-8b-Uncensored-Dare",
    "llama": "ModelsLab/Llama-3.1-8b-Uncensored-Dare",
    
    # Image models
    "flux": "flux",
    "sdxl": "sdxl", 
    "playground": "playground",
    
    # Video models
    "cogvideo": "cogvideo",
    
    # Voice models
    "default_voice": "default",
}