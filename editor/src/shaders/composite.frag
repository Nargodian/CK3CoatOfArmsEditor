#version 330 core

/**
 * Composite Shader - Fragment Stage
 * 
 * Composites the RTT CoA texture with frame overlay using frame mask.
 * The frame mask determines where the CoA is visible through the frame.
 */

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D coaTexture;     // RTT texture containing rendered CoA
uniform sampler2D frameSampler;   // Frame texture (with prestige levels)
uniform sampler2D frameMaskSampler; // Frame mask (white = show CoA, black = show frame)

void main() {
	// Sample textures
	vec4 coaColor = texture(coaTexture, vTexCoord);
	vec4 frameColor = texture(frameSampler, vTexCoord);
	float frameMask = texture(frameMaskSampler, vTexCoord).r;
	
	// Composite: frame mask controls blending
	// frameMask = 1.0 (white): show CoA
	// frameMask = 0.0 (black): show frame
	vec4 result = mix(frameColor, coaColor, frameMask);
	
	FragColor = result;
}
