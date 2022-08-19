#version 430
layout(local_size_x = 16, local_size_y = 16) in;
//layout(rgba32f, binding = 0) uniform image2D img_output;
layout(rgba8, location=0) writeonly uniform image2D destTex;

struct Player {
    vec3 pos;
    float scale;
};

#define PLAYER_COUNT 1

uniform vec2 windowSize;
uniform vec3 cameraPos;
uniform mat3 cameraMatrix;
uniform float speedScale;
uniform float time;
uniform Player[PLAYER_COUNT] players;

#define PI 3.1415926538

#define MIN_DISTANCE_MULTIPLIER 0.0001

vec4 scale(float factor, vec4 pos) {
    return pos / factor;
}

vec4 scaleDown(float factor, vec4 pos) {
    return pos * factor;
}

vec4 translate(vec3 translation, vec4 pos) {
    return pos - vec4(translation, 0.0);
}

vec4 mirrorX(vec4 pos) {
    return vec4(abs(pos.x), pos.yzw);
}

vec4 mirrorY(vec4 pos) {
    return vec4(pos.x, abs(pos.y), pos.zw);
}

vec4 mirrorZ(vec4 pos) {
    return vec4(pos.xy, abs(pos.z), pos.w);
}

vec4 rotateXY(float angle, vec4 pos) {
    return vec4(cos(angle)*pos.x+sin(angle)*pos.y, cos(angle)*pos.y-sin(angle)*pos.x, pos.z, pos.w);
}

vec4 rotateXZ(float angle, vec4 pos) {
    return vec4(cos(angle)*pos.x+sin(angle)*pos.z, pos.y, cos(angle)*pos.z-sin(angle)*pos.x, pos.w);
}

vec4 rotateYZ(float angle, vec4 pos) {
    return vec4(pos.x, cos(angle)*pos.y+sin(angle)*pos.z, cos(angle)*pos.z-sin(angle)*pos.y, pos.w);
}

vec4 repeatX(float width, vec4 pos) {
    return vec4(mod(pos.x + 0.5*width, width) - 0.5*width, pos.yzw);
}

vec4 repeatY(float width, vec4 pos) {
    return vec4(pos.x, mod(pos.y + 0.5*width, width) - 0.5*width, pos.zw);
}

vec4 repeatZ(float width, vec4 pos) {
    return vec4(pos.xy, mod(pos.z + 0.5*width, width) - 0.5*width, pos.w);
}

vec4 none(vec4 pos) {
    return pos;
}

float expand(float radius, float distance) {
    return distance - radius;
}

vec4 mengerFold(vec4 pos) {
    if (pos.x+pos.y<0) {pos.xy =- pos.yx;}
    if (pos.x+pos.z<0) {pos.xz =- pos.zx;}
    if (pos.y+pos.z<0) {pos.yz =- pos.zy;}
    return pos;
}

vec4 menger(vec4 pos) {
    return translate(vec3(2.0, 0.0, 0.0),
    mirrorX(
    translate(vec3(0.0, 2.0, 0.0),
    mirrorY(
    translate(vec3(0.0, 0.0, 1.0),
    mirrorZ(
    translate(vec3(0.0, 0.0, 1.0),
    mirrorZ(
    rotateYZ(PI/4,
    mirrorZ(
    rotateYZ(PI/4,
    mirrorY(
    mirrorZ(
    rotateXZ(PI/4,
    mirrorZ(
    rotateXZ(PI/4,
    mirrorX(
    mirrorZ(
    scale(1.0/3.0, pos
    )))))))))))))))))));
}

float de_sphere(vec4 pos) {
    return (distance(pos.xyz, vec3(0.0)) - 1) / pos.w;
}

float de_cube(vec4 pos) {
    return (length(max(abs(pos.xyz) - 1.0, 0.0)) / pos.w);// - min(max(pos.x, max(pos.y, pos.z)), 0.0));
}

/*float de(vec4 pos) {
    return de_sphere(menger(pos));
    return de_cube(menger(menger(menger(menger(menger(menger(menger(menger(pos)))))))));
}*/

//PutDEHere

vec3 ray(vec3 start, vec3 direction) {
    float length = 0;
    bool hit = false;
    vec3 point;
    float dist;
    float counter = 0.0;
    float min_dist = 1000000.0;
    while (length < 1000000 && counter < 1000) {
        point = start + direction * length;
        dist = de(vec4(point, 1.0));
        if (dist < (MIN_DISTANCE_MULTIPLIER*min(max(length, 0.0001), 1))) {
            hit = true;
            break;
        }
        length += dist;
        counter += 1.0;
        min_dist = min(dist, min_dist);
    }

    if (hit) {
        //return ((point + 1) / 2) / counter * 10;
        //vec3 pos = floor((point + 1) * pow(3, 9) / 2);
        //return vec3(mod(pos.x+pos.y+pos.z, 2), 1.0, counter/100) / counter * 10;
        return vec3(0.0, 1.0, counter/100) / counter * 10;
    } else {
        //return vec3(0.5, 0.5, 0.8);
        //return vec3(0.0, 0.0, 1000000/length);
        return vec3(0.0, 0.0, counter/100);
    }

}

void main() {
    vec4 pixel = vec4(0.0, 1.0, 0.0, 1.0);
    ivec2 pixel_coords = ivec2(gl_GlobalInvocationID.xy);
/*
    vec2 point = pixel_coords / windowSize.x;
    point = 2 * point - vec2(1.0, windowSize.y/windowSize.x);
*/
    vec2 point = (pixel_coords * 2 - windowSize) / windowSize.x;
    //point.y = -point.y;
    vec3 rayFromCamera = vec3(point, -1.0);

    /*vec3 rayOrigin = (cameraMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
    vec3 rayOffset = (cameraMatrix * vec4(rayFromCamera, 0.0)).xyz;

    vec3 rayDirection = rayOffset - rayOrigin;*/
    rayFromCamera = normalize(rayFromCamera);
    vec3 rayDirection = cameraMatrix * rayFromCamera;

    //pixel.rg = point;
    //pixel.rgb = ray(vec3(point, -5.0), vec3(0.0, 0.0, 1.0));
    //pixel.rgb = ray(cameraPos, normalize(rayDirection));
    pixel.rgb = ray(cameraPos, normalize(rayDirection));

    imageStore(destTex, pixel_coords, pixel);
}