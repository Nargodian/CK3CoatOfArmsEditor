#version 330 core

/**
 * Main Composite Shader DEBUG - Fragment Stage
 * 
 * Debug version with red fill and yellow box boundary visualization.
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
	
	// Check if we're inside the CoA bounds
	bool insideBounds = (fragPos.x >= minX && fragPos.x <= maxX && 
	                     fragPos.y >= minY && fragPos.y <= maxY);
	
	// Check if we're on the border (within 2 pixels of edge)
	float borderWidth = 2.0;
	bool onBorder = insideBounds && (
		fragPos.x < minX + borderWidth || fragPos.x > maxX - borderWidth ||
		fragPos.y < minY + borderWidth || fragPos.y > maxY - borderWidth
	);
	
	// Calculate UV coordinates from fragment position
	vec2 coaUV = (fragPos - vec2(minX, minY)) / (vec2(maxX, maxY) - vec2(minX, minY));
	float inset = 0.005;
	coaUV = clamp(coaUV, inset, 1.0 - inset);
	
	// Sample CoA texture
	vec4 coaColor = texture(coaTextureSampler, coaUV);
	
	// Debug visualization:
	// - Red background everywhere
	// - Yellow box over the CoA bounds area
	if (insideBounds) {
		FragColor = vec4(1.0, 1.0, 0.0, 1.0);  // Yellow where CoA should be
	} else {
		FragColor = vec4(1.0, 0.0, 0.0, 1.0);  // Red background
	}
}
