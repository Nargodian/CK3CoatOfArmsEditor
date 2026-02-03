#version 330 core

in vec2 fragUV;
out vec4 fragColor;

uniform sampler2D patternMaskSampler;  // 8192×8192 atlas with 256 tiles (16×16 grid, 512×512 per tile)
uniform vec3 color1;
uniform vec3 color2;
uniform vec3 color3;

void main()
{
	// fragUV comes from vertex shader already mapped to the correct tile in the atlas
	// via uvOffset and uvScale uniforms in quad.vert
	vec4 textureMask = texture(patternMaskSampler, fragUV);
	
	// Mix colors based on mask channels
	vec3 outputColor = vec3(0.0);
	outputColor = mix(color1, color2, textureMask.g);
	outputColor = mix(outputColor, color3, textureMask.b);
	
	fragColor = vec4(outputColor, textureMask.a);
}
