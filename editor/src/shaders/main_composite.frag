#version 330 core

/**
 * Main Composite Shader - Fragment Stage
 * 
 * Frame-aware CoA rendering using pixel-space corner positions.
 * No UV math - fragment shader calculates its own UVs from gl_FragCoord.
 */

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D coaTextureSampler;  // RTT texture containing rendered CoA
uniform vec2 coaTopLeft;      // Top-left corner of CoA render area (viewport pixels)
uniform vec2 coaBottomRight;  // Bottom-right corner of CoA render area (viewport pixels)

void main() {
	// Get fragment position in viewport coordinates
	vec2 fragPos = gl_FragCoord.xy;
	
	// Calculate min/max bounds (handles top > bottom in Y)
	float minX = min(coaTopLeft.x, coaBottomRight.x);
	float maxX = max(coaTopLeft.x, coaBottomRight.x);
	float minY = min(coaTopLeft.y, coaBottomRight.y);
	float maxY = max(coaTopLeft.y, coaBottomRight.y);
	
	// Calculate UV coordinates from fragment position
	// Map fragment position to 0-1 range within CoA bounds
	vec2 coaUV = (fragPos - vec2(minX, minY)) / (vec2(maxX, maxY) - vec2(minX, minY));
	
	// Clamp UVs with small inset to avoid edge artifacts
	float inset = 0.005;
	coaUV = clamp(coaUV, inset, 1.0 - inset);
	
	// Sample CoA texture
	vec4 coaColor = texture(coaTextureSampler, coaUV);
	
	FragColor = coaColor;
}
