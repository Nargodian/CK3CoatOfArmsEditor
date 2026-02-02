#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D emblemMaskSampler;        // 8192×8192 emblem atlas with 256 tiles (16×16 grid, 512×512 per tile)
uniform sampler2D patternMaskSampler;       // 8192×8192 pattern atlas with 256 tiles (16×16 grid, 512×512 per tile)

uniform int patternFlag; // Flag to enable pattern overlay
uniform vec4 patternUV; // Pattern atlas UV coordinates (u0, v0, u1, v1)

uniform vec3 indexColor; // Emblem picker index color

void main()
{
	vec4 textureMask = texture(emblemMaskSampler, vTexCoord);
	//generate a unique colour based on index - use exact byte values, no interpolation

	
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
	//greedy alpha
	float alpha = step(0.1, textureMask.a*patternMaskValue);
	
	// Discard transparent fragments (no blending in picker mode)
	if (alpha < 0.5) {
		discard;
	}
	
	FragColor = vec4(indexColor, 1.0);
}
