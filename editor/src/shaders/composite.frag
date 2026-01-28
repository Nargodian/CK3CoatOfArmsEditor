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
	
	// Apply mask to CoA alpha
	FragColor = vec4(coaColor.rgb, frameMask);
}
