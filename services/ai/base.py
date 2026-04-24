"""
Base AI Service
===============
Abstract base class and interfaces for AI/LLM services.
Supports multiple providers (OpenAI, local models, etc.)
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    LOCAL = "local"
    MOCK = "mock"  # For testing/development


@dataclass
class AIResponse:
    """Standard AI response container."""
    content: str
    provider: AIProvider
    model: str
    tokens_used: int = 0
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "provider": self.provider.value,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata or {},
        }


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> AIResponse:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        self._client = None
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("OpenAI package not installed")
                return None
        return self._client
    
    def is_available(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.api_key) and self._get_client() is not None
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> AIResponse:
        """Generate text using OpenAI."""
        client = self._get_client()
        
        if not client:
            raise RuntimeError("OpenAI client not available")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            return AIResponse(
                content=response.choices[0].message.content,
                provider=AIProvider.OPENAI,
                model=self.model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class MockAIProvider(BaseAIProvider):
    """Mock AI provider for development/testing."""
    
    def is_available(self) -> bool:
        return True
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> AIResponse:
        """Generate mock response based on prompt patterns."""
        content = self._generate_mock_response(prompt, system_prompt)
        
        return AIResponse(
            content=content,
            provider=AIProvider.MOCK,
            model="mock-v1",
            tokens_used=len(content.split()),
        )
    
    def _generate_mock_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate contextual mock response."""
        prompt_lower = prompt.lower()
        
        # Interview questions
        if "interview" in prompt_lower and "question" in prompt_lower:
            return self._generate_interview_questions(prompt_lower)
        
        # Cover letter
        if "cover letter" in prompt_lower:
            return self._generate_cover_letter()
        
        # Career advice
        if "career" in prompt_lower or "advice" in prompt_lower:
            return self._generate_career_advice()
        
        # Skill explanation
        if "explain" in prompt_lower or "what is" in prompt_lower:
            return self._generate_skill_explanation(prompt)
        
        # Default response
        return "I'd be happy to help you with your career development. " \
               "Could you please provide more specific details about what you need?"
    
    def _generate_interview_questions(self, prompt: str) -> str:
        """Generate mock interview questions."""
        if "behavioral" in prompt:
            return """Here are some behavioral interview questions:

1. Tell me about a time when you had to deal with a difficult team member. How did you handle it?
2. Describe a situation where you had to meet a tight deadline. What was your approach?
3. Give an example of a project that didn't go as planned. What did you learn?
4. Tell me about a time you received critical feedback. How did you respond?
5. Describe a situation where you had to learn something quickly to complete a task."""

        if "technical" in prompt:
            return """Here are some technical interview questions:

1. Explain the difference between REST and GraphQL APIs. When would you use each?
2. How would you design a URL shortening service like bit.ly?
3. What is the time complexity of your favorite sorting algorithm? Explain why.
4. How do you handle database migrations in a production environment?
5. Explain the concept of eventual consistency in distributed systems."""

        return """Here are some general interview questions:

1. Why are you interested in this position?
2. What are your greatest strengths and areas for improvement?
3. Where do you see yourself in 5 years?
4. Why are you leaving your current role?
5. What makes you the best candidate for this position?"""

    def _generate_cover_letter(self) -> str:
        """Generate mock cover letter."""
        return """Dear Hiring Manager,

I am writing to express my strong interest in the [Position] role at [Company]. With my background in software development and passion for building impactful solutions, I believe I would be a valuable addition to your team.

In my current role, I have successfully led projects that improved system performance by 40% and mentored junior developers. My experience with Python, React, and cloud technologies aligns well with your requirements.

I am particularly excited about [Company]'s mission to [mission]. I would welcome the opportunity to contribute my skills to help achieve these goals.

Thank you for considering my application. I look forward to discussing how I can contribute to your team.

Best regards,
[Your Name]"""

    def _generate_career_advice(self) -> str:
        """Generate mock career advice."""
        return """Based on current market trends, here's my career advice:

1. **Focus on In-Demand Skills**: Cloud computing (AWS, Azure), AI/ML, and DevOps skills are highly valued. Consider getting certified in these areas.

2. **Build a Strong Portfolio**: Showcase your projects on GitHub. Contribute to open source to demonstrate collaboration skills.

3. **Network Actively**: Attend tech meetups, contribute to online communities, and maintain your LinkedIn profile.

4. **Consider Specialization**: While being a generalist is valuable, having deep expertise in one area can differentiate you.

5. **Soft Skills Matter**: Communication, leadership, and problem-solving skills are increasingly important as you advance.

6. **Stay Current**: The tech industry evolves rapidly. Dedicate time each week to learning new technologies and best practices."""

    def _generate_skill_explanation(self, prompt: str) -> str:
        """Generate mock skill explanation."""
        return """Let me explain this concept:

This is a fundamental concept in software development that helps you build more maintainable and scalable applications. 

Key points:
- It promotes separation of concerns
- Makes code easier to test
- Improves collaboration in teams
- Follows industry best practices

To learn more, I recommend starting with the official documentation and then practicing with small projects before applying it to larger applications."""


class AIService:
    """
    Main AI service that manages providers and routing.
    
    Usage:
        ai = AIService()
        response = ai.generate("Write interview questions for a Python developer")
    """
    
    def __init__(self, preferred_provider: AIProvider = None):
        self.providers = {
            AIProvider.OPENAI: OpenAIProvider(),
            AIProvider.MOCK: MockAIProvider(),
        }
        
        # Determine preferred provider
        if preferred_provider:
            self.preferred = preferred_provider
        elif self.providers[AIProvider.OPENAI].is_available():
            self.preferred = AIProvider.OPENAI
        else:
            self.preferred = AIProvider.MOCK
            logger.info("Using mock AI provider (OpenAI not configured)")
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        provider: AIProvider = None,
    ) -> AIResponse:
        """
        Generate AI response using configured provider.
        
        Args:
            prompt: User prompt
            system_prompt: System context/instructions
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0-1)
            provider: Override default provider
        """
        selected_provider = provider or self.preferred
        provider_instance = self.providers.get(selected_provider)
        
        if not provider_instance or not provider_instance.is_available():
            # Fallback to mock
            provider_instance = self.providers[AIProvider.MOCK]
            selected_provider = AIProvider.MOCK
        
        logger.info(f"Generating AI response using {selected_provider.value}")
        
        return provider_instance.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    def is_openai_available(self) -> bool:
        """Check if OpenAI is configured and available."""
        return self.providers[AIProvider.OPENAI].is_available()
    
    def get_active_provider(self) -> str:
        """Get name of active provider."""
        return self.preferred.value


# Singleton instance
_ai_service_instance: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create singleton AIService instance."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
