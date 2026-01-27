#version 330 core

/**
 * Composite Shader - Fragment Stage
 * 
 * Samples the RTT texture and outputs to viewport.
 * Can apply additional post-processing effects here if needed.
 */

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D coaTexture;  // RTT texture containing rendered CoA

void main() {
	// Sample the rendered CoA texture
	vec4 coaColor = texture(coaTexture, vTexCoord);
	
	// Output directly (future: could add frame overlay, effects, etc.)
	FragColor = coaColor;
}
