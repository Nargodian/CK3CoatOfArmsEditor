"""
Tests for Color class and Layer color properties.

Verifies:
- Color construction from all factory methods
- Color equality, hashing, output formats
- CK3 named color resolution
- Layer color1/2/3 get/set symmetry (color3 setter regression)
- Layer property access patterns (Vec2, transform)
- Instance defaults and properties
"""
import pytest
from models.color import Color
from models.transform import Vec2


# ══════════════════════════════════════════════════════════════════════════
# Color Construction
# ══════════════════════════════════════════════════════════════════════════

class TestColorConstruction:

    def test_from_name_known(self):
        c = Color.from_name("red")
        assert isinstance(c, Color)
        assert c.name == "red"
        assert c.r > 0

    def test_from_name_all_ck3_colors(self):
        """Every CK3 named color must resolve without error."""
        from constants import CK3_NAMED_COLORS
        for name in CK3_NAMED_COLORS:
            c = Color.from_name(name)
            assert isinstance(c, Color), f"Failed for '{name}'"
            assert c.name == name

    def test_from_name_unknown_fallback(self):
        """Unknown names should not crash."""
        c = Color.from_name("totally_fake_color")
        assert isinstance(c, Color)

    def test_from_rgb255(self):
        c = Color.from_rgb255(100, 150, 200)
        assert c.r == 100
        assert c.g == 150
        assert c.b == 200

    def test_from_hex(self):
        c = Color.from_hex("#FF0000")
        assert c is not None
        assert c.r == 255
        assert c.g == 0
        assert c.b == 0

    def test_from_hex_no_hash(self):
        c = Color.from_hex("00FF00")
        assert c is not None
        assert c.g == 255

    def test_from_float3(self):
        c = Color.from_float3([1.0, 0.5, 0.0])
        assert c.r == 255
        assert 126 <= c.g <= 128  # float rounding
        assert c.b == 0

    def test_from_ck3_string_rgb(self):
        c = Color.from_ck3_string("rgb { 100 200 50 }")
        assert c is not None
        assert c.r == 100
        assert c.g == 200
        assert c.b == 50

    def test_from_ck3_string_invalid(self):
        c = Color.from_ck3_string("not a color")
        assert c is None

    def test_clamping(self):
        c = Color(300, -10, 128)
        assert c.r == 255
        assert c.g == 0
        assert c.b == 128


# ══════════════════════════════════════════════════════════════════════════
# Color Output
# ══════════════════════════════════════════════════════════════════════════

class TestColorOutput:

    def test_to_hex(self):
        c = Color(255, 0, 0)
        assert c.to_hex().upper() == "#FF0000"

    def test_to_float3(self):
        c = Color(255, 0, 128)
        f = c.to_float3()
        assert len(f) == 3
        assert abs(f[0] - 1.0) < 0.01
        assert abs(f[1] - 0.0) < 0.01
        assert 0.49 < f[2] < 0.51

    def test_to_ck3_string_named(self):
        c = Color.from_name("red")
        s = c.to_ck3_string()
        assert s == "red"

    def test_to_ck3_string_force_rgb(self):
        c = Color.from_name("red")
        s = c.to_ck3_string(force_rgb=True)
        assert "rgb" in s

    def test_to_ck3_string_custom(self):
        c = Color(42, 128, 200)
        s = c.to_ck3_string()
        assert "rgb" in s
        assert "42" in s

    def test_to_rgb255(self):
        c = Color(10, 20, 30)
        lst = c.to_rgb255()
        assert lst == [10, 20, 30]


# ══════════════════════════════════════════════════════════════════════════
# Color Equality & Hashing
# ══════════════════════════════════════════════════════════════════════════

class TestColorEquality:

    def test_equal_same_rgb_and_name(self):
        a = Color.from_name("red")
        b = Color.from_name("red")
        assert a == b

    def test_equal_same_rgb_different_name(self):
        a = Color(100, 100, 100, name="foo")
        b = Color(100, 100, 100, name="bar")
        # Equality includes name, so these should NOT be equal
        assert a != b

    def test_hash_same_rgb(self):
        a = Color(100, 100, 100)
        b = Color(100, 100, 100)
        # Hash is RGB-only so they can coexist in sets
        assert hash(a) == hash(b)

    def test_not_equal_different_rgb(self):
        a = Color(100, 100, 100)
        b = Color(200, 200, 200)
        assert a != b


# ══════════════════════════════════════════════════════════════════════════
# Color Mutation
# ══════════════════════════════════════════════════════════════════════════

