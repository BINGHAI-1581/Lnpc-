import QtQuick
import QtQuick.Controls

// 统一样式的滚动条：细圆条、留内边距，不贴窗口边缘（避免切到圆角）
ScrollBar {
    id: root

    // 必须给出 implicitWidth/Height，否则 Basic 样式下滚动条宽度会退化为 0 而不显示
    contentItem: Item {
        implicitWidth: 13
        implicitHeight: 13

        Rectangle {
            anchors.fill: parent
            anchors.margins: 3
            radius: Math.min(width, height) / 2
            color: root.pressed
                   ? Qt.rgba(0, 0, 0, 0.45)
                   : (root.hovered || root.active
                      ? Qt.rgba(0, 0, 0, 0.34)
                      : Qt.rgba(0, 0, 0, 0.22))
            Behavior on color { ColorAnimation { duration: 160 } }
        }
    }

    background: Item {}
}
