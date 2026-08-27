"""
Regressão: grooming/analyzer.py::_analyze_skin usava
sample.reshape(int(np.sqrt(len(sample))), -1) para montar uma amostra
quase-quadrada da região de pele antes de calcular variância de textura
(cv2.Laplacian). int(sqrt(n)) só produz um reshape válido quando n é
divisível por esse valor truncado -- não garantido, já que n depende do
tamanho da região de pele detectada em cada foto.

Bug real em produção: ValueError: cannot reshape array of size 1869 into
shape (43,newaxis) (sqrt(1869)≈43.23, int()=43, 1869 não é múltiplo de 43).

Este teste não reproduz o número exato 1869 (isso dependeria de ajustar
dimensões de imagem para bater exatamente), mas reproduz a MESMA classe de
falha através do código real (_analyze_skin sem landmarks, usando as
regiões de testa/bochechas aproximadas): com face_gray 100x100, a soma das
3 regiões dá 5000 pixels, e int(sqrt(5000))=70, mas 70*70=4900 != 5000 --
o reshape antigo quebraria aqui do mesmo jeito.
"""
import numpy as np
import pytest

from app.ai.grooming.analyzer import GroomingAnalyzer


@pytest.fixture
def analyzer():
    return GroomingAnalyzer()


def test_analyze_skin_texture_reshape_does_not_crash_on_non_square_sample(analyzer):
    """Reproduz a classe do bug real: reshape com int(sqrt(n)) que não
    divide n. Antes da correção, isto levantava:
    ValueError: cannot reshape array of size 5000 into shape (70,newaxis)
    """
    h, w = 100, 100
    face_gray = np.random.randint(0, 255, size=(h, w), dtype=np.uint8)
    face_color = np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8)

    # landmarks=None força o caminho de regiões aproximadas (testa +
    # bochechas), que é onde o tamanho não-quadrado de 5000 pixels ocorre.
    result = analyzer._analyze_skin(
        face_color=face_color,
        face_gray=face_gray,
        landmarks=None,
        face_x=0,
        face_y=0,
        face_w=w,
        face_h=h,
    )

    # Não crashou -- o objetivo principal do teste. Verificações adicionais
    # confirmam que o resultado ainda é coerente (score em [0,1]).
    assert result is not None
    assert 0.0 <= result.overall_score <= 1.0


@pytest.mark.parametrize("sample_size", [1869, 5000, 101, 9999, 7, 200])
def test_texture_reshape_pattern_never_raises_for_various_sizes(sample_size):
    """Testa diretamente o padrão de reshape defensivo (side*side <= n)
    para uma variedade de tamanhos, incluindo o valor exato reportado em
    produção (1869), sem precisar reconstruir toda a análise de imagem."""
    sample = np.random.randint(0, 255, size=sample_size, dtype=np.uint8)

    side = int(np.sqrt(len(sample)))
    if side == 0:
        pytest.skip("tamanho degenerado, fora do branch protegido por len > 100")

    # Este é exatamente o padrão aplicado em analyzer.py após a correção.
    sample_2d = sample[: side * side].reshape(side, side)

    assert sample_2d.shape == (side, side)
    assert sample_2d.size <= sample_size
