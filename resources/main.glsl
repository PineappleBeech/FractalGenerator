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
    vec3 direction;
};

#define PLAYER_COUNT 1

uniform vec2 windowSize;
uniform vec3 cameraPos;
uniform mat3 cameraMatrix;
uniform float speedScale;
uniform float time;
uniform Player[PLAYER_COUNT] players;

#define PI 3.1415926538

#define EPSILON (0.001*speedScale)

float distanceFromObject;

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

vec4 sierpinskiFold(vec4 pos) {
    if (pos.x+pos.y<0) {pos.xy =- pos.yx;}
    if (pos.x+pos.z<0) {pos.xz =- pos.zx;}
    if (pos.y+pos.z<0) {pos.yz =- pos.zy;}
    return pos;
}

vec4 mengerFold(vec4 z) {
	float a = min(z.x - z.y, 0.0);
	z.x -= a;
	z.y += a;
	a = min(z.x - z.z, 0.0);
	z.x -= a;
	z.z += a;
	a = min(z.y - z.z, 0.0);
	z.y -= a;
	z.z += a;
    return z;
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

float de_marbleMarcher(int iterations, float angle1, float angle2, float scale, vec3 shift, vec4 pos) {
    //pos /= 6.0;
    for (int i = 0; i < iterations; i++) {
        pos.xyz = abs(pos.xyz);
        pos = rotateXY(angle1, pos);
        pos = mengerFold(pos);
        pos = rotateYZ(angle2, pos);
        pos *= scale;
        pos.xyz += shift;
    }
    pos /= 6.0;
    return de_cube(pos);
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
    while (length < 10000 && counter < 1000) {
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

    RayResult result = RayResult(start, point, length, int(counter), hit, offsetPoint, direction);
    return result;
}

float ambientOcculsion(vec3 point, vec3 normal) {
    float occulsion = 1.0;
    float step = 0.01;
    for (float i = 1; i < 4.9; i++) {
        //occulsion -= pow((step * i) - de(point + normal * (step * i)), 2.0) / i;
        occulsion -= (step * i) - de(point + normal * (step * i));
    }

    return occulsion;
}

float angleBetween(vec3 a, vec3 b) {
    return acos(dot(a, b));
}

vec3 getColour(RayResult result) {
    vec3 sunDirection = normalize(vec3(1.0, 1.0, 1.0));
    vec3 sunColour = vec3(1.5, 1.5, 1.0);

    vec3 skyColour = vec3(0.471, 0.655, 1.0);
    vec3 materialColour = vec3(0.2, 0.6, 0.0);

    vec3 colour;
    if (result.hit) {
        colour = materialColour;
        colour *= ambientOcculsion(result.point, getNormal(result.point));

        RayResult sunRay = ray(result.point, sunDirection);

        if (!sunRay.hit) {
            colour *= sunColour;
        }

    } else {
        colour = skyColour;
    }
    return colour;
}

void main() {
    vec4 pixel = vec4(0.0, 0.0, 0.0, 1.0);
    ivec2 pixel_coords = ivec2(gl_GlobalInvocationID.xy);
    vec2 point = (pixel_coords * 2 - windowSize) / windowSize.x;
    vec3 rayFromCamera = vec3(point, -1.0);
    rayFromCamera = normalize(rayFromCamera);
    vec3 rayDirection = cameraMatrix * rayFromCamera;
    rayDirection = normalize(rayDirection);
    distanceFromObject = de(cameraPos);

    RayResult result = ray(cameraPos, rayDirection);

    vec3 colour;

    colour = getColour(result);

    /*vec3 reflection;
    if (result.hit) {
        reflection = getColour(ray(result.point, reflect(rayDirection, getNormal(result.point))));
        colour = mix(colour, reflection, 0.5);
    }*/

    const int reflectionCount = 0;
    float reflectivity = 0.5;

    if (reflectionCount > 0) {
        RayResult[reflectionCount > 0 ? reflectionCount : 1] reflections;
        int bounces = 0;

        for (int i = 0; i < reflectionCount; i++) {
            if (i == 0) {
                if (result.hit) {
                    reflections[i] = ray(result.point, reflect(rayDirection, getNormal(result.point)));
                    bounces++;
                } else {
                    break;
                }
            } else {
                if (reflections[i - 1].hit) {
                    reflections[i] = ray(reflections[i - 1].point, reflect(reflections[i - 1].direction, getNormal(reflections[i - 1].point)));
                    bounces++;
                } else {
                    break;
                }
            }
        }

        if (bounces > 0) {
            vec3 reflectionColour = getColour(reflections[bounces - 1]);

            for (int i = bounces - 2; i >= 0; i--) {
                reflectionColour = mix(getColour(reflections[i]), reflectionColour, reflectivity);
            }

            colour = mix(colour, reflectionColour, reflectivity);
        }
    }

    pixel.rgb = colour;

    imageStore(destTex, pixel_coords, pixel);
}