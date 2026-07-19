"""aptdata.studio — camada de visualização web do aptdata.

Servidor de LEITURA (stdlib, sem deps) que expõe o registry de agentes, a
decisão de roteamento e a observabilidade para um frontend vanilla. É um
*consumidor*: não tem lógica de negócio, só lê e serve.

Uso: ``aptdata studio`` (CLI) ou ``from aptdata.studio import serve; serve()``.
"""

from aptdata.studio.server import serve

__all__ = ["serve"]
