import QtQuick

// 渐变动态背景：基础纵向渐变 + 多个缓慢漂移的大半透明圆（纯 QML，稳定可靠）
Rectangle {
    id: root
    anchors.fill: parent
    radius: 18

    // 美化风格：底色更饱和、色团更强，让上层玻璃有东西可"透"
    property bool fancy: false
    property real boost: fancy ? 1.0 : 0.55

    gradient: Gradient {
        GradientStop { position: 0.0; color: root.fancy ? Backend.bgTop
                                                         : Qt.lighter(Backend.bgTop, 1.22) }
        GradientStop { position: 0.55; color: root.fancy ? Backend.bgMid
                                                          : Qt.lighter(Backend.bgMid, 1.26) }
        GradientStop { position: 1.0; color: root.fancy ? Backend.bgBottom
                                                         : Qt.lighter(Backend.bgBottom, 1.20) }
    }

    // 色团容器内缩并裁剪，保证不会画到四角圆角之外
    Item {
        anchors.fill: parent
        anchors.margins: 18
        clip: true

    // ---- 极光色团：每团由三层同心圆叠出柔边 ----
    Repeater {
        model: [
            { c: "#8fb8ff", o: 0.55 * root.boost, s: 860, x0: 0.14, y0: 0.18, sx: 0.30, sy: 0.10, p1: 23000, p2: 31000 },
            { c: "#b79cff", o: 0.48 * root.boost, s: 740, x0: 0.86, y0: 0.30, sx: 0.22, sy: 0.16, p1: 27000, p2: 21000 },
            { c: "#7fdcb8", o: 0.34 * root.boost, s: 640, x0: 0.55, y0: 0.85, sx: 0.34, sy: 0.08, p1: 33000, p2: 25000 },
            { c: "#ffb3d1", o: 0.30 * root.boost, s: 560, x0: 0.30, y0: 0.95, sx: 0.18, sy: 0.12, p1: 29000, p2: 35000 },
            { c: "#9ecdff", o: 0.42 * root.boost, s: 800, x0: 0.95, y0: 0.90, sx: 0.26, sy: 0.14, p1: 25000, p2: 37000 }
        ]
        delegate: Item {
            id: blob
            required property var modelData
            width: modelData.s
            height: modelData.s
            x: parent.width * modelData.x0 - modelData.s * 0.5 + blob.w1
            y: parent.height * modelData.y0 - modelData.s * 0.5 + blob.w2

            property real w1: 0
            property real w2: 0

            SequentialAnimation {
                running: true
                loops: Animation.Infinite
                NumberAnimation { target: blob; property: "w1"; from: -modelData.sx * blob.width; to: modelData.sx * blob.width; duration: modelData.p1; easing.type: Easing.InOutSine }
                NumberAnimation { target: blob; property: "w1"; from: modelData.sx * blob.width; to: -modelData.sx * blob.width; duration: modelData.p1; easing.type: Easing.InOutSine }
            }
            SequentialAnimation {
                running: true
                loops: Animation.Infinite
                NumberAnimation { target: blob; property: "w2"; from: -modelData.sy * blob.height; to: modelData.sy * blob.height; duration: modelData.p2; easing.type: Easing.InOutSine }
                NumberAnimation { target: blob; property: "w2"; from: modelData.sy * blob.height; to: -modelData.sy * blob.height; duration: modelData.p2; easing.type: Easing.InOutSine }
            }

            // 三层同心圆叠出柔和边缘
            Repeater {
                model: [
                    { k: 1.00, a: modelData.o * 0.16 },
                    { k: 0.78, a: modelData.o * 0.20 },
                    { k: 0.55, a: modelData.o * 0.22 }
                ]
                delegate: Rectangle {
                    required property var modelData
                    property real blobW: blob.width
                    width: blobW * modelData.k
                    height: width
                    radius: width / 2
                    anchors.centerIn: parent
                    color: blob.modelData.c
                    opacity: modelData.a
                }
            }
        }
    }
    }
}
