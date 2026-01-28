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

uniform sampler2D coaTextureSampler;    // RTT texture containing rendered CoA
uniform sampler2D frameMaskSampler;  // Frame mask (white = show CoA, black = transparent)
uniform vec2 coaScale;               // Scale for CoA sampling (default 0.9, Asian frames ~1.0)
uniform vec2 coaOffset;              // Offset for CoA sampling (default 0.0, 0.04)

void main() {
	// Apply scale and offset to CoA texture coordinates
	// First scale around center (0.5, 0.5), then apply offset
	vec2 centeredUV = vTexCoord - 0.5;
	centeredUV /= coaScale;  // Scale (smaller coaScale = larger CoA in output)
	vec2 coaUV = centeredUV + 0.5; // Recenter
	coaUV += coaOffset; // Apply offset after scaling
	
	// Sample the rendered CoA texture
	vec4 coaColor = texture(coaTextureSampler, coaUV);
	
	// Sample frame mask (flip V coordinate)
	vec2 maskCoord = vec2(vTexCoord.x, 1.0 - vTexCoord.y);
	float frameMask = texture(frameMaskSampler, maskCoord).a;
	
	// Apply mask to CoA alpha
	FragColor = vec4(coaColor.rgb, frameMask);
}
