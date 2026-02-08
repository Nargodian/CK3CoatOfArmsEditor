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
uniform sampler2D texturedMaskSampler; // Material/dirt texture (coa_mask_texture.png)
uniform sampler2D noiseMaskSampler;    // Noise texture (noise.png)
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
	
	// Apply noise and material texture using frame quad UV
	vec2 screenUV = fragUV;
	screenUV.y = 1.0 - screenUV.y;  // Flip Y
	
	// Apply material mask (dirt/texture) - blue channel
	vec4 materialSample = texture(texturedMaskSampler, screenUV);
	coaColor.rgb = mix(coaColor.rgb, coaColor.rgb * materialSample.b, 0.3);
	
	// Apply noise grain
	float noise = texture(noiseMaskSampler, screenUV).r;
	coaColor.rgb = mix(coaColor.rgb, coaColor.rgb * noise, 0.1);
	
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
			// 8-sample edge detection for smoother outlines
			vec2 texelSize = 1.0 / vec2(512.0, 512.0);
			
			// Sample 8 neighbors (cardinal + diagonal)
			float edgeSum = 0.0;
			for (int dy = -1; dy <= 1; dy++) {
				for (int dx = -1; dx <= 1; dx++) {
					if (dx == 0 && dy == 0) continue;
					vec2 offset = vec2(float(dx), float(dy)) * texelSize * 1.5;
					vec3 neighbor = texture(pickerTextureSampler, flippedCoaUV + offset).rgb;
					edgeSum += step(0.001, distance(pickerAtFrag, neighbor));
				}
			}
			
			// Smooth edge factor (0-8 neighbors different, normalize to 0-1)
			float edgeFactor = edgeSum / 8.0;
			
			// Gradient from interior fill to edge highlight
			vec3 fillColor = vec3(0.3, 0.5, 1.0);   // Blue interior
			vec3 edgeColor = vec3(0.9, 0.95, 1.0);  // Bright white-blue edge
			
			// Smooth blend based on edge factor
			float fillStrength = 0.25 * (1.0 - edgeFactor);
			float edgeStrength = smoothstep(0.1, 0.5, edgeFactor);
			
			coaColor.rgb = mix(coaColor.rgb, fillColor, fillStrength);
			coaColor.rgb = mix(coaColor.rgb, edgeColor, edgeStrength);
		}
	}
	
	// NOTE: maskAlpha IS the final alpha, it completely replaces coaColor.a
	// The frame mask defines the cutout shape, CoA provides only the RGB colors
	FragColor = vec4(coaColor.rgb, maskAlpha);
}
