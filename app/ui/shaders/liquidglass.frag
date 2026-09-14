// 液态玻璃折射着色器（Qt 6 Vulkan 风格 GLSL，需用 qsb 预编译）。
//
// 编译命令：
//   qsb --glsl "100 es,120,310 es" --hlsl 50 --msl 12 -o liquidglass.frag.qsb liquidglass.frag
//
// 思路与网页版液态玻璃一致：用"位移"扰动背景采样坐标，让玻璃边缘像厚玻璃一样
// 弯折背后画面；再叠白色雾面、边缘高光与轻微色散。
// 不同之处：无需隐藏 Canvas 预生成位移图，直接在着色器里算圆角矩形 SDF，
// 由它的梯度得到边缘法线，法线 × 距离 × 厚度 即为采样偏移。
//
// 注意 Qt 6 的规定：专用内置量只能用 qt_TexCoord0 / qt_Matrix / qt_Opacity；
// 自定义 uniform 必须放在 std140、binding 0 的 block 里，位置在 qt_Matrix 与
// qt_Opacity 之后；采样器从 binding 1 起；输出 premultiplied。
#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float radius;        // 圆角半径（像素）
    float thickness;     // 边缘折射厚度（像素）
    float tint;          // 白色雾面浓度
    float aberration;    // 色散强度（像素）
    float margin;        // 纹理相对面板向外扩出的边距（像素）
    vec2 size;           // 面板像素尺寸
    vec2 texSize;        // 纹理尺寸 = size + 2 * margin
};

layout(binding = 1) uniform sampler2D src;

float sdRoundRect(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 px = uv * size;
    vec2 halfSize = size * 0.5;

    float d = sdRoundRect(px - halfSize, halfSize - 2.0, radius);

    float dx = sdRoundRect(px - halfSize + vec2(1.0, 0.0), halfSize - 2.0, radius) - d;
    float dy = sdRoundRect(px - halfSize + vec2(0.0, 1.0), halfSize - 2.0, radius) - d;
    vec2 n = normalize(vec2(dx, dy) + vec2(1e-5, 1e-5));

    float edge = 1.0 - smoothstep(0.0, max(thickness, 0.001), -d);
    vec2 offset = n * edge * thickness * 0.85;
    // 采样映射到"向外扩了 margin 的纹理"上，并把采样点钳制在**面板自身**的范围内：
    //  · 扩 margin 是为了避开纹理边缘那圈透明内边距（采到会变黑，边缘出现黑带）；
    //  · 再钳制回面板范围，是为了不采到面板之外——那可能是窗口外的桌面（深色）。
    // 两者结合：偏移永远落在面板自身的有效背景像素内。
    vec2 sp = px + vec2(margin) + offset;
    sp = clamp(sp, vec2(margin + 1.0), vec2(margin + size.x - 1.0, margin + size.y - 1.0));
    vec2 suv = sp / texSize;

    vec3 col;
    col.r = texture(src, suv + n * aberration / size).r;
    col.g = texture(src, suv).g;
    col.b = texture(src, suv - n * aberration / size).b;

    col = mix(col, vec3(1.0), tint);
    col += vec3(0.32) * pow(edge, 3.0);

    // 圆角遮罩（带抗锯齿）：面板外一律透明，
    // 这样底层捕获到的矩形纹理不会在四角露出方角。
    float mask = 1.0 - smoothstep(-1.5, 0.5, d);
    fragColor = vec4(col * mask, mask) * qt_Opacity;   // premultiplied
}
