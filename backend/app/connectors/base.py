"""
VisionConnector - Interface base para todos os conectores externos.

Conectores são responsáveis pela integração com serviços externos:
- Redes sociais (Instagram, TikTok, LinkedIn, YouTube)
- Mensagens (WhatsApp, Email, Push)
- Casting (plataformas de casting)
- Storage (S3, Google Cloud, etc)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class ConnectorType(str, Enum):
    SOCIAL = "social"
    MESSAGING = "messaging"
    CASTING = "casting"
    STORAGE = "storage"


class ConnectorStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class ConnectorCapability(str, Enum):
    # Social
    PUBLISH_POST = "publish_post"
    PUBLISH_STORY = "publish_story"
    PUBLISH_REEL = "publish_reel"
    SCHEDULE_POST = "schedule_post"
    GET_METRICS = "get_metrics"
    GET_COMMENTS = "get_comments"
    
    # Messaging
    SEND_MESSAGE = "send_message"
    SEND_MEDIA = "send_media"
    RECEIVE_MESSAGE = "receive_message"
    
    # Casting
    SEARCH_CASTINGS = "search_castings"
    APPLY_CASTING = "apply_casting"
    GET_CASTING_DETAILS = "get_casting_details"
    
    # Storage
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    DELETE_FILE = "delete_file"
    GENERATE_URL = "generate_url"


class PublishResult:
    """Resultado de uma publicação."""
    
    def __init__(
        self,
        success: bool,
        post_id: Optional[str] = None,
        url: Optional[str] = None,
        error: Optional[str] = None,
        published_at: Optional[datetime] = None,
    ):
        self.success = success
        self.post_id = post_id
        self.url = url
        self.error = error
        self.published_at = published_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "post_id": self.post_id,
            "url": self.url,
            "error": self.error,
            "published_at": self.published_at.isoformat(),
        }


class VisionConnector(ABC):
    """Interface base para todos os conectores."""
    
    def __init__(
        self,
        connector_id: str,
        name: str,
        connector_type: ConnectorType,
        capabilities: List[ConnectorCapability],
    ):
        self.connector_id = connector_id
        self.name = name
        self.connector_type = connector_type
        self.capabilities = capabilities
        self.status = ConnectorStatus.DISCONNECTED
        self.last_error: Optional[str] = None
        self.last_used: Optional[datetime] = None
    
    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Estabelece conexão com o serviço externo."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Encerra a conexão."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verifica a saúde da conexão."""
        pass
    
    def has_capability(self, capability: ConnectorCapability) -> bool:
        return capability in self.capabilities
    
    def _update_status(self, status: ConnectorStatus, error: Optional[str] = None):
        self.status = status
        self.last_error = error
        self.last_used = datetime.utcnow()


class SocialConnector(VisionConnector):
    """Interface base para conectores de redes sociais."""
    
    def __init__(
        self,
        connector_id: str,
        name: str,
        platform: str,  # instagram, tiktok, youtube, linkedin
        capabilities: List[ConnectorCapability],
    ):
        super().__init__(
            connector_id=connector_id,
            name=name,
            connector_type=ConnectorType.SOCIAL,
            capabilities=capabilities,
        )
        self.platform = platform
    
    @abstractmethod
    async def publish_post(
        self,
        content: str,
        media_urls: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        """Publica um post na rede social."""
        pass
    
    @abstractmethod
    async def get_metrics(
        self,
        post_id: str,
    ) -> Dict[str, Any]:
        """Obtém métricas de um post."""
        pass
    
    @abstractmethod
    async def schedule_post(
        self,
        content: str,
        media_urls: List[str],
        scheduled_at: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Agenda uma publicação."""
        pass


class MessagingConnector(VisionConnector):
    """Interface base para conectores de mensagens."""
    
    def __init__(
        self,
        connector_id: str,
        name: str,
        platform: str,  # whatsapp, email, push
        capabilities: List[ConnectorCapability],
    ):
        super().__init__(
            connector_id=connector_id,
            name=name,
            connector_type=ConnectorType.MESSAGING,
            capabilities=capabilities,
        )
        self.platform = platform
    
    @abstractmethod
    async def send_message(
        self,
        recipient: str,
        content: str,
        media_url: Optional[str] = None,
        buttons: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Envia uma mensagem."""
        pass
    
    @abstractmethod
    async def send_approval_request(
        self,
        recipient: str,
        content_preview: str,
        media_url: Optional[str] = None,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Envia solicitação de aprovação com botões interativos."""
        pass


class CastingConnector(VisionConnector):
    """Interface base para conectores de plataformas de casting."""
    
    def __init__(
        self,
        connector_id: str,
        name: str,
        platform: str,
        capabilities: List[ConnectorCapability],
    ):
        super().__init__(
            connector_id=connector_id,
            name=name,
            connector_type=ConnectorType.CASTING,
            capabilities=capabilities,
        )
        self.platform = platform
    
    @abstractmethod
    async def search_castings(
        self,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Busca oportunidades de casting."""
        pass
    
    @abstractmethod
    async def apply_to_casting(
        self,
        casting_id: str,
        profile_data: Dict[str, Any],
        materials: List[str],
    ) -> Dict[str, Any]:
        """Candidata-se a um casting."""
        pass
