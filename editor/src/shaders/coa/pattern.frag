#version 330 core

in vec2 vTexCoord;  // 0-1 range from basic.vert
out vec4 fragColor;

uniform sampler2D patternMaskSampler;  // 8192×8192 atlas with 1024 tiles (32×32 grid, 256×256 per tile)
uniform uvec2 tileIndex;  // Tile position in 32×32 grid
uniform vec3 color1;
uniform vec3 color2;
uniform vec3 color3;

void main()
{
	// Calculate exact tile bounds from tile index
	const float tileSize = 1.0 / 32.0;  // 0.03125 for 32×32 grid
	vec2 tileMin = vec2(tileIndex) * tileSize;
	vec2 tileMax = tileMin + tileSize;
	
	// Inset by ~0.8 pixels at 8192 resolution to avoid edge bleeding
	float inset = 0.0001;
	vec2 clampMin = tileMin + inset;
	vec2 clampMax = tileMax - inset;
	
	// Map vTexCoord (0-1 within tile) to atlas UV space and clamp
	vec2 atlasUV = mix(tileMin, tileMax, vTexCoord);
	vec2 clampedUV = clamp(atlasUV, clampMin, clampMax);
	
	vec4 textureMask = texture(patternMaskSampler, clampedUV);
	
	// Mix colors based on mask channels
	vec3 outputColor = vec3(0.0);
	outputColor = mix(color1, color2, textureMask.g);
	outputColor = mix(outputColor, color3, textureMask.b);
	
	fragColor = vec4(outputColor, textureMask.a);
}
