#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec2 texCoord;

out vec2 vTexCoord;

void main()
{
    // Vertices are -0.5 to 0.5, scale by 2x to fill screen (-1 to 1)
    gl_Position = vec4(position.xy * 2.0, 0.0, 1.0);
    vTexCoord = texCoord;
}
