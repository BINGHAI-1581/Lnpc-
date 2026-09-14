import QtQuick

// iOS 风格开关
Item {
    id: root
    property bool checked: false
    signal toggled(bool checked)

    width: 46
    height: 28

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? "#34C759" : "#d6d8de"
        Behavior on color { ColorAnimation { duration: 180 } }
    }

    Rectangle {
        id: knob
        width: 24
        height: 24
        radius: 12
        color: "#ffffff"
        anchors.verticalCenter: parent.verticalCenter
        x: root.checked ? root.width - width - 2 : 2
        Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        anchors.fill: parent
        preventStealing: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.checked = !root.checked
            root.toggled(root.checked)
        }
    }
}
