#version 330 core

/**
 * Composite Shader - Fragment Stage
 * 
 * Applies frame mask to RTT CoA texture.
 * The frame mask clips the CoA to the shield shape.
 * The actual frame graphic is rendered separately on top.
 */

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D coaTexture;        // RTT texture containing rendered CoA
uniform sampler2D frameMaskSampler;  // Frame mask (white = show CoA, black = transparent)

void main() {
	// Sample the rendered CoA texture
	vec4 coaColor = texture(coaTexture, vTexCoord);
	
	// Sample frame mask (determines where CoA is visible)
	float frameMask = texture(frameMaskSampler, vTexCoord).r;
	
	// Apply mask to CoA alpha
	FragColor = vec4(coaColor.rgb, coaColor.a * frameMask);
}
