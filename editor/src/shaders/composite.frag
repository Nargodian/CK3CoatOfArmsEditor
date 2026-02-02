#version 330 core

/**
 * Composite Shader - Fragment Stage
 * 
 * Applies frame mask to RTT CoA texture.
 * The frame mask clips the CoA to the shield shape.
 * The actual frame graphic is rendered separately on top.
 * Noise and material textures are applied here after UV transformation.
 */

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D coaTextureSampler;    // RTT texture containing rendered CoA
uniform sampler2D frameMaskSampler;     // Frame mask (white = show CoA, black = transparent)
uniform sampler2D texturedMaskSampler;  // Material/dirt texture (coa_mask_texture.png)
uniform sampler2D noiseMaskSampler;     // Noise texture (noise.png)
uniform sampler2D pickerTextureSampler;   // Picker texture (for highlighting)
uniform vec2 mouseUV;                  // Mouse UV coordinates for picker highlight
uniform vec2 coaScale;                  // Scale for CoA sampling (default 0.9, Asian frames ~1.0)
uniform vec2 coaOffset;                 // Offset for CoA sampling (default 0.0, 0.04)
uniform float bleedMargin;              // Bleed margin factor (1.0 = no bleed, >1.0 = shrink CoA for edge bleed)

void main() {
	// Apply bleed margin, scale, and offset to CoA texture coordinates
	// First scale around center (0.5, 0.5), then apply offset
	vec2 centeredUV = vTexCoord - 0.5;
	centeredUV /= (coaScale / bleedMargin);  // Apply both scale and bleed margin
	vec2 coaUV = centeredUV + 0.5; // Recenter

	coaUV -= coaOffset; // Apply offset after scaling
	// Clamp UVs to [0, 1] with a small inset to bleed the edges out to avoid layering artifacts
	float inset = 0.01;
	coaUV = clamp(coaUV, inset, 1.0 - inset); // Clamp to valid UV range with inset	
	// Sample the rendered CoA texture
	vec4 coaColor = texture(coaTextureSampler, coaUV);
	
	// Apply noise and material texture using the transformed viewport UV
	// This ensures noise/material follow the frame mask, not the clamped CoA
	vec2 screenUV = vTexCoord;
	screenUV.y = 1.0 - screenUV.y;  // Flip Y
	
	// Apply material mask (dirt/texture) - blue channel
	vec4 materialSample = texture(texturedMaskSampler, screenUV);
	coaColor.rgb = mix(coaColor.rgb, coaColor.rgb * materialSample.b, 0.5);
	
	// Apply noise grain
	float noise = texture(noiseMaskSampler, screenUV).r;
	coaColor.rgb = mix(coaColor.rgb, coaColor.rgb * noise, 0.2);
	
	// Sample frame mask (flip V coordinate)
	vec2 spreadUV = screenUV;
	spreadUV -= 0.5;
	spreadUV /= 1.05; // Apply same scale as CoA
	spreadUV += 0.5;
	float frameMask = texture(frameMaskSampler, spreadUV).a;
	
	if(mouseUV.x > 0.0){
		// Flip Y coordinate when sampling picker texture (OpenGL framebuffer to texture coordinate conversion)
		vec2 flippedCoAUV = vec2(coaUV.x, 1.0 - coaUV.y);
		
		// Sample picker texture at mouse and current UV
		vec3 pickerSample = texture(pickerTextureSampler, mouseUV).rgb;
		vec3 pickerTexture = texture(pickerTextureSampler, flippedCoAUV).rgb;
		
		// Check if picker color at mouse is not black (no layer)
		float value = max(max(pickerSample.r, pickerSample.g), pickerSample.b);
		
		// Compare the two picker ID colors (not visual colors)
		float colorDiff = distance(pickerSample, pickerTexture);
		
		// If same layer ID and not black, highlight
		if(colorDiff < 0.001 && value > 0.01)
		{
			// Multi-sample edge detection for better border at 512x512 resolution
			vec2 texelSize = 1.0 / textureSize(pickerTextureSampler, 0);
			float borderWidth = 2.0; // pixels
			
			// Sample 4 neighbors for edge detection
			vec3 pickerRight = texture(pickerTextureSampler, flippedCoAUV + vec2(texelSize.x * borderWidth, 0.0)).rgb;
			vec3 pickerLeft = texture(pickerTextureSampler, flippedCoAUV - vec2(texelSize.x * borderWidth, 0.0)).rgb;
			vec3 pickerUp = texture(pickerTextureSampler, flippedCoAUV + vec2(0.0, texelSize.y * borderWidth)).rgb;
			vec3 pickerDown = texture(pickerTextureSampler, flippedCoAUV - vec2(0.0, texelSize.y * borderWidth)).rgb;
			
			// Check if any neighbor is different color (edge detection)
			bool isEdge = distance(pickerTexture, pickerRight) > 0.001 ||
			              distance(pickerTexture, pickerLeft) > 0.001 ||
			              distance(pickerTexture, pickerUp) > 0.001 ||
			              distance(pickerTexture, pickerDown) > 0.001;
			
			// Border or fill effect based on edge detection
			if(isEdge) {
				// At border - bright blue outline
				coaColor.rgb = mix(coaColor.rgb, vec3(0.6, 0.9, 1.0), 1.0);
			} else {
				// Interior - subtle blue overlay
				vec3 blueOverlay = vec3(0.3, 0.5, 1.0);
				coaColor.rgb = mix(coaColor.rgb, blueOverlay, 0.3);
			}
			
			// Contrast adjustment
			float contrast = 1.15;
			coaColor.rgb = ((coaColor.rgb - 0.5) * contrast) + 0.5;
		}
	}

	// Apply mask to CoA alpha
	//if you come here thinking the frameMask needs to be multiplied to coaColor.a you're wrong
	FragColor = vec4(coaColor.rgb, frameMask);
}
