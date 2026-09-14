import QtQuick

// 液态玻璃面板（真折射版）。
//
// 管线：背景捕获 → 调色 → 折射着色器 → 亮边 / 鼠标高光。
//
// 折射着色器（app/ui/shaders/liquidglass.frag，用 qsb 预编译成 .qsb）做的事：
// 算出面板圆角矩形的 SDF，取其梯度作为边缘法线，按"法线 × 边缘距离 × 厚度"
// 偏移背景采样坐标 —— 于是玻璃边缘会像厚玻璃一样把背后画面弯折，并带轻微色散。
// 这与网页版液态玻璃（liquid-glass-react / shuding/liquid-glass）的位移图思路一致，
// 区别是我们直接解析求得位移场，不需要预先生成位移图。
//
// 性能：背景动画很慢，因此不做每帧捕获，而是低频刷新（默认约 8 次/秒）。
Item {
    id: root

    property Item backdrop: null
    property real radius: 20
    property real tint: 0.22              // 白色雾面浓度
    property real edge: 20                // 边缘折射厚度上限（像素，实际按可用余量收敛）
    property real aberration: 1.2         // 色散强度
    property real saturate: 0.14
    property bool showSheen: true
    property bool specular: true
    // 捕获纹理向外扩出的边距（给折射留余量）。
    // 关键限制：不能超过该面板到背景边缘的可用空间——否则 sourceRect 会落到背景控件
    // 之外，Qt 用透明填充，折射采样就会采到黑色，在边缘压出一条黑带。
    readonly property real margin: {
        if (!backdrop)
            return 0
        var o = origin
        var avail = Math.min(o.x, o.y,
                             Math.max(0, backdrop.width - o.x - width),
                             Math.max(0, backdrop.height - o.y - height))
        return Math.max(0, Math.min(26, avail - 2))
    }
    property int refreshMs: 130
    property bool live: false
    property bool refraction: true        // 关闭则退化为纯调色（无折射）

    readonly property point origin: backdrop ? root.mapToItem(backdrop, 0, 0) : Qt.point(0, 0)

    // ---- 背景捕获 ----
    ShaderEffectSource {
        id: capture
        sourceItem: root.backdrop
        // 比面板大一圈：折射偏移才不会采到纹理边缘的透明内边距
        anchors.fill: parent
        anchors.margins: -root.margin
        live: root.live
        hideSource: false
        // 关键：这个 Source 自己不要绘制。它只负责把背景抓成纹理供着色器采样；
        // 一旦它自己绘制，就会在圆角玻璃底下露出一张方角矩形。
        visible: false
        sourceRect: Qt.rect(root.origin.x - root.margin, root.origin.y - root.margin,
                            root.width + root.margin * 2, root.height + root.margin * 2)

        Timer {
            interval: root.refreshMs
            running: root.visible && !root.live && root.backdrop !== null
            repeat: true
            onTriggered: capture.scheduleUpdate()
        }
    }

    // ---- 折射本体（纹理直接取 ShaderEffectSource）----
    ShaderEffect {
        id: lens
        anchors.fill: parent
        visible: root.refraction && root.backdrop !== null
        property variant src: capture
        property vector2d size: Qt.vector2d(root.width, root.height)
        property real radius: root.radius
        // 折射厚度按"可用余量"收敛：面板贴边时余量小，折射就必须弱，
        // 否则采样偏移会越出纹理有效范围而采到黑色，边缘出现黑带。
        property real thickness: Math.min(root.edge, Math.max(0, root.margin * 0.8))
        property real tint: root.tint
        property real aberration: root.aberration
        property real margin: root.margin
        property vector2d texSize: Qt.vector2d(root.width + root.margin * 2,
                                              root.height + root.margin * 2)
        fragmentShader: "../shaders/liquidglass.frag.qsb"
    }

    // 兜底底色：只在没有折射（着色器缺失或未接背景）时使用，
    // 否则会在圆角外多出一层方块。
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        visible: !root.refraction || root.backdrop === null
        color: Qt.rgba(1, 1, 1, root.tint + 0.5)
    }

    // ---- 玻璃轮廓：亮边 + 内侧细边 ----
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.62)
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, root.radius - 1)
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.16)
    }

    // ---- 顶部斜向高光 ----
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, root.radius - 1)
        visible: root.showSheen && root.refraction
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.26) }
            GradientStop { position: 0.28; color: Qt.rgba(1, 1, 1, 0.04) }
            GradientStop { position: 0.62; color: Qt.rgba(1, 1, 1, 0.0) }
            GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.08) }
        }
    }

    // ---- 跟随鼠标的柔光 ----
    Rectangle {
        visible: root.specular
        width: root.width * 0.62
        height: root.height * 0.62
        radius: width / 2
        color: "transparent"
        opacity: hover.hovered ? 0.5 : 0.0
        Behavior on opacity { NumberAnimation { duration: 220 } }
        // 钳制在面板内部：之前的写法下限是负值，光斑会溢出到面板外面，
        // 看起来就像"背景图形跑偏"（圆角并不能裁掉它）。
        x: Math.max(2, Math.min(root.width - width - 2,
                                hover.point.position.x - width / 2))
        y: Math.max(2, Math.min(root.height - height - 2,
                                hover.point.position.y - height / 2))
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.34) }
            GradientStop { position: 0.55; color: Qt.rgba(1, 1, 1, 0.05) }
            GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.0) }
        }
    }

    HoverHandler {
        id: hover
    }
}
