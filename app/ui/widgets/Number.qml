import QtQuick
import QtQuick.Controls

// 统一样式的数字输入框（时/分）：圆角浅白底，右侧上下小箭头
SpinBox {
    id: root

    implicitHeight: 36
    implicitWidth: 92
    font.pixelSize: 13
    editable: true

    contentItem: TextInput {
        text: root.textFromValue(root.value, root.locale)
        font: root.font
        color: root.enabled ? "#1d1d1f" : "#a1a1a6"
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        readOnly: !root.editable
        validator: root.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        selectionColor: Backend.accent
        selectedTextColor: "#ffffff"
    }

    up.indicator: Item {
        x: root.width - 26
        y: 4
        width: 20
        height: (root.height - 8) / 2
        Text {
            anchors.centerIn: parent
            text: "\uE70E"
            font.family: "Segoe MDL2 Assets"
            font.pixelSize: 8
            color: root.up.pressed ? Backend.accent : "#86868b"
        }
    }

    down.indicator: Item {
        x: root.width - 26
        y: 4 + (root.height - 8) / 2
        width: 20
        height: (root.height - 8) / 2
        Text {
            anchors.centerIn: parent
            text: "\uE70D"
            font.family: "Segoe MDL2 Assets"
            font.pixelSize: 8
            color: root.down.pressed ? Backend.accent : "#86868b"
        }
    }

    background: Rectangle {
        radius: 10
        color: root.enabled ? Qt.rgba(1, 1, 1, 0.88) : Qt.rgba(1, 1, 1, 0.45)
        border.width: root.activeFocus ? 1.5 : 1
        border.color: root.activeFocus
                      ? Qt.rgba(Backend.theme.r, Backend.theme.g, Backend.theme.b, 0.35)
                      : (hov.hovered ? Qt.rgba(0, 0, 0, 0.18) : Qt.rgba(0, 0, 0, 0.10))
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }

    HoverHandler { id: hov }
}
