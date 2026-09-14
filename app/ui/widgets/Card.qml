import QtQuick
import QtQuick.Layouts

// 设置项卡片：白色玻璃圆角块。
// 使用方把内容（如 ColumnLayout/GridLayout）设为子项并用 anchors.margins: 18 贴合，
// 卡片高度由子项的 implicitHeight 自动推出。
Rectangle {
    id: root

    // Layout 会把子项的隐式宽度当成最小宽度；显式清零，避免卡片内容把卡片撑宽导致横向溢出
    implicitWidth: 0
    Layout.minimumWidth: 0

    implicitHeight: {
        var h = 0
        for (var i = 0; i < children.length; i++) {
            var c = children[i]
            if (c.implicitHeight !== undefined && c.implicitHeight > 0)
                h = Math.max(h, c.implicitHeight + 36)
        }
        return h > 0 ? h : 80
    }

    property Item backdrop: null
    readonly property bool fancy: Backend.fancyUi


    radius: 16
    color: fancy ? "transparent" : Qt.rgba(1, 1, 1, 0.82)
    border.width: fancy ? 0 : 1
    border.color: Qt.rgba(1, 1, 1, 0.95)

    GlassSurface {
        visible: root.fancy
        anchors.fill: parent
        radius: root.radius
        edge: 18
        aberration: 1.1
        tint: 0.26
        refreshMs: 150
        backdrop: root.backdrop
        z: -1
    }
}
