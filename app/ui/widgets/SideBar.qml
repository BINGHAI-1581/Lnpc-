import QtQuick

// 左侧选项卡导航栏
Item {
    id: root
    property int currentIndex: 0
    property string loginState: "未登录"
    property bool loggedIn: false
    signal navClicked(int index)

    width: 216

    property Item backdrop: null
    readonly property bool fancy: Backend.fancyUi

    // 白底：左上/左下取圆角，右侧保持直边（用补块覆盖右半部分）
    readonly property int shellRadius: 18

    Rectangle {
        visible: !root.fancy
        anchors.fill: parent
        radius: root.shellRadius
        color: "#ffffff"
    }
    Rectangle {
        visible: !root.fancy
        x: root.shellRadius
        y: 0
        width: parent.width - root.shellRadius
        height: parent.height
        color: "#ffffff"
    }
    Rectangle {
        // 右侧分隔细线
        visible: !root.fancy
        anchors.right: parent.right
        width: 1
        height: parent.height
        color: Qt.rgba(0, 0, 0, 0.06)
    }


    // 美化风格：与背景做真实模糊的玻璃导航栏    // 美化风格：与背景做真实模糊的玻璃导航栏
    GlassSurface {
        visible: root.fancy
        anchors.fill: parent
        anchors.margins: 6
        radius: 20
        tint: 0.30
        backdrop: root.backdrop
    }

    Column {
        anchors.top: parent.top
        anchors.topMargin: 28
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4

        // 品牌
        Item {
            width: parent.width
            height: 52

            Rectangle {
                id: logo
                width: 36; height: 36; radius: 10
                anchors.left: parent.left; anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                gradient: Gradient {
                    GradientStop { position: 0; color: Backend.accent }
                    GradientStop { position: 1; color: Qt.lighter(Backend.accent, 1.14) }
                }
                Text {
                    anchors.centerIn: parent
                    text: "课"; color: "#fff"
                    font.pixelSize: 18; font.weight: Font.Bold
                }
            }
            Text {
                anchors.left: logo.right; anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "课程推送助手"
                font.pixelSize: 16; font.weight: Font.DemiBold
                color: "#1d1d1f"
            }
        }

        Item { width: 1; height: 22 }

        Repeater {
            model: [
                { icon: "\uE821", label: "主页" },
                { icon: "\uE713", label: "设置" }
            ]
            delegate: Item {
                width: parent.width
                height: 44
                required property var modelData
                required property int index

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 8
                    radius: 12
                    color: root.currentIndex === index ? Qt.rgba(0.039,0.518,1.0,0.08) : (navArea.containsMouse ? Qt.rgba(0,0,0,0.03) : "transparent")
                    Behavior on color { ColorAnimation { duration: 140 } }
                }
                Rectangle {
                    width: 3; height: 18; radius: 1.5
                    anchors.left: parent.left; anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    color: Backend.accent
                    visible: root.currentIndex === index
                }

                Row {
                    anchors.left: parent.left; anchors.leftMargin: 24
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    Text {
                        text: modelData.icon
                        font.family: "Segoe MDL2 Assets"
                        font.pixelSize: 16
                        color: root.currentIndex === index ? Backend.accent : "#86868b"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: modelData.label
                        font.pixelSize: 14
                        font.weight: root.currentIndex === index ? Font.DemiBold : Font.Normal
                        color: root.currentIndex === index ? Backend.accent : "#1d1d1f"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                MouseArea {
                    id: navArea
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onClicked: root.navClicked(index)
                }
            }
        }
    }

    // 底部：登录状态
    Column {
        anchors.left: parent.left
        anchors.leftMargin: 24
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 22
        spacing: 4

        Row {
            spacing: 7
            Rectangle {
                width: 8; height: 8; radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: root.loggedIn ? "#34C759" : "#ff9f0a"
                SequentialAnimation on opacity {
                    running: !root.loggedIn
                    loops: Animation.Infinite
                    NumberAnimation { from: 1; to: 0.3; duration: 700 }
                    NumberAnimation { from: 0.3; to: 1; duration: 700 }
                }
            }
            Text {
                text: "校园网登录信息"
                font.pixelSize: 11
                color: "#86868b"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Text {
            text: root.loginState
            font.pixelSize: 12
            font.weight: Font.DemiBold
            color: root.loggedIn ? "#34C759" : "#ff9f0a"
        }
    }
}
