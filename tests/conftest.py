"""
Shared fixtures for CK3 Coat of Arms Editor tests.

Provides reusable CoA instances, sample CK3 text, and widget fixtures.
"""
import sys
import os
import pytest

# Ensure editor/src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))


# ── Sample CK3 CoA strings ──────────────────────────────────────────────

SAMPLE_SIMPLE = """\
coa_export={
\tpattern="pattern_solid.dds"
\tcolor1=red
\tcolor2=yellow
\tcolor3=black
\tcolored_emblem={
\t\tcolor1=yellow
\t\ttexture="ce_fleur.dds"
\t\tinstance={
\t\t\tscale={ 0.700000 0.700000 }
\t\t}
\t}
}
"""

SAMPLE_MULTI_LAYER = """\
coa_export={
\tpattern="pattern_triangle_01.dds"
\tcolor1=white
\tcolor2=black
\tcolor3=blue
\tcolored_emblem={
\t\tcolor1=white
\t\ttexture="ce_mena_bend.dds"
\t\tinstance={
\t\t\tposition={ 0.970000 0.560000 }
\t\t\trotation=70
\t\t}
\t\tinstance={
\t\t\tposition={ 0.000000 0.550000 }
\t\t\tdepth=1.010000
\t\t\trotation=20
\t\t}
\t}
\tcolored_emblem={
\t\tcolor1=black
\t\ttexture="ce_tamgha_turkic_09.dds"
\t\tinstance={
\t\t\tposition={ 0.780000 0.230000 }
\t\t\tdepth=2.010000
\t\t}
\t}
\tcolored_emblem={
\t\tcolor1=black
\t\ttexture="ce_tamgha_oghuz_kayig.dds"
\t\tinstance={
\t\t\tdepth=3.010000
\t\t\trotation=59
\t\t}
\t}
}
"""

SAMPLE_THREE_COLORS = """\
coa_export={
\tpattern="pattern_solid.dds"
\tcolor1=red
\tcolor2=yellow
\tcolor3=blue
\tcolored_emblem={
\t\tcolor1=yellow
\t\tcolor2=red
\t\tcolor3=blue
\t\ttexture="ce_cross.dds"
\t\tinstance={
\t\t\tscale={ 0.700000 0.700000 }
\t\t}
\t}
}
"""


@pytest.fixture
def simple_coa_text():
    """Simple single-layer CoA text"""
    return SAMPLE_SIMPLE


@pytest.fixture
def multi_layer_coa_text():
    """Multi-layer CoA with varied instances"""
    return SAMPLE_MULTI_LAYER


@pytest.fixture
def three_color_coa_text():
    """CoA with a 3-color emblem"""
    return SAMPLE_THREE_COLORS


@pytest.fixture
def fresh_coa():
    """Fresh default CoA instance"""
    from models.coa import CoA
    coa = CoA()
    CoA.set_active(coa)
    return coa


@pytest.fixture
def parsed_simple_coa(simple_coa_text):
    """CoA parsed from simple sample"""
    from models.coa import CoA
    coa = CoA.from_string(simple_coa_text)
    CoA.set_active(coa)
    return coa


@pytest.fixture
def parsed_multi_coa(multi_layer_coa_text):
    """CoA parsed from multi-layer sample"""
    from models.coa import CoA
    coa = CoA.from_string(multi_layer_coa_text)
    CoA.set_active(coa)
    return coa


@pytest.fixture
def parsed_three_color_coa(three_color_coa_text):
    """CoA parsed from 3-color sample"""
    from models.coa import CoA
    coa = CoA.from_string(three_color_coa_text)
    CoA.set_active(coa)
    return coa
