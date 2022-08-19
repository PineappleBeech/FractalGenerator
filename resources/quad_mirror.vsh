 #version 330
 in vec3 in_position;
 in vec2 in_texcoord_0;
 out vec2 uv;
 void main() {
     gl_Position = vec4(in_position, 1.0);
     uv = vec2(in_texcoord_0.x, 1.0-in_texcoord_0.y);
 }