import unicodedata


def name_sort_key(name: str) -> str:
    """Ordem alfabética como o mestre espera: sem diferença de acento nem de
    maiúscula ("Álvaro" antes de "ana", que vem antes de "Bruno")."""
    decomposed = unicodedata.normalize('NFKD', name)
    plain = ''.join(
        char for char in decomposed if not unicodedata.combining(char)
    )

    return plain.casefold()
