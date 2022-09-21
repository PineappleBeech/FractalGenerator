#version 430
layout(local_size_x = 16, local_size_y = 16) in;
//layout(rgba32f, binding = 0) uniform image2D img_output;
layout(rgba8, location=0) writeonly uniform image2D destTex;

struct Player {
    vec3 pos;
    float scale;
};

struct RayResult {
    vec3 start;
    vec3 end;
    float dist;
    int count;
    bool hit;
    vec3 point;
};

#define PLAYER_COUNT 1

uniform vec2 windowSize;
uniform vec3 cameraPos;
uniform mat3 cameraMatrix;
uniform float speedScale;
uniform float time;
uniform Player[PLAYER_COUNT] players;

#define PI 3.1415926538

#define EPSILON (0.0001*speedScale)

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

float de(vec3 pos) {
    return de(vec4(pos, 1.0));
}

vec3 getNormal(vec3 point) {
    float normalX = de(vec4(point + vec3(EPSILON, 0.0, 0.0), 1.0));
    float normalY = de(vec4(point + vec3(0.0, EPSILON, 0.0), 1.0));
    float normalZ = de(vec4(point + vec3(0.0, 0.0, EPSILON), 1.0));
    float normalantiX = de(vec4(point + vec3(-EPSILON, 0.0, 0.0), 1.0));
    float normalantiY = de(vec4(point + vec3(0.0, -EPSILON, 0.0), 1.0));
    float normalantiZ = de(vec4(point + vec3(0.0, 0.0, -EPSILON), 1.0));

    vec3 normal = normalize(vec3(normalX - normalantiX, normalY - normalantiY, normalZ - normalantiZ));
    return normal;
}

RayResult ray(vec3 start, vec3 direction) {
    float length = de(start);
    bool hit = false;
    vec3 point;
    float dist;
    float counter = 0.0;
    float min_dist = 1000000.0;
    vec3 colour;
    vec3 reflection;
    while (length < 1000000 && counter < 1000) {
        point = start + direction * length;
        dist = de(vec4(point, 1.0));
        if (dist < (EPSILON)) {
            hit = true;
            break;
        }
        length += dist;
        counter += 1.0;
        min_dist = min(dist, min_dist);
    }

    vec3 offsetPoint = point + getNormal(point) * EPSILON;

    RayResult result = RayResult(start, point, length, int(counter), hit, offsetPoint);
    return result;
}

vec3 getReflection(vec3 incident, vec3 normal) {
    return incident - 2 * normal * (incident * normal);
}

float ambientOcculsion(vec3 point, vec3 normal) {
    float occulsion = 1.0;
    float step = 0.01;
    for (float i = 1; i < 4.9; i++) {
        occulsion -= (step * i) - de(point + normal * (step * i));
    }

    return occulsion;
}

float angleBetween(vec3 a, vec3 b) {
    return acos(dot(a, b));
}

void main() {
    vec4 pixel = vec4(0.0, 0.0, 0.0, 1.0);
    ivec2 pixel_coords = ivec2(gl_GlobalInvocationID.xy);
    vec2 point = (pixel_coords * 2 - windowSize) / windowSize.x;
    vec3 rayFromCamera = vec3(point, -1.0);
    rayFromCamera = normalize(rayFromCamera);
    vec3 rayDirection = cameraMatrix * rayFromCamera;
    rayDirection = normalize(rayDirection);

    RayResult result = ray(cameraPos, rayDirection);

    vec3 sunDirection = normalize(vec3(1.0, 1.0, 1.0));

    vec3 colour;

    if (result.hit) {
        colour = vec3(0.0, 1.0, 0.0);

        colour *= ambientOcculsion(result.point, getNormal(result.point));

        RayResult sunRay = ray(result.point, sunDirection);

        if (sunRay.hit) {
            colour *= 0.5;
        }

        vec3 reflection = reflect(rayDirection, getNormal(result.point));
        RayResult reflectionRay = ray(result.point, reflection);
        vec3 reflectionColour;
        if (reflectionRay.hit) {
            reflectionColour = getNormal(reflectionRay.point);
            reflectionColour = vec3(0.0, 1.0, 0.0);
            reflectionColour *= ambientOcculsion(reflectionRay.point, getNormal(reflectionRay.point));
            sunRay = ray(reflectionRay.point, sunDirection);
            if (sunRay.hit) {
                reflectionColour *= 0.5;
            }
        } else {
            reflectionColour = vec3(0.0, 0.0, 1.0);
        }

        colour = mix(colour, reflectionColour, 0.5);

    } else {
        colour = vec3(0.0, 0.0, 1.0);
    }

    //colour = result.point;

    pixel.rgb = colour;

    imageStore(destTex, pixel_coords, pixel);
}