#version 330 core

in vec2 fragUV;
out vec4 FragColor;

uniform sampler2D emblemMaskSampler;        // 8192×8192 emblem atlas with 1024 tiles (32×32 grid, 256×256 per tile)
uniform sampler2D patternMaskSampler;       // 8192×8192 pattern atlas with 1024 tiles (32×32 grid, 256×256 per tile)

uniform uvec2 emblemTileIndex;  // Emblem tile index in 32×32 grid
uniform int patternFlag; // Flag to enable pattern overlay
uniform uvec2 patternTileIndex; // Pattern tile index in 32×32 grid

uniform vec3 indexColor; // Emblem picker index color

void main()
{
	// Calculate emblem tile bounds from tile index (32×32 grid)
	const float emblemTileSize = 1.0 / 32.0;  // 0.03125 for 32×32 grid
	vec2 emblemTileMin = vec2(emblemTileIndex) * emblemTileSize;
	vec2 emblemTileMax = emblemTileMin + emblemTileSize;
	
	// Inset by ~0.8 pixels at 8192 resolution to avoid edge bleeding
	float emblemInset = 0.0001;
	vec2 emblemClampMin = emblemTileMin + emblemInset;
	vec2 emblemClampMax = emblemTileMax - emblemInset;
	
	// Map per-instance UV (0-1) to emblem tile in atlas
	vec2 emblemAtlasUV = mix(emblemTileMin, emblemTileMax, fragUV);
	emblemAtlasUV = clamp(emblemAtlasUV, emblemClampMin, emblemClampMax);
	
	vec4 textureMask = texture(emblemMaskSampler, emblemAtlasUV);
	// Calculate CoA UV from fragment coords (512×512 RTT framebuffer)
	vec2 coaUV = gl_FragCoord.xy / vec2(512.0, 512.0);
	coaUV.y = 1.0 - coaUV.y;  // Flip Y (OpenGL bottom-up to texture top-down)
	
	// Calculate pattern tile bounds from tile index (32×32 grid)
	const float tileSize = 1.0 / 32.0;  // 0.03125 for 32×32 grid
	vec2 tileMin = vec2(patternTileIndex) * tileSize;
	vec2 tileMax = tileMin + tileSize;
	
	// Inset by ~0.8 pixels at 8192 resolution to avoid edge bleeding
	float inset = 0.0001;
	vec2 clampMin = tileMin + inset;
	vec2 clampMax = tileMax - inset;
	
	// Map coaUV to pattern atlas space and clamp
	vec2 patternCoord = mix(tileMin, tileMax, coaUV);
	patternCoord = clamp(patternCoord, clampMin, clampMax);
	
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
