#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D textureSampler;
uniform sampler2D coaMaskSampler;

uniform vec3 primaryColor;
uniform vec3 secondaryColor;
uniform vec3 tertiaryColor;
uniform vec2 viewportSize;

void main()
{
	vec4 textureMask=texture(textureSampler,vTexCoord);
	vec3 outputColour=vec3(0.);
	outputColour=mix(primaryColor,secondaryColor,textureMask.g);
	outputColour=mix(outputColour,tertiaryColor,textureMask.r);
	
	// Use screen-space coordinates for mask (0-1 range, centered)
	vec2 maskCoord = 1.0-(gl_FragCoord.xy / viewportSize);
	maskCoord-=.5;// Center the coordinates
	maskCoord*=1.6;// Scale to cover more area
	maskCoord+=.5;// Re-center the coordinates
	vec4 maskSample = texture(coaMaskSampler,maskCoord);
	// Use max of RGB channels or alpha, whichever has data
	float coaMaskValue = max(max(maskSample.r, maskSample.g), max(maskSample.b, maskSample.a));
	
	FragColor=vec4(outputColour*textureMask.b,textureMask.a*coaMaskValue);
}
