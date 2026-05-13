from PIL import Image

from cogs.games import POKEMON_REWARD, normalizar, obtener_silueta


def test_pokemon_reward_positivo():
    assert POKEMON_REWARD > 0


def test_normalizar_quita_acentos():
    assert normalizar("Pikachú") == "pikachu"


def test_normalizar_lowercase_y_sin_espacios():
    assert normalizar("Mr. Mime") == "mr.mime"


def test_normalizar_guion_y_espacio():
    assert normalizar("Ho-Oh") == "hooh"


def test_normalizar_idempotente():
    assert normalizar(normalizar("Flabébé")) == normalizar("Flabébé")


def test_obtener_silueta_devuelve_png(tmp_path):
    img = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
    for x in range(0, 16):
        for y in range(0, 16):
            img.putpixel((x, y), (0, 0, 0, 0))
    from io import BytesIO

    buf = BytesIO()
    img.save(buf, format="PNG")
    silueta = obtener_silueta(buf.getvalue())

    out = Image.open(BytesIO(silueta))
    assert out.size == (32, 32)
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0)) == (0, 0, 0, 0)
    assert out.getpixel((20, 20)) == (0, 0, 0, 255)
