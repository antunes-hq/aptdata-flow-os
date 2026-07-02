"""aptdata.transports — transportes FINOS sobre o ConversationEngine.

Regra de ouro (docs/plans/telegram-orchestration.md): transporte = I/O do
canal. Nenhuma decisão de rota, threshold ou estado de conversa vive aqui —
o cérebro é o :class:`aptdata.agents.ConversationEngine`.
"""

from aptdata.transports.telegram import TelegramTransport, render_turn

__all__ = ["TelegramTransport", "render_turn"]
