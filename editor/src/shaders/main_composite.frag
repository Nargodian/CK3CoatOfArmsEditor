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
uniform sampler2D pickerTextureSampler;  // Picker texture for layer highlighting
uniform vec2 coaTopLeft;      // Top-left corner of CoA render area (viewport pixels)
uniform vec2 coaBottomRight;  // Bottom-right corner of CoA render area (viewport pixels)
uniform vec2 mouseUV;         // Mouse position in CoA UV space (-1,-1 = outside)
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
	
	// Apply picker overlay if mouse is hovering
	if (mouseUV.x >= 0.0) {
		// Flip Y when sampling picker texture (OpenGL bottom-up to texture top-down)
		vec2 flippedCoaUV = vec2(coaUV.x, coaUV.y);
		
		// Sample picker at mouse and current fragment
		vec3 pickerAtMouse = texture(pickerTextureSampler, vec2(mouseUV.x, 1.0 - mouseUV.y)).rgb;
		vec3 pickerAtFrag = texture(pickerTextureSampler, flippedCoaUV).rgb;
		
		// Check if mouse is over a layer (not black)
		float mouseValue = max(max(pickerAtMouse.r, pickerAtMouse.g), pickerAtMouse.b);
		
		// Check if same layer ID
		float colorDiff = distance(pickerAtMouse, pickerAtFrag);
		
		if (colorDiff < 0.001 && mouseValue > 0.01) {
			// Multi-sample edge detection
			vec2 texelSize = 1.0 / vec2(512.0, 512.0);
			float borderWidth = 2.0;
			
			// Sample 4 neighbors
			vec3 pickerRight = texture(pickerTextureSampler, flippedCoaUV + vec2(texelSize.x * borderWidth, 0.0)).rgb;
			vec3 pickerLeft = texture(pickerTextureSampler, flippedCoaUV - vec2(texelSize.x * borderWidth, 0.0)).rgb;
			vec3 pickerUp = texture(pickerTextureSampler, flippedCoaUV + vec2(0.0, texelSize.y * borderWidth)).rgb;
			vec3 pickerDown = texture(pickerTextureSampler, flippedCoaUV - vec2(0.0, texelSize.y * borderWidth)).rgb;
			
			// Edge detection
			bool isEdge = distance(pickerAtFrag, pickerRight) > 0.001 ||
			              distance(pickerAtFrag, pickerLeft) > 0.001 ||
			              distance(pickerAtFrag, pickerUp) > 0.001 ||
			              distance(pickerAtFrag, pickerDown) > 0.001;
			
			if (isEdge) {
				// Bright blue outline
				coaColor.rgb = mix(coaColor.rgb, vec3(0.6, 0.9, 1.0), 1.0);
			} else {
				// Subtle blue overlay
				coaColor.rgb = mix(coaColor.rgb, vec3(0.3, 0.5, 1.0), 0.3);
			}
			
			// Contrast adjustment
			float contrast = 1.15;
			coaColor.rgb = ((coaColor.rgb - 0.5) * contrast) + 0.5;
		}
	}
	
	// NOTE: maskAlpha IS the final alpha, it completely replaces coaColor.a
	// The frame mask defines the cutout shape, CoA provides only the RGB colors
	FragColor = vec4(coaColor.rgb, maskAlpha);
}