class TestColorMutation:

    def test_set_rgb255(self):
        c = Color(0, 0, 0)
        c.set_rgb255(42, 100, 200)
        assert c.r == 42
        assert c.g == 100
        assert c.b == 200

    def test_set_hex(self):
        c = Color(0, 0, 0)
        result = c.set_hex("#FF8800")
        assert result is True
        assert c.r == 255
        assert c.g == 0x88
        assert c.b == 0

    def test_set_name(self):
        c = Color(0, 0, 0)
        result = c.set_name("blue")
        assert result is True
        assert c.name == "blue"

    def test_set_float(self):
        c = Color(0, 0, 0)
        c.set_float(1.0, 0.5, 0.0)
        assert c.r == 255
        assert c.b == 0


# ══════════════════════════════════════════════════════════════════════════
# Layer Color Properties (direct layer access)
# ══════════════════════════════════════════════════════════════════════════

class TestLayerColorProperties:
    """Test that Layer.color1/2/3 all have working getters AND setters.

    This is the core regression test for the missing color3 setter.
    """

    @pytest.fixture
    def layer(self):
        from models.coa._internal.layer import Layer
        return Layer(caller='CoA')

    @pytest.mark.parametrize("attr", ["color1", "color2", "color3"])
    def test_getter_returns_color(self, layer, attr):
        c = getattr(layer, attr)
        assert isinstance(c, Color)

    @pytest.mark.parametrize("attr", ["color1", "color2", "color3"])
    def test_setter_accepts_color(self, layer, attr):
        """This is the exact test that would have caught the color3 bug."""
        new_color = Color.from_name("white")
        setattr(layer, attr, new_color)
        result = getattr(layer, attr)
        assert result.r == new_color.r
        assert result.g == new_color.g
        assert result.b == new_color.b

    @pytest.mark.parametrize("attr", ["color1", "color2", "color3"])
    def test_setter_rejects_non_color(self, layer, attr):
        with pytest.raises(TypeError):
            setattr(layer, attr, (255, 0, 0))

    @pytest.mark.parametrize("attr", ["color1", "color2", "color3"])
    def test_set_read_back_custom_rgb(self, layer, attr):
        custom = Color(11, 22, 33)
        setattr(layer, attr, custom)
        got = getattr(layer, attr)
        assert got.r == 11
        assert got.g == 22
        assert got.b == 33


# ══════════════════════════════════════════════════════════════════════════
# Layer Position/Scale (Vec2)
# ══════════════════════════════════════════════════════════════════════════

class TestLayerTransform:

    @pytest.fixture
    def layer(self):
        from models.coa._internal.layer import Layer
        return Layer(caller='CoA')

    def test_default_pos(self, layer):
        pos = layer.pos
        assert isinstance(pos, Vec2)
        # Default is 0.5, 0.5
        assert abs(pos.x - 0.5) < 0.01
        assert abs(pos.y - 0.5) < 0.01

    def test_set_pos(self, layer):
        layer.pos = Vec2(0.2, 0.8)
        assert abs(layer.pos.x - 0.2) < 0.01
        assert abs(layer.pos.y - 0.8) < 0.01

    def test_default_scale(self, layer):
        scale = layer.scale
        assert isinstance(scale, Vec2)

    def test_set_scale(self, layer):
        layer.scale = Vec2(0.5, 0.3)
        assert abs(layer.scale.x - 0.5) < 0.01
        assert abs(layer.scale.y - 0.3) < 0.01

    def test_unpack_pos(self, layer):
        x, y = layer.pos
        assert isinstance(x, float)
        assert isinstance(y, float)

    def test_unpack_scale(self, layer):
        sx, sy = layer.scale
        assert isinstance(sx, float)
        assert isinstance(sy, float)


# ══════════════════════════════════════════════════════════════════════════
# Layer Misc Properties
# ══════════════════════════════════════════════════════════════════════════

class TestLayerMiscProperties:

    @pytest.fixture
    def layer(self):
        from models.coa._internal.layer import Layer
        return Layer(caller='CoA')

    def test_uuid_exists(self, layer):
        assert layer.uuid is not None
        assert len(layer.uuid) > 0

    def test_visible_default_true(self, layer):
        assert layer.visible is True

    def test_set_visible(self, layer):
        layer.visible = False
        assert layer.visible is False

    def test_flip_x_default_false(self, layer):
        assert layer.flip_x is False

    def test_set_flip_x(self, layer):
        layer.flip_x = True
        assert layer.flip_x is True

    def test_flip_y_default_false(self, layer):
        assert layer.flip_y is False

    def test_set_flip_y(self, layer):
        layer.flip_y = True
        assert layer.flip_y is True

    def test_rotation_default(self, layer):
        assert layer.rotation == 0 or layer.rotation == 0.0

    def test_set_rotation(self, layer):
        layer.rotation = 45.0
        assert abs(layer.rotation - 45.0) < 0.01
