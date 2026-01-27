#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D textureSampler;
uniform sampler2D coaMaskSampler;
uniform sampler2D materialMaskSampler;
uniform sampler2D noiseSampler;

uniform vec3 primaryColor;
uniform vec3 secondaryColor;
uniform vec3 tertiaryColor;

void main()
{
	vec2 tileIndex = floor(vTexCoord * 32.0);  // Which tile in the 32x32 atlas
	vec2 tileCenter = (tileIndex + 0.5) / 32.0;  // Center of that tile in atlas coords
	vec2 scaleCoords = tileCenter + (vTexCoord - tileCenter) * 1.3;  // Scale around tile center
	vec4 textureMask=texture(textureSampler,scaleCoords);
	vec3 outputColour=vec3(0.);
	outputColour=mix(primaryColor,secondaryColor,textureMask.g);
	outputColour=mix(outputColour,tertiaryColor,textureMask.b);
	
	// When rendering to RTT framebuffer at 512×512, fragment coords map directly to normalized space
	vec2 maskCoord = gl_FragCoord.xy / vec2(512.0, 512.0);
	maskCoord.y = 1.0 - maskCoord.y;  // Flip Y (OpenGL bottom-up to texture top-down)

	vec4 maskSample = texture(coaMaskSampler, maskCoord);
	// Use max of RGB channels or alpha, whichever has data
	float coaMaskValue = max(max(maskSample.r, maskSample.g), max(maskSample.b, maskSample.a));
	
	// Apply material mask using same normalized coordinates (red channel = dirt map)
	vec4 materialMask = texture(materialMaskSampler, maskCoord);
	outputColour = mix(outputColour, outputColour * materialMask.b, 0.5);
	
	// Apply noise grain for texture
	float noise = texture(noiseSampler, maskCoord).r;
	outputColour = mix(outputColour, outputColour * noise, 0.1);
	
	FragColor=vec4(outputColour,textureMask.a*coaMaskValue);
}
