#version 330 core

layout(location = 0) in vec3 vertexPosition;
layout(location = 1) in vec2 vertexUV;

out vec2 fragUV;

uniform vec2 screenRes;   // Viewport dimensions in pixels (width, height)
uniform vec2 position;    // Center position in pixels from screen center
uniform vec2 scale;       // Full width, full height in pixels
uniform float rotation;   // Rotation in radians (0 if not needed)
uniform vec2 uvOffset;    // UV offset (u0, v0)
uniform vec2 uvScale;     // UV scale (u1-u0, v1-v0)
uniform bool flipU;       // Flip U coordinate
uniform bool flipV;       // Flip V coordinate

void main() {
    // Start with unit quad vertex (-0.5 to 0.5, total span = 1.0)
    vec2 vertex = vertexPosition.xy;
    
    // Convert pixel-based inputs to normalized device coordinates
    // scale is full width/height in pixels
    // Normalized coords: screen spans 2.0 (-1 to +1), so screenRes pixels = 2.0 normalized
    // Therefore: normalized = pixels / (screenRes / 2.0)
    vec2 normalizedScale = abs(scale) / (screenRes / 2.0);
    vec2 normalizedPosition = position / (screenRes / 2.0);
    
    // CK3 Transform Order: FLIP → ROTATE → SCALE → TRANSLATE
    
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
    
    // Step 3: SCALE (using normalized scale)
    vertex *= normalizedScale;
    
    // Step 4: TRANSLATE (using normalized position)
    vertex += normalizedPosition;
    
    gl_Position = vec4(vertex, 0.0, 1.0);
    
    // Transform UVs
    vec2 uv = vertexUV;
    if (flipV) uv.y = 1.0 - uv.y;
    if (flipU) uv.x = 1.0 - uv.x;
    fragUV = uvOffset + uv * uvScale;
}
