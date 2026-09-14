import QtQuick

// Apple 风格按钮：kind = primary / secondary / ghost
Rectangle {
    id: btn
    property string text: ""
    property string kind: "primary"
    property string iconGlyph: ""
    property bool busy: false
    signal clicked()

    implicitHeight: 36
    implicitWidth: row.implicitWidth + (kind === "primary" ? 36 : 28)

    radius: height / 2
    opacity: enabled ? (area.pressed ? 0.72 : 1.0) : 0.4

    readonly property color c1: kind === "primary" ? Backend.accent
                                : (kind === "danger" ? "#FF3B30"
                                : (kind === "secondary" ? "#ffffff" : "transparent"))
    readonly property color c2: kind === "primary" ? Qt.lighter(Backend.accent, 1.12)
                                : (kind === "danger" ? "#FF6A5E" : c1)

    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0.0; color: btn.c1 }
        GradientStop { position: 1.0; color: btn.c2 }
    }
    border.width: kind === "primary" ? 0 : (kind === "secondary" ? 1 : 0)
    border.color: Qt.rgba(0.039,0.518,1.0,0.33)

    scale: area.pressed ? 0.97 : 1.0
    Behavior on scale { NumberAnimation { duration: 120 } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6

        BusySpinner {
            visible: btn.busy
            size: 14
            color: "#ffffff"
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: btn.iconGlyph !== ""
            text: btn.iconGlyph
            font.family: "Segoe MDL2 Assets"
            font.pixelSize: 13
            color: (btn.kind === "primary" || btn.kind === "danger")
                   ? "#ffffff" : Backend.accent
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: btn.text
            font.family: "Microsoft YaHei UI"
            font.pixelSize: 13
            font.weight: Font.DemiBold
            color: (btn.kind === "primary" || btn.kind === "danger")
                   ? "#ffffff" : Backend.accent
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        // 按钮可能位于可滚动面板内，避免按下事件被 Flickable 抢走
        preventStealing: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (!btn.busy) btn.clicked()
    }
}
