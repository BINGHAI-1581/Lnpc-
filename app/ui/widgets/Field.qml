import QtQuick
import QtQuick.Controls

// 统一样式的输入框：圆角、浅白底、聚焦时高亮描边
TextField {
    id: root

    implicitHeight: 36
    implicitWidth: 200
    font.pixelSize: 13
    color: "#1d1d1f"
    placeholderTextColor: "#a1a1a6"
    selectionColor: Backend.accent
    selectedTextColor: "#ffffff"
    leftPadding: 12
    rightPadding: 12
    verticalAlignment: TextInput.AlignVCenter

    HoverHandler { id: hov }

    background: Rectangle {
        radius: 10
        color: root.enabled ? Qt.rgba(1, 1, 1, 0.88) : Qt.rgba(1, 1, 1, 0.45)
        border.width: root.activeFocus ? 1.5 : 1
        border.color: root.activeFocus
                      ? Qt.rgba(Backend.theme.r, Backend.theme.g, Backend.theme.b, 0.35)
                      : (hov.hovered ? Qt.rgba(0, 0, 0, 0.18) : Qt.rgba(0, 0, 0, 0.10))
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }
}
