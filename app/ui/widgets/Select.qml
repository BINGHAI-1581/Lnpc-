import QtQuick
import QtQuick.Controls

// 统一样式的下拉框：圆角浅白底、自绘箭头、圆角弹出面板
ComboBox {
    id: root

    implicitHeight: 36
    implicitWidth: 200
    font.pixelSize: 13
    leftPadding: 12
    rightPadding: 28

    readonly property bool open: popup.visible

    contentItem: Text {
        leftPadding: root.leftPadding
        rightPadding: root.rightPadding
        verticalAlignment: Text.AlignVCenter
        text: root.displayText
        font: root.font
        color: root.enabled ? "#1d1d1f" : "#a1a1a6"
        elide: Text.ElideRight
    }

    indicator: Text {
        x: root.width - width - 11
        y: (root.height - height) / 2
        text: "\uE70D"
        font.family: "Segoe MDL2 Assets"
        font.pixelSize: 10
        color: "#86868b"
        rotation: root.open ? 180 : 0
        Behavior on rotation { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    }

    background: Rectangle {
        radius: 10
        color: root.enabled ? Qt.rgba(1, 1, 1, 0.88) : Qt.rgba(1, 1, 1, 0.45)
        border.width: (root.activeFocus || root.open) ? 1.5 : 1
        border.color: (root.activeFocus || root.open)
                      ? Qt.rgba(Backend.theme.r, Backend.theme.g, Backend.theme.b, 0.35)
                      : (hov.hovered ? Qt.rgba(0, 0, 0, 0.18) : Qt.rgba(0, 0, 0, 0.10))
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }

    HoverHandler { id: hov }

    delegate: ItemDelegate {
        id: item
        required property var model
        required property int index
        width: root.width - 12
        height: 30
        highlighted: root.highlightedIndex === index

        contentItem: Text {
            text: {
                var m = item.model
                if (m === null || m === undefined) return ""
                if (typeof m === "string" || typeof m === "number") return String(m)
                if (m[root.textRole] !== undefined) return String(m[root.textRole])
                if (m.modelData !== undefined) return String(m.modelData)
                return String(m)
            }
            font.pixelSize: 13
            color: item.highlighted ? Backend.accent : "#1d1d1f"
            verticalAlignment: Text.AlignVCenter
            leftPadding: 8
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 7
            color: item.highlighted ? Qt.rgba(Backend.theme.r, Backend.theme.g, Backend.theme.b, 0.12) : "transparent"
        }
    }

    popup: Popup {
        y: root.height + 6
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 260)
        padding: 6

        background: Rectangle {
            radius: 12
            color: Qt.rgba(1, 1, 1, 0.98)
            border.width: 1
            border.color: Qt.rgba(0, 0, 0, 0.08)
        }

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
                contentItem: Item {
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 3
                        radius: width / 2
                        color: Qt.rgba(0, 0, 0, 0.22)
                    }
                }
                background: Item {}
            }
        }
    }
}
