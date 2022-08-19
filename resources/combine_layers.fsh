 #version 330
 uniform sampler2D texture0;
 uniform sampler2D texture1;
 out vec4 fragColor;
 in vec2 uv;
 void main() {
     vec4 base_colour = texture(texture0, uv);
     vec4 overlay_colour = texture(texture1, vec2(uv.x, 1.0-uv.y));
     fragColor = base_colour * (1.0-overlay_colour.a) + overlay_colour * (overlay_colour.a);
 }