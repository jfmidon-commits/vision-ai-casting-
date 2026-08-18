"""
LLMProvider - Interface base para provedores de Language Models.

Permite trocar entre OpenAI, Anthropic, Google, modelos locais, etc.
sem alterar o código dos agentes.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from enum import Enum
from dataclasses import dataclass


class LLMProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"
    AZURE = "azure"


@dataclass
class LLMMessage:
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """
    Interface base para provedores de LLM.
    
    Implementações concretas devem herdar desta classe e implementar
    os métodos de comunicação com a API específica.
    """
    
    def __init__(
        self,
        provider_type: LLMProviderType,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: int = 60,
    ):
        self.provider_type = provider_type
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
    
    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        response_format: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        """
        Envia uma conversa para o modelo e retorna a resposta.
        
        Args:
            messages: Lista de mensagens
            response_format: Formato da resposta (json_object, etc)
            tools: Ferramentas disponíveis para o modelo
            
        Returns:
            LLMResponse com o conteúdo gerado
        """
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[LLMMessage],
    ) -> AsyncGenerator[str, None]:
        """
        Envia uma conversa e retorna a resposta em streaming.
        
        Args:
            messages: Lista de mensagens
            
        Yields:
            Chunks de texto da resposta
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se o provedor está acessível."""
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna a configuração atual (sem a API key)."""
        return {
            "provider_type": self.provider_type.value,
            "model": self.model,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
        }


class OpenAIProvider(LLMProvider):
    """Implementação do provedor OpenAI."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            provider_type=LLMProviderType.OPENAI,
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client
    
    async def chat(
        self,
        messages: List[LLMMessage],
        response_format: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        client = self._get_client()
        
        formatted_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        params = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        if response_format:
            params["response_format"] = {"type": response_format}
        if tools:
            params["tools"] = tools
        
        response = await client.chat.completions.create(**params)
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )
    
    async def stream_chat(
        self,
        messages: List[LLMMessage],
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        
        formatted_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        stream = await client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            await client.models.list()
            return True
        except Exception:
            return False


class AnthropicProvider(LLMProvider):
    """Implementação do provedor Anthropic (Claude)."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        **kwargs
    ):
        super().__init__(
            provider_type=LLMProviderType.ANTHROPIC,
            model=model,
            api_key=api_key,
            **kwargs
        )
    
    async def chat(
        self,
        messages: List[LLMMessage],
        response_format: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        # Placeholder - implementação real requeria a SDK da Anthropic
        return LLMResponse(
            content="Anthropic provider not yet implemented",
            model=self.model,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
    
    async def stream_chat(
        self,
        messages: List[LLMMessage],
    ) -> AsyncGenerator[str, None]:
        yield "Anthropic provider not yet implemented"
    
    async def health_check(self) -> bool:
        return False


class LocalProvider(LLMProvider):
    """Implementação para modelos locais (Ollama, etc)."""
    
    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        **kwargs
    ):
        super().__init__(
            provider_type=LLMProviderType.LOCAL,
            model=model,
            base_url=base_url,
            **kwargs
        )
    
    async def chat(
        self,
        messages: List[LLMMessage],
        response_format: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        # Placeholder - implementação real usaria httpx para chamar Ollama
        return LLMResponse(
            content="Local provider not yet implemented",
            model=self.model,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
    
    async def stream_chat(
        self,
        messages: List[LLMMessage],
    ) -> AsyncGenerator[str, None]:
        yield "Local provider not yet implemented"
    
    async def health_check(self) -> bool:
        return False


class LLMProviderFactory:
    """Factory para criar instâncias de provedores LLM."""
    
    @staticmethod
    def create(
        provider_type: LLMProviderType,
        **config
    ) -> LLMProvider:
        if provider_type == LLMProviderType.OPENAI:
            return OpenAIProvider(**config)
        elif provider_type == LLMProviderType.ANTHROPIC:
            return AnthropicProvider(**config)
        elif provider_type == LLMProviderType.LOCAL:
            return LocalProvider(**config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
