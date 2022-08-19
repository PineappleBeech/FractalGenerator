 #version 330
 uniform sampler2D texture0;
 out vec4 fragColor;
 in vec2 uv;
 void main() {
     fragColor = texture(texture0, uv);
 }