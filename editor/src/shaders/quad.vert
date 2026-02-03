#version 330 core

layout(location = 0) in vec3 vertexPosition;
layout(location = 1) in vec2 vertexUV;

out vec2 fragUV;

uniform vec2 position;    // Center position in NDC
uniform vec2 scale;       // Half-width, half-height
uniform float rotation;   // Rotation in radians (0 if not needed)
uniform vec2 uvOffset;    // UV offset (u0, v0)
uniform vec2 uvScale;     // UV scale (u1-u0, v1-v0)
uniform bool flipU;       // Flip U coordinate
uniform bool flipV;       // Flip V coordinate

void main() {
    // Start with unit quad vertex (-0.5 to 0.5, size = 1)
    vec2 vertex = vertexPosition.xy;
    
    // CK3 Transform Order: FLIP (sign of scale) → ROTATE → SCALE (absolute) → TRANSLATE
    // NOTE: This is unconventional - typically you'd scale-rotate-translate.
    // CK3 encodes flip as the sign of scale, extracts it, applies before rotation,
    // then uses absolute scale. Odd, but that's how CK3 works.
    
    // Step 1: Extract sign from scale for flipping
    vec2 flipSign = vec2(
        scale.x >= 0.0 ? 1.0 : -1.0,
        scale.y >= 0.0 ? 1.0 : -1.0
    );
    if (flipU) flipSign.x *= -1.0;
    if (flipV) flipSign.y *= -1.0;
    
    vertex *= flipSign;
    
    // Step 2: ROTATE
    if (rotation != 0.0) {
        float cosR = cos(rotation);
        float sinR = sin(rotation);
        vec2 rotated = vec2(
            vertex.x * cosR - vertex.y * sinR,
            vertex.x * sinR + vertex.y * cosR
        );
        vertex = rotated;
    }
    
    // Step 3: SCALE (use absolute value)
    vertex *= abs(scale);
    
    // Step 4: TRANSLATE
    vertex += position;
    
    gl_Position = vec4(vertex, 0.0, 1.0);
    
    // Transform UVs
    vec2 uv = vertexUV;
    if (flipV) uv.y = 1.0 - uv.y;
    if (flipU) uv.x = 1.0 - uv.x;
    fragUV = uvOffset + uv * uvScale;
}
