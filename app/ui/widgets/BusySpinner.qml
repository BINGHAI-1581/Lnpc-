import QtQuick

// 细线旋转指示器：外圈淡色 + 旋转的高亮弧（Canvas 绘制，跨实现稳定）
Item {
    id: root
    property int size: 18
    property color color: Backend.accent
    width: size
    height: size

    Canvas {
        id: cv
        anchors.fill: parent
        antialiasing: true
        property real t: 0.0

        onTChanged: cv.requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var cx = width / 2, cy = height / 2
            var r = Math.min(width, height) / 2 - root.size / 9
            var lw = Math.max(2, root.size / 9)
            ctx.lineWidth = lw
            ctx.lineCap = "round"

            ctx.strokeStyle = Qt.rgba(root.color.r, root.color.g, root.color.b, 0.18)
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, Math.PI * 2)
            ctx.stroke()

            var start = t * Math.PI * 2
            var span = Math.PI * 0.75
            ctx.strokeStyle = root.color
            ctx.beginPath()
            ctx.arc(cx, cy, r, start, start + span)
            ctx.stroke()
        }

        RotationAnimation on t {
            from: 0; to: 1; duration: 1000
            loops: Animation.Infinite
            running: root.visible
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }
}
