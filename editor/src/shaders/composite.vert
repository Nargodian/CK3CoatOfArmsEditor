#version 330 core

/**
 * Composite Shader - Vertex Stage
 * 
 * Simple passthrough shader for compositing RTT texture to viewport.
 * Used to render the offscreen-rendered CoA to the screen.
 */

layout(location = 0) in vec3 position;
layout(location = 1) in vec2 texCoord;

out vec2 vTexCoord;

void main() {
	vTexCoord = texCoord;
	gl_Position = vec4(position, 1.0);
}
