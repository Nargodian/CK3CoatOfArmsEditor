#version 330 core

in vec2 fragUV;  // Per-instance UV from vertex shader (0-1 range)
out vec4 FragColor;

uniform sampler2D emblemMaskSampler;        // 8192×8192 emblem atlas with 1024 tiles (32×32 grid, 256×256 per tile)
uniform sampler2D patternMaskSampler;       // 8192×8192 pattern atlas with 1024 tiles (32×32 grid, 256×256 per tile)

uniform uvec2 emblemTileIndex;  // Emblem tile index in 32×32 grid
uniform int patternFlag; // Flag to enable pattern overlay
uniform uvec2 patternTileIndex; // Pattern tile index in 32×32 grid

uniform vec3 primaryColor;
uniform vec3 secondaryColor;
uniform vec3 tertiaryColor;

uniform float selectionTint; // 0.0 = no tint, 1.0 = full red tint for selected layers

const float TILE_SIZE = 1.0 / 32.0;    // 0.03125 for 32×32 grid
const float TILE_INSET = 0.0001;       // ~0.8 pixels at 8192 resolution
const vec2 RTT_SIZE = vec2(512.0);     // CoA RTT framebuffer size

// ============================================================================
// Blending Functions
// ============================================================================

float overlayBlend(float base, float blend) {
	return (blend < 0.5) 
		? (2.0 * base * blend) 
		: (1.0 - 2.0 * (1.0 - base) * (1.0 - blend));
}

vec3 applyOverlay(vec3 base, vec3 blend, float strength) {
	vec3 result = vec3(
		overlayBlend(base.r, blend.r),
		overlayBlend(base.g, blend.g),
		overlayBlend(base.b, blend.b)
	);
	return mix(base, result, strength);
}

// ============================================================================
// Atlas UV Calculation
// ============================================================================

vec2 calculateAtlasUV(vec2 localUV, uvec2 tileIndex) {
	vec2 tileMin = vec2(tileIndex) * TILE_SIZE;
	vec2 tileMax = tileMin + TILE_SIZE;
	vec2 atlasUV = mix(tileMin, tileMax, localUV);
	return clamp(atlasUV, tileMin + TILE_INSET, tileMax - TILE_INSET);
}

vec2 getCoaUV() {
	vec2 uv = gl_FragCoord.xy / RTT_SIZE;
	uv.y = 1.0 - uv.y;  // Flip Y (OpenGL bottom-up to texture top-down)
	return uv;
}

// ============================================================================
// Color Computation
// ============================================================================

vec3 computeEmblemColor(vec4 mask) {
	vec3 color = mix(primaryColor, secondaryColor, mask.g);
	color = mix(color, tertiaryColor, mask.r);
	// Blue channel = overlay shading (CK3 uses ~0.7 strength)
	// Scale strength by alpha: B extends past alpha boundary (DXT artifact),
	// so fade overlay to zero at transparent edges to prevent fringing
	return applyOverlay(color, vec3(mask.b), 0.7);
}

vec3 applySelectionTint(vec3 color, vec2 atlasUV, float alpha) {
	if (selectionTint < 0.01 || alpha < 0.01) return color;
	
	// Colors
	vec3 cageColor = vec3(1.0, 0.7, 0.7);   // Bright pink for edges + stripes
	vec3 fillColor = vec3(1.0, 0.2, 0.2);   // Red tint for fill
	
	// Diagonal stripes (screen-space for consistent width)
	vec2 screenPos = gl_FragCoord.xy;
	float stripe = fract((screenPos.x + screenPos.y) * 0.02);  // 0.02 = ~10px stripes at 512 resolution
	float stripeMask = step(0.9, stripe);  // 10% stripe width, aligned to screen diagonals
	
	stripe = fract((screenPos.x - screenPos.y) * 0.02);  // 0.02 = ~10px stripes at 512 resolution
	stripeMask = max(stripeMask, step(0.9, stripe));  // 10% stripe width, aligned to screen diagonals
	
	// Edge detection: sample 4 neighbors from emblem alpha
	vec2 texelSize = vec2(TILE_SIZE / 256.0);  // Tile is 256px in atlas
	float alphaL = texture(emblemMaskSampler, atlasUV + vec2(-texelSize.x, 0.0)).a;
	float alphaR = texture(emblemMaskSampler, atlasUV + vec2( texelSize.x, 0.0)).a;
	float alphaU = texture(emblemMaskSampler, atlasUV + vec2(0.0,  texelSize.y)).a;
	float alphaD = texture(emblemMaskSampler, atlasUV + vec2(0.0, -texelSize.y)).a;
	
	// Edge where any neighbor has significantly different alpha
	float maxDiff = max(max(abs(alpha - alphaL), abs(alpha - alphaR)),
	                    max(abs(alpha - alphaU), abs(alpha - alphaD)));
	float isEdge = step(0.1, maxDiff);
	
	// Combine: cage = stripes OR edges (both bright pink)
	float cageMask = max(stripeMask, isEdge);
	
	// Fill gets red tint, cage gets pink
	vec3 tinted = mix(color, fillColor, 0.35);        // Red fill base
	tinted = mix(tinted, cageColor, cageMask * 0.9);  // Pink cage on top
	
	return mix(color, tinted, selectionTint);
}

// ============================================================================
// Pattern Mask Calculation
// ============================================================================

float computePatternMask(vec4 patternSample) {
	// Pattern flag bits: 1=R, 2=G, 4=B
	// 0 or 7 = all channels (full mask)
	int channels = patternFlag & 7;
	
	if (channels == 0 || channels == 7) {
		return 1.0;  // No masking or all channels = full opacity
	}
	
	float mask = 0.0;
	if ((channels & 1) != 0) mask += max(0.0, patternSample.r - patternSample.g);
	if ((channels & 2) != 0) mask += max(0.0, patternSample.g - patternSample.b);
	if ((channels & 4) != 0) mask += patternSample.b;
	
	return clamp(mask, 0.0, 1.0);
}

// ============================================================================
// Main
// ============================================================================

void main() {
	// Sample emblem mask (RGB stored premultiplied by alpha)
	vec2 emblemUV = calculateAtlasUV(fragUV, emblemTileIndex);
	vec4 emblemMask = texture(emblemMaskSampler, emblemUV);
	
	// Un-premultiply all RGB to recover original mask values
	if (emblemMask.a > 0.001) {
		emblemMask.rgb *= 1.0 / emblemMask.a;
	}
	
	// Compute base color from emblem channels
	vec3 color = computeEmblemColor(emblemMask);
	
	// Sample pattern mask and compute alpha multiplier
	vec2 patternUV = calculateAtlasUV(getCoaUV(), patternTileIndex);
	vec4 patternSample = texture(patternMaskSampler, patternUV);
	float patternAlpha = computePatternMask(patternSample);
	
	// Final output
	float finalAlpha = emblemMask.a * patternAlpha;
	color = applySelectionTint(color, emblemUV, emblemMask.a);
	FragColor = vec4(color, finalAlpha);
}
