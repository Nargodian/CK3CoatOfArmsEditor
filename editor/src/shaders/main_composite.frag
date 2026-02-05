#version 330 core

/**
 * Main Composite Shader - Fragment Stage
 * 
 * Frame-aware CoA rendering using pixel-space corner positions.
 * No UV math - fragment shader calculates its own UVs from gl_FragCoord.
 */

in vec2 fragUV;
out vec4 FragColor;

uniform sampler2D coaTextureSampler;   // RTT texture containing rendered CoA
uniform sampler2D frameMaskSampler;    // Frame mask texture (alpha defines shape)
uniform vec2 coaTopLeft;      // Top-left corner of CoA render area (viewport pixels)
uniform vec2 coaBottomRight;  // Bottom-right corner of CoA render area (viewport pixels)
uniform bool useMask;    // Whether to smear to a mask or just clip beyond the mask bounds (for debugging)

const float FRAME_MASK_SCALE = 0.75;  // Scale factor for frame mask sampling
const float FRAME_MASK_FUDGE = 1.10; // Fudge factor to push the mask UVs out slightly

void main() {
	// Get fragment position in viewport coordinates
	vec2 fragPos = gl_FragCoord.xy;
	
	// Calculate min/max bounds (handles top > bottom in Y)
	float minX = min(coaTopLeft.x, coaBottomRight.x);
	float maxX = max(coaTopLeft.x, coaBottomRight.x);
	float minY = min(coaTopLeft.y, coaBottomRight.y);
	float maxY = max(coaTopLeft.y, coaBottomRight.y);
	
	// Calculate UV coordinates from fragment position for CoA sampling
	// Map fragment position to 0-1 range within CoA bounds
	vec2 coaUV = (fragPos - vec2(minX, minY)) / (vec2(maxX, maxY) - vec2(minX, minY));
	
	// Sample CoA texture (RGB colors)
	vec4 coaColor = texture(coaTextureSampler, coaUV);
	
	// Calculate frame mask UV from frame quad UV (fragUV from vertex shader)
	// Scale to sample from center portion of mask texture, then push out with fudge factor
	vec2 frameMaskUV = ((fragUV - 0.5) / FRAME_MASK_FUDGE) / FRAME_MASK_SCALE + 0.5;
	
	// Check if frame mask UV is outside 0-1 range (beyond texture = 0 alpha)
	float maskAlpha = 0.0;
	if (frameMaskUV.x >= 0.0 && frameMaskUV.x <= 1.0 && 
	    frameMaskUV.y >= 0.0 && frameMaskUV.y <= 1.0) {
		// Sample frame mask texture
		vec4 frameMask = texture(frameMaskSampler, frameMaskUV);
		maskAlpha = frameMask.a;
	}
	if (!useMask) {
		maskAlpha = 1.0; // Ignore mask alpha, just use the CoA colors within the frame bounds
		if (minX > fragPos.x || fragPos.x > maxX || minY > fragPos.y || fragPos.y > maxY) 
		{
			maskAlpha = 0.0;
		}
	}
	
	// NOTE: maskAlpha IS the final alpha, it completely replaces coaColor.a
	// The frame mask defines the cutout shape, CoA provides only the RGB colors
	FragColor = vec4(coaColor.rgb, maskAlpha);
}
