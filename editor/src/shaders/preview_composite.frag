#version 330 core
in vec2 fragUV;
out vec4 fragColor;

uniform sampler2D coaTextureSampler;   // RTT CoA texture
uniform sampler2D frameMaskSampler;    // Frame/preview mask
uniform sampler2D texturedMaskSampler; // Material/dirt texture (coa_mask_texture.png)
uniform sampler2D noiseMaskSampler;    // Noise texture (noise.png)
uniform vec2 coaScale;                 // CoA scale within mask (simple constant, e.g., 0.9)
uniform vec2 coaOffset;                // CoA offset within mask (simple constant, e.g., 0.0, 0.1)

void main() {
    // Apply CoA scale and offset to UV coordinates (matching composite.frag logic)
    // First scale around center, then apply offset
    vec2 centeredUV = fragUV - 0.5;
    centeredUV /= coaScale;  // Apply scale
    vec2 coaUV = centeredUV + 0.5;  // Recenter
    coaUV -= coaOffset;  // Apply offset (subtractive, matching main composite shader)
    
    // Flip Y coordinate for correct orientation
    coaUV.y = 1.0 - coaUV.y;
    
    // Sample CoA
    vec4 coaColor = texture(coaTextureSampler, coaUV);
    
    // Apply noise and material texture using screen UV (not transformed CoA UV)
    vec2 screenUV = fragUV;
    screenUV.y = 1.0 - screenUV.y;  // Flip Y
    
    // Apply material mask (dirt/texture) - blue channel
    vec4 materialSample = texture(texturedMaskSampler, screenUV);
    coaColor.rgb = mix(coaColor.rgb, coaColor.rgb * materialSample.b, 0.5);
    
    // Apply noise grain
    float noise = texture(noiseMaskSampler, screenUV).r;
    coaColor.rgb = mix(coaColor.rgb, coaColor.rgb * noise, 0.2);
    
    // Apply frame mask
    float maskValue = texture(frameMaskSampler, fragUV).a;
    fragColor = vec4(coaColor.rgb, maskValue);
}
