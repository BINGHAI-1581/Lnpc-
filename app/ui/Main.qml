import QtQuick
import QtQuick.Controls
import "widgets"

ApplicationWindow {
    id: win
    width: 1420
    height: 820
    minimumWidth: 900
    minimumHeight: 620
    visible: true
    title: "课程推送助手"
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint

    property int currentPage: 0

    // 恢复上次的窗口大小与位置
    Component.onCompleted: {
        var g = Backend.windowGeometry
        if (g && g.w) {
            win.width = g.w
            win.height = g.h
            if (g.x !== undefined && g.y !== undefined
                    && g.x > -50 && g.y > -50
                    && g.x < Screen.desktopAvailableWidth - 100
                    && g.y < Screen.desktopAvailableHeight - 100) {
                win.x = g.x
                win.y = g.y
            }
        }
    }

    // 窗口几何变化后延迟写回，避免拖动/缩放过程中频繁落盘
    Timer {
        id: geomSave
        interval: 700
        onTriggered: Backend.saveWindowGeometry(win.x, win.y, win.width, win.height)
    }
    onWidthChanged: geomSave.restart()
    onHeightChanged: geomSave.restart()
    onXChanged: geomSave.restart()
    onYChanged: geomSave.restart()

    // ================= 窗口拖动 =================
    MouseArea {
        id: titleDrag
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 46
        z: 90
        acceptedButtons: Qt.LeftButton
        property point lastPos
        onPressed: function (mouse) { lastPos = Qt.point(mouse.x, mouse.y) }
        onPositionChanged: function (mouse) {
            if (pressed && win.visibility === Window.Windowed) {
                win.x += mouse.x - lastPos.x
                win.y += mouse.y - lastPos.y
            }
        }
        onDoubleClicked: win.toggleMaximized()
    }

    function toggleMaximized() {
        if (win.visibility === Window.Maximized) win.showNormal()
        else win.showMaximized()
    }

    // ================= 边缘缩放（无边框窗口手写实现） =================
    // 每个把手记录按下时的光标全局位置与窗口几何，拖动时按差值调整
    component ResizeHandle: MouseArea {
        property int edges: 0            // Qt.LeftEdge 等按位组合
        property real sx: 0
        property real sy: 0
        property real sw: 0
        property real sh: 0
        property real sxp: 0
        property real syp: 0
        property bool active: false

        hoverEnabled: true
        onPressed: function (mouse) {
            var p = Backend.cursorPos()
            sx = p.x; sy = p.y
            sw = win.width; sh = win.height
            sxp = win.x; syp = win.y
            active = true
        }
        onReleased: active = false
        onCanceled: active = false
        onPositionChanged: function (mouse) {
            if (!active) return
            var p = Backend.cursorPos()
            var dx = p.x - sx
            var dy = p.y - sy
            var nx = sxp, ny = syp, nw = sw, nh = sh

            if (edges & Qt.LeftEdge) {
                nw = Math.max(win.minimumWidth, sw - dx)
                nx = sxp + (sw - nw)
            } else if (edges & Qt.RightEdge) {
                nw = Math.max(win.minimumWidth, sw + dx)
            }
            if (edges & Qt.TopEdge) {
                nh = Math.max(win.minimumHeight, sh - dy)
                ny = syp + (sh - nh)
            } else if (edges & Qt.BottomEdge) {
                nh = Math.max(win.minimumHeight, sh + dy)
            }

            win.x = nx
            win.y = ny
            win.width = nw
            win.height = nh
        }
    }

    readonly property int grip: 7

    ResizeHandle {
        edges: Qt.LeftEdge | Qt.TopEdge
        width: win.grip + 6; height: win.grip + 6
        anchors.left: parent.left; anchors.top: parent.top
        cursorShape: Qt.SizeFDiagCursor
        z: 95
    }
    ResizeHandle {
        edges: Qt.RightEdge | Qt.TopEdge
        width: win.grip + 6; height: win.grip + 6
        anchors.right: parent.right; anchors.top: parent.top
        cursorShape: Qt.SizeBDiagCursor
        z: 95
    }
    ResizeHandle {
        edges: Qt.LeftEdge | Qt.BottomEdge
        width: win.grip + 6; height: win.grip + 6
        anchors.left: parent.left; anchors.bottom: parent.bottom
        cursorShape: Qt.SizeBDiagCursor
        z: 95
    }
    ResizeHandle {
        edges: Qt.RightEdge | Qt.BottomEdge
        width: win.grip + 6; height: win.grip + 6
        anchors.right: parent.right; anchors.bottom: parent.bottom
        cursorShape: Qt.SizeFDiagCursor
        z: 95
    }
    ResizeHandle {
        edges: Qt.LeftEdge
        width: win.grip; anchors.left: parent.left
        anchors.top: parent.top; anchors.bottom: parent.bottom
        anchors.topMargin: win.grip + 6; anchors.bottomMargin: win.grip + 6
        cursorShape: Qt.SizeHorCursor
        z: 94
    }
    ResizeHandle {
        edges: Qt.RightEdge
        width: win.grip; anchors.right: parent.right
        anchors.top: parent.top; anchors.bottom: parent.bottom
        anchors.topMargin: win.grip + 6; anchors.bottomMargin: win.grip + 6
        cursorShape: Qt.SizeHorCursor
        z: 94
    }
    ResizeHandle {
        edges: Qt.TopEdge
        height: win.grip; anchors.top: parent.top
        anchors.left: parent.left; anchors.right: parent.right
        anchors.leftMargin: win.grip + 6; anchors.rightMargin: win.grip + 6
        cursorShape: Qt.SizeVerCursor
        z: 94
    }
    ResizeHandle {
        edges: Qt.BottomEdge
        height: win.grip; anchors.bottom: parent.bottom
        anchors.left: parent.left; anchors.right: parent.right
        anchors.leftMargin: win.grip + 6; anchors.rightMargin: win.grip + 6
        cursorShape: Qt.SizeVerCursor
        z: 94
    }

    // ================= 圆角外壳 + 渐变动态背景 =================
    Rectangle {
        id: shell
        anchors.fill: parent
        anchors.margins: 8               // 预留投影空间
        radius: 18
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.75)

        // 投影
        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 6
            radius: shell.radius
            color: Qt.rgba(0.14, 0.19, 0.28, 0.12)
            z: -2
        }

        // 内容区：自绘圆角底 + 动态背景，各页自身背景透明
        Item {
            anchors.fill: parent
            clip: true

            Rectangle {
                anchors.fill: parent
                radius: shell.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#f7f9ff" }
                    GradientStop { position: 0.55; color: "#eef2fc" }
                    GradientStop { position: 1.0; color: "#f4f0fa" }
                }
            }

            AuroraBg { id: bgLayer; anchors.fill: parent; fancy: Backend.fancyUi }

            Row {
                anchors.fill: parent

                SideBar {
                    id: sidebar
                    height: parent.height
                    backdrop: bgLayer
                    currentIndex: win.currentPage
                    loginState: Backend.loginState
                    loggedIn: Backend.loggedIn
                    onNavClicked: function (i) { win.currentPage = i }
                }

                Item {
                    width: parent.width - sidebar.width
                    height: parent.height

                    HomePage {
                        id: homePage
                        anchors.fill: parent
                        visible: win.currentPage === 0
                        backend: Backend
                        backdrop: bgLayer
                        onRequestSettings: win.currentPage = 1
                    }

                    SettingsPage {
                        id: settingsPage
                        anchors.fill: parent
                        visible: win.currentPage === 1
                        backend: Backend
                        backdrop: bgLayer
                    }
                }
            }
        }

        // 圆角描边（覆盖在内容之上，保证四角干净）
        Rectangle {
            anchors.fill: parent
            radius: shell.radius
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(0, 0, 0, 0.07)
            z: 60
        }
    }

    // ================= 窗口控制按钮 =================
    Row {
        anchors.top: shell.top
        anchors.right: shell.right
        anchors.topMargin: 10
        anchors.rightMargin: 12
        spacing: 6
        z: 100

        Repeater {
            model: [
                { glyph: "\uE921", tip: "最小化", hover: Qt.rgba(0, 0, 0, 0.08), fg: "#6e6e73" },
                { glyph: "\uE922", tip: "最大化", hover: Qt.rgba(0, 0, 0, 0.08), fg: "#6e6e73" },
                { glyph: "\uE8BB", tip: "关闭到托盘", hover: "#e81123", fg: "#ffffff" }
            ]

            delegate: Rectangle {
                required property var modelData
                required property int index
                width: 26; height: 26; radius: 13
                color: area.containsMouse ? modelData.hover : "transparent"
                Behavior on color { ColorAnimation { duration: 120 } }

                Text {
                    anchors.centerIn: parent
                    text: modelData.glyph
                    font.family: "Segoe MDL2 Assets"
                    font.pixelSize: 10
                    color: area.containsMouse ? modelData.fg : "#6e6e73"
                }
                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (index === 0) Backend.hideWindow()
                        else if (index === 1) win.toggleMaximized()
                        else Backend.hideWindow()
                    }
                }
            }
        }
    }

    // ================= 提示 toast =================
    Rectangle {
        id: toast
        property string text: ""
        anchors.bottom: shell.bottom
        anchors.bottomMargin: 26
        anchors.horizontalCenter: shell.horizontalCenter
        width: toastText.implicitWidth + 36
        height: 38
        radius: 19
        color: Qt.rgba(0.17, 0.17, 0.17, 0.93)
        opacity: 0
        z: 200

        Text {
            id: toastText
            anchors.centerIn: parent
            text: toast.text
            color: "#fff"
            font.pixelSize: 13
        }

        SequentialAnimation on opacity {
            id: toastAnim
            NumberAnimation { to: 1; duration: 180 }
            PauseAnimation { duration: 2400 }
            NumberAnimation { to: 0; duration: 300 }
        }
    }

    Connections {
        target: Backend
        function onLoginDone(ok, msg) {
            toast.text = msg
            toastAnim.restart()
        }
        function onSendDone(ok, msg) {
            toast.text = msg
            toastAnim.restart()
        }
    }

    // 启动时的自动登录由 main.py 调用 Backend.startup()，此处不重复触发
}
