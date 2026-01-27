#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D textureSampler;
uniform sampler2D coaMaskSampler;
uniform sampler2D materialMaskSampler;
uniform sampler2D noiseSampler;
uniform sampler2D patternSampler;  // Pattern texture for mask channels

uniform int patternFlag; // Flag to enable pattern overlay
uniform vec4 patternUV; // Pattern atlas UV coordinates (u0, v0, u1, v1)

uniform vec3 primaryColor;
uniform vec3 secondaryColor;
uniform vec3 tertiaryColor;

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
	vec4 textureMask=texture(textureSampler,vTexCoord);
	vec3 outputColour=vec3(0.);
	outputColour=mix(primaryColor,secondaryColor,textureMask.g);
	outputColour=mix(outputColour,tertiaryColor,textureMask.r);
	
	// Apply blue channel as overlay shading (CK3 uses ~0.7 strength for aggressive shading)
	outputColour = applyOverlay(outputColour, vec3(textureMask.b), 0.7);
	
	// When rendering to RTT framebuffer at 512×512, fragment coords map directly to normalized space
	vec2 maskCoord = gl_FragCoord.xy / vec2(512.0, 512.0);
	maskCoord.y = 1.0 - maskCoord.y;  // Flip Y (OpenGL bottom-up to texture top-down)
	
	vec4 maskSample = texture(coaMaskSampler, maskCoord);
	// Use max of RGB channels or alpha, whichever has data
	float coaMaskValue = max(max(maskSample.r, maskSample.g), max(maskSample.b, maskSample.a));
	
	// Map normalized coordinates to pattern UV atlas space
	vec2 patternCoord = mix(patternUV.xy, patternUV.zw, maskCoord);
	vec4 patternTexture = texture(patternSampler, patternCoord);
	// flags
	// 0 mask off
	// 1 maskR on
	// 2 maskG on
	// 3 maskR and maskG on
	// 4 maskB on
	// 5 maskR and maskB on
	// 6 maskG and maskB on
	// 7 maskR and maskG and maskB on
	float patternMask = 0.0;
	bool allOrNoneSet = (patternFlag & 7) == 7 || (patternFlag & 7) == 0;

	if((patternFlag & 1) == 1 && !allOrNoneSet)
	{
		patternMask = max(0.0, patternTexture.r-patternTexture.g);
	}
	if((patternFlag & 2) == 2 && !allOrNoneSet)
	{
		patternMask += max(0.0, patternTexture.g-patternTexture.b);
	}
	if((patternFlag & 4) == 4 && !allOrNoneSet)
	{
		patternMask += patternTexture.b;
	}
	// If no valid pattern channels selected, default to full pattern
	if(allOrNoneSet)
	{
		patternMask = 1.0;
	}
	// Clamp pattern mask to valid range
	patternMask = clamp(patternMask, 0.0, 1.0);
	// Apply material mask using screen-space coordinates (red channel = dirt map)
	vec4 materialMask = texture(materialMaskSampler, maskCoord);
	outputColour = mix(outputColour, outputColour * materialMask.b, 0.5);
	
	// Apply noise grain for texture
	float noise = texture(noiseSampler, maskCoord).r;
	outputColour = mix(outputColour, outputColour * noise, 0.2);
	
	FragColor=vec4(outputColour,textureMask.a*coaMaskValue*patternMask);
}
