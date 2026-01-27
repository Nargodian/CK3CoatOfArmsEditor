#version 330 core

/**
 * Composite Shader - Fragment Stage
 * 
 * Composites the RTT CoA texture with optional frame overlay using frame mask.
 * For now, just displays the CoA texture directly.
 */

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D coaTexture;     // RTT texture containing rendered CoA

void main() {
	// Sample the rendered CoA texture
	vec4 coaColor = texture(coaTexture, vTexCoord);
	
	// Output directly (TODO: add frame compositing)
	FragColor = coaColor;
}
