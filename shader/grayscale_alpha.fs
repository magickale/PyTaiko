// fragment shader
#version 330
in vec2 fragTexCoord;
uniform sampler2D texture0;
out vec4 finalColor;
uniform float ext_alpha;
void main() {
    vec4 texColor = texture(texture0, fragTexCoord);
    vec3 last_color = vec3(1.0, 253.0/255.0, (186.0*0.80)/255.0);
    // Use luminance as alpha (0.0 = transparent, 1.0 = opaque)
    float alpha = ((texColor.r + texColor.g + texColor.b)/3)*0.70;
    finalColor = vec4(last_color, alpha * ext_alpha);
}
