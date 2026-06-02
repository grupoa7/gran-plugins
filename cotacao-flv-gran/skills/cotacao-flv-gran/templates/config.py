"""Conteúdo/parametros editáveis. Mexer AQUI, não na lógica dos scripts."""

# Banda de sanidade: alerta se preço cotado > FATOR x último custo (ou < 1/FATOR)
FATOR_BANDA_SANIDADE = 2.0

# Alerta "acima do mercado" se preço > FATOR_MEDIANA x mediana (e houver >=3 fontes)
FATOR_ACIMA_MEDIANA = 1.20

# Rodapé dos pedidos WhatsApp
RODAPE_PEDIDO = "Confirmar separação e disponibilidade 🙏"
