"""
MockInstagramConnector - Simulador do conector Instagram.

NÃO publica nada de verdade. Apenas registra no console e no banco
de dados o que seria publicado. Usado para desenvolvimento e testes.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

from app.utils.logger import get_logger
from app.connectors.base import (
    SocialConnector,
    ConnectorCapability,
    ConnectorStatus,
    PublishResult,
)

logger = get_logger(__name__)


class MockInstagramConnector(SocialConnector):
    """
    Conector mock do Instagram para desenvolvimento.
    
    Simula todas as operações sem fazer chamadas reais à API.
    Toda ação é registrada em log para auditoria.
    """
    
    def __init__(self):
        super().__init__(
            connector_id="mock_instagram_001",
            name="Mock Instagram Connector",
            platform="instagram",
            capabilities=[
                ConnectorCapability.PUBLISH_POST,
                ConnectorCapability.PUBLISH_STORY,
                ConnectorCapability.PUBLISH_REEL,
                ConnectorCapability.SCHEDULE_POST,
                ConnectorCapability.GET_METRICS,
            ],
        )
        self.mock_posts: List[Dict[str, Any]] = []
        self.mock_metrics: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Simula conexão - sempre retorna True."""
        logger.info("[MOCK] Instagram connector connected")
        self._update_status(ConnectorStatus.CONNECTED)
        return True
    
    async def disconnect(self) -> bool:
        """Simula desconexão."""
        logger.info("[MOCK] Instagram connector disconnected")
        self._update_status(ConnectorStatus.DISCONNECTED)
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Retorna status saudável."""
        return {
            "status": "healthy",
            "platform": self.platform,
            "connector_id": self.connector_id,
            "mock": True,
            "posts_simulated": len(self.mock_posts),
        }
    
    async def publish_post(
        self,
        content: str,
        media_urls: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        """
        Simula publicação de um post no Instagram.
        Registra no log e armazena internamente.
        """
        post_id = f"mock_post_{uuid4().hex[:12]}"
        
        post_data = {
            "post_id": post_id,
            "content": content,
            "media_urls": media_urls,
            "metadata": metadata or {},
            "published_at": datetime.utcnow().isoformat(),
            "platform": "instagram",
            "type": "post",
        }
        
        self.mock_posts.append(post_data)
        self.mock_metrics[post_id] = {
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "saves": 0,
            "reach": 0,
            "impressions": 0,
        }
        
        logger.info(f"[MOCK] Instagram post published: {post_id}")
        logger.info(f"[MOCK] Content: {content[:100]}...")
        logger.info(f"[MOCK] Media: {len(media_urls)} files")
        
        return PublishResult(
            success=True,
            post_id=post_id,
            url=f"https://instagram.com/p/{post_id}",
            published_at=datetime.utcnow(),
        )
    
    async def get_metrics(self, post_id: str) -> Dict[str, Any]:
        """Retorna métricas simuladas."""
        if post_id not in self.mock_metrics:
            return {"error": "Post not found"}
        
        # Simula crescimento de métricas
        import random
        metrics = self.mock_metrics[post_id]
        metrics["likes"] += random.randint(0, 10)
        metrics["comments"] += random.randint(0, 3)
        metrics["impressions"] += random.randint(10, 50)
        
        return {
            "post_id": post_id,
            "platform": "instagram",
            "metrics": metrics,
            "collected_at": datetime.utcnow().isoformat(),
        }
    
    async def schedule_post(
        self,
        content: str,
        media_urls: List[str],
        scheduled_at: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Simula agendamento de post."""
        schedule_id = f"mock_schedule_{uuid4().hex[:12]}"
        
        logger.info(f"[MOCK] Instagram post scheduled: {schedule_id}")
        logger.info(f"[MOCK] Scheduled for: {scheduled_at.isoformat()}")
        
        return {
            "schedule_id": schedule_id,
            "status": "scheduled",
            "scheduled_at": scheduled_at.isoformat(),
            "platform": "instagram",
            "mock": True,
        }
