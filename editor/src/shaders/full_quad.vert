#version 330 core

layout(location = 0) in vec3 vertexPosition;
layout(location = 1) in vec2 vertexUV;

out vec2 fragUV;
flat out ivec2 tileIndex;

uniform vec2 uvOffset;    // UV offset (u0, v0)
uniform vec2 uvScale;     // UV scale (u1-u0, v1-v0)

void main() {
    // Unit quad vertices are already in NDC space (-1 to +1)
    // No transforms needed - render full-screen
    gl_Position = vec4(vertexPosition.xy, 0.0, 1.0);
    
    // Calculate tile index from UV offset (32x32 grid)
    tileIndex = ivec2(uvOffset * 32.0);
    
    // UV coordinates in 0-1 range within the tile
    fragUV = vertexUV;
}
