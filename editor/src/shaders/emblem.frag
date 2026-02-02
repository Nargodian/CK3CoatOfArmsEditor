#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D emblemMaskSampler;        // 8192×8192 emblem atlas with 256 tiles (16×16 grid, 512×512 per tile)
uniform sampler2D patternMaskSampler;       // 8192×8192 pattern atlas with 256 tiles (16×16 grid, 512×512 per tile)

uniform int patternFlag; // Flag to enable pattern overlay
uniform vec4 patternUV; // Pattern atlas UV coordinates (u0, v0, u1, v1)

uniform vec3 primaryColor;
uniform vec3 secondaryColor;
uniform vec3 tertiaryColor;

uniform float selectionTint; // 0.0 = no tint, 1.0 = full red tint for selected layers

// Overlay blend function (per-channel)
float overlayBlend(float base, float blend) {
	return (blend < 0.5) ? (2.0 * base * blend) : (1.0 - 2.0 * (1.0 - base) * (1.0 - blend));
}

// Apply overlay blend with strength
vec3 applyOverlay(vec3 base, vec3 blend, float strength) {
	vec3 result;
	result.r = overlayBlend(base.r, blend.r);
	result.g = overlayBlend(base.g, blend.g);
	result.b = overlayBlend(base.b, blend.b);
	return mix(base, result, strength);
}

void main()
{
	vec4 textureMask = texture(emblemMaskSampler, vTexCoord);
	vec3 outputColour = vec3(0.);
	outputColour = mix(primaryColor, secondaryColor, textureMask.g);
	outputColour = mix(outputColour, tertiaryColor, textureMask.r);
	
	// Apply blue channel as overlay shading (CK3 uses ~0.7 strength for aggressive shading)
	outputColour = applyOverlay(outputColour, vec3(textureMask.b), 0.7);
	
	// When rendering to RTT framebuffer at 512×512, fragment coords map directly to normalized space
	vec2 coaUV = gl_FragCoord.xy / vec2(512.0, 512.0);
	coaUV.y = 1.0 - coaUV.y;  // Flip Y (OpenGL bottom-up to texture top-down)
	
	// Map normalized coordinates to pattern UV atlas space for emblem-specific masking
	vec2 patternCoord = mix(patternUV.xy, patternUV.zw, coaUV);
	vec4 patternMask = texture(patternMaskSampler, patternCoord);
	// flags
	// 0 mask off
	// 1 maskR on
	// 2 maskG on
	// 3 maskR and maskG on
	// 4 maskB on
	// 5 maskR and maskB on
	// 6 maskG and maskB on
	// 7 maskR and maskG and maskB on
	float patternMaskValue = 0.0;
	bool allOrNoneSet = (patternFlag & 7) == 7 || (patternFlag & 7) == 0;

	if((patternFlag & 1) == 1 && !allOrNoneSet)
	{
		patternMaskValue = max(0.0, patternMask.r - patternMask.g);
	}
	if((patternFlag & 2) == 2 && !allOrNoneSet)
	{
		patternMaskValue += max(0.0, patternMask.g - patternMask.b);
	}
	if((patternFlag & 4) == 4 && !allOrNoneSet)
	{
		patternMaskValue += patternMask.b;
	}
	// If no valid pattern channels selected, default to full pattern
	if(allOrNoneSet)
	{
		patternMaskValue = 1.0;
	}
	// Clamp pattern mask to valid range
	patternMaskValue = clamp(patternMaskValue, 0.0, 1.0);
	
	// Apply selection tint (red overlay) if selected
	vec3 finalColor = mix(outputColour, vec3(1.0, 0.3, 0.3), selectionTint * 0.5);
	
	FragColor = vec4(finalColor, textureMask.a * patternMaskValue);
}
