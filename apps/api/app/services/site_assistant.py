"""Respostas de apresentação e triagem. Não promete IA ou atendimento humano online."""

import unicodedata

WELCOME = (
    "Olá! Eu sou a Acme, assistente virtual da ACMEbr. "
    "Posso apresentar nossos sistemas e registrar sua necessidade. "
    "Qual é o seu ramo de atividade? Se preferir, escreva 'atendente' para falar com a equipe."
)


def reply_to(message: str, *, channel: str = "web") -> tuple[str, bool]:
    text = "".join(
        c for c in unicodedata.normalize("NFD", message.lower()) if not unicodedata.combining(c)
    )
    if text.strip(" !.,?") in ("oi", "ola", "bom dia", "boa tarde", "boa noite"):
        return WELCOME, False
    if any(word in text for word in ("atendente", "humano", "pessoa", "reclamacao")):
        destination = "WhatsApp" if channel == "whatsapp" else "chat"
        return (
            "Registrei seu pedido para a equipe. Você pode continuar deixando os detalhes aqui; "
            f"as mensagens ficam salvas e a equipe responderá neste {destination} "
            "quando estiver disponível.",
            True,
        )
    if any(word in text for word in ("preco", "valor", "orcamento", "quanto", "contratar")):
        return (
            "A proposta depende do sistema e das adaptações necessárias. "
            "Conte seu ramo, quantidade de unidades e o que precisa resolver. "
            "Não tenho um preço confirmado para informar.",
            False,
        )
    products = (
        (
            ("restaurante", "comanda", "lanchonete", "delivery"),
            "Comanda e delivery",
            "pedidos, atendimento e operação de alimentação",
        ),
        (("crm", "venda", "cliente"), "CRM", "organização de clientes e acompanhamento comercial"),
        (("ead", "curso", "aula", "escola"), "EAD", "cursos e ensino online"),
        (
            ("livro", "storebook", "ebook", "loja"),
            "StoreBook e e-commerce",
            "venda e organização de produtos e livros digitais",
        ),
        (("treino", "academia", "fitness"), "Treinos", "gestão de atividades e treinos"),
        (("condominio", "morador"), "Condomínios", "rotinas de condomínios e moradores"),
        (
            ("mqtt", "xmqr", "iot", "sensor"),
            "XMQR e IoT",
            "mensageria e integração de dispositivos",
        ),
        (
            ("erp", "estoque", "caixa", "pdv"),
            "ERP e PDV",
            "gestão comercial, estoque e frente de caixa",
        ),
    )
    for keywords, name, description in products:
        if any(word in text for word in keywords):
            return (
                f"Podemos avaliar {name} para {description}. "
                "O que você precisa melhorar na sua operação? "
                "Para conversar sobre uma proposta, escreva 'atendente'.",
                False,
            )
    return (
        "A ACMEbr desenvolve sistemas web, aplicativos e automação. "
        "Temos soluções para delivery, gestão comercial, CRM, condomínios, cursos, "
        "e-commerce, treinos e IoT. Conte seu ramo e sua necessidade, "
        "ou escreva 'atendente' para encaminhar a conversa à equipe.",
        False,
    )
