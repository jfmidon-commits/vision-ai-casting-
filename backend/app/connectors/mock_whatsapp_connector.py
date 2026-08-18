"""
MockWhatsAppConnector - Simulador do conector WhatsApp.

NÃO envia mensagens reais. Apenas registra no console e no banco
de dados o que seria enviado. Usado para desenvolvimento e testes
do fluxo de aprovação.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

from app.utils.logger import get_logger
from app.connectors.base import (
    MessagingConnector,
    ConnectorCapability,
    ConnectorStatus,
)

logger = get_logger(__name__)


class MockWhatsAppConnector(MessagingConnector):
    """
    Conector mock do WhatsApp para desenvolvimento.
    
    Simula envio de mensagens de aprovação sem fazer chamadas reais.
    Toda ação é registrada em log para auditoria.
    """
    
    def __init__(self):
        super().__init__(
            connector_id="mock_whatsapp_001",
            name="Mock WhatsApp Connector",
            platform="whatsapp",
            capabilities=[
                ConnectorCapability.SEND_MESSAGE,
                ConnectorCapability.SEND_MEDIA,
                ConnectorCapability.RECEIVE_MESSAGE,
            ],
        )
        self.mock_messages: List[Dict[str, Any]] = []
        self.mock_approvals: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Simula conexão."""
        logger.info("[MOCK] WhatsApp connector connected")
        self._update_status(ConnectorStatus.CONNECTED)
        return True
    
    async def disconnect(self) -> bool:
        """Simula desconexão."""
        logger.info("[MOCK] WhatsApp connector disconnected")
        self._update_status(ConnectorStatus.DISCONNECTED)
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Retorna status saudável."""
        return {
            "status": "healthy",
            "platform": self.platform,
            "connector_id": self.connector_id,
            "mock": True,
            "messages_simulated": len(self.mock_messages),
        }
    
    async def send_message(
        self,
        recipient: str,
        content: str,
        media_url: Optional[str] = None,
        buttons: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Simula envio de mensagem WhatsApp.
        Registra no log e armazena internamente.
        """
        message_id = f"mock_msg_{uuid4().hex[:12]}"
        
        message_data = {
            "message_id": message_id,
            "recipient": recipient,
            "content": content,
            "media_url": media_url,
            "buttons": buttons,
            "sent_at": datetime.utcnow().isoformat(),
            "platform": "whatsapp",
            "status": "sent",
        }
        
        self.mock_messages.append(message_data)
        
        logger.info(f"[MOCK] WhatsApp message sent to {recipient}")
        logger.info(f"[MOCK] Content: {content[:150]}...")
        if buttons:
            logger.info(f"[MOCK] Buttons: {[b.get('text') for b in buttons]}")
        
        return {
            "message_id": message_id,
            "status": "sent",
            "recipient": recipient,
            "platform": "whatsapp",
            "mock": True,
        }
    
    async def send_approval_request(
        self,
        recipient: str,
        content_preview: str,
        media_url: Optional[str] = None,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Simula envio de solicitação de aprovação via WhatsApp.
        
        Envia mensagem com botões interativos:
        - APROVAR
        - ALTERAR
        - REJEITAR
        """
        buttons = [
            {"id": "approve", "text": "APROVAR"},
            {"id": "revision", "text": "ALTERAR"},
            {"id": "reject", "text": "REJEITAR"},
        ]
        
        message = (
            f"Vision - Solicitação de Aprovação\n\n"
            f"{content_preview}\n\n"
            f"Escolha uma opção:"
        )
        
        result = await self.send_message(
            recipient=recipient,
            content=message,
            media_url=media_url,
            buttons=buttons,
        )
        
        if approval_id:
            self.mock_approvals[approval_id] = {
                "recipient": recipient,
                "message_id": result["message_id"],
                "status": "pending",
                "sent_at": datetime.utcnow().isoformat(),
            }
        
        logger.info(f"[MOCK] Approval request sent: {approval_id}")
        
        return {
            **result,
            "approval_id": approval_id,
            "type": "approval_request",
        }
