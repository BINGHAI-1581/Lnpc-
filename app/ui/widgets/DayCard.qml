import QtQuick
import QtQuick.Controls

// 单日课程卡片（窄列形态，用于七天横向平铺）
Rectangle {
    id: card
    property var dayData: ({})
    property bool isToday: false
    property bool deleteMode: false

    signal deleteRequested(string date, string name, int secStart)
    signal courseRightClicked(var course, string dateLabel, string dayLabel)
    signal emptyRightClicked(string date, int day)
    signal swapRequested(string date, string nameA, int secA, string nameB, int secB)

    property Item backdrop: null
    readonly property bool fancy: Backend.fancyUi

    radius: 16
    color: fancy ? "transparent"
                  : (isToday ? Qt.rgba(1, 1, 1, 0.92) : Qt.rgba(1, 1, 1, 0.72))
    border.width: fancy ? 0 : (isToday ? 1.5 : 1)
    border.color: isToday ? Qt.rgba(0.039, 0.518, 1.0, 0.38) : Qt.rgba(1, 1, 1, 0.9)

    // 美化风格：整块卡片就是一片玻璃
    GlassSurface {
        visible: card.fancy
        anchors.fill: parent
        radius: card.radius
        edge: 16
        aberration: 1.0
        tint: card.isToday ? 0.30 : 0.24
        refreshMs: 140
        backdrop: card.backdrop
        z: -1
    }



    // 拖动落点：返回鼠标 y 位置对应的课程（按各行的实际位置判断）
    function dropTargetAt(contentY, excludeIndex) {
        var best = null
        var bestDist = 1e9
        for (var i = 0; i < coursesColumn.children.length; i++) {
            var child = coursesColumn.children[i]
            if (!child || child.modelData === undefined)
                continue
            if (child.index === excludeIndex)
                continue
            var mid = child.y + child.height / 2
            var d = Math.abs(mid - contentY)
            if (d < bestDist) {
                bestDist = d
                best = child.modelData
            }
        }
        return best
    }

    // 美化风格下"今天"的描边
    Rectangle {
        visible: card.fancy && card.isToday
        anchors.fill: parent
        radius: card.radius
        color: "transparent"
        border.width: 1.5
        border.color: Qt.rgba(Backend.theme.r, Backend.theme.g, Backend.theme.b, 0.35)
        z: 3
    }

    // 柔和投影：垫在玻璃**下面**（z 比玻璃更低），并向外溢出一点，
    // 这样阴影只在卡片外侧一圈可见，不会在卡片内部压出偏移的暗块。
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 3
        anchors.bottomMargin: -4
        anchors.leftMargin: -1
        anchors.rightMargin: -1
        radius: card.radius + 1
        color: Qt.rgba(0.14, 0.19, 0.28, 0.10)
        z: -2
    }

    Column {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 3

        Row {
            width: parent.width
            spacing: 6

            Text {
                text: card.dayData.dayLabel || ""
                font.pixelSize: 15
                font.weight: Font.Bold
                color: card.isToday ? Backend.accent : "#1d1d1f"
                anchors.verticalCenter: parent.verticalCenter
            }
            Rectangle {
                visible: card.isToday
                width: 30
                height: 16
                radius: 8
                color: Backend.accent
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    anchors.centerIn: parent
                    text: "今天"
                    color: "#fff"
                    font.pixelSize: 9
                    font.weight: Font.DemiBold
                }
            }
        }

        Row {
            width: parent.width
            spacing: 4

            Text {
                text: card.dayData.dateLabel || ""
                font.pixelSize: 11
                color: "#86868b"
            }
            Item { width: 1; height: 1; LayoutMirroring.enabled: false }
            Text {
                visible: card.dayData.weekNum > 0
                text: card.dayData.weekNum > 0 ? ("第" + card.dayData.weekNum + "周") : ""
                font.pixelSize: 10
                color: "#a1a1a6"
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(0, 0, 0, 0.06)
            anchors.topMargin: 5
        }
    }

    // 课程列表（超出可滚动）
    ScrollPane {
        id: listView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.bottomMargin: 10
        anchors.topMargin: 8
        barWidth: 10

        Column {
            id: coursesColumn
            width: parent ? parent.width : 0
            spacing: 9

            Text {
                visible: !card.dayData.courses || card.dayData.courses.length === 0
                width: parent.width
                text: "无课"
                font.pixelSize: 12
                color: "#b0b0b5"
                horizontalAlignment: Text.AlignHCenter
                topPadding: 6
            }

            Repeater {
                model: card.dayData.courses || []
                delegate: Item {
                    id: rowItem
                    required property var modelData
                    required property int index

                    // 果冻动画：先挤压回弹，再塌缩消失，最后真正删除
                    property real shrink: 0
                    property bool deleting: false

                    width: parent.width
                    height: Math.max(0, rowCol.implicitHeight * (1 - shrink))
                    opacity: 1 - shrink * 0.9
                    clip: true

                    signal removeMe()

                    transform: Scale {
                        id: rowScale
                        origin.x: rowItem.width / 2
                        origin.y: rowItem.height / 2
                    }

                    Column {
                        id: rowCol
                        width: parent.width
                        spacing: 2

                        Row {
                            width: parent.width
                            spacing: 6

                            Rectangle {
                                width: 3
                                height: 13
                                radius: 1.5
                                anchors.top: parent.top
                                anchors.topMargin: 2
                                // 按考核类型统一着色：考试红 / 考查黄 / 实训绿（其它为中性灰）
                                color: modelData.typeColor && modelData.typeColor !== ""
                                       ? modelData.typeColor : "#AFB6C2"
                            }

                            Text {
                                text: modelData.name || ""
                                width: parent.width - 20
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                color: "#1d1d1f"
                                wrapMode: Text.Wrap
                                maximumLineCount: 3
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 4
                            leftPadding: 9

                            Text {
                                text: modelData.timeText || modelData.secText || ""
                                font.pixelSize: 10
                                color: "#6e6e73"
                            }
                            Rectangle {
                                visible: !!(modelData.examType)
                                width: examText.implicitWidth + 10
                                height: 13
                                radius: 6.5
                                color: Qt.rgba(0, 0, 0, 0.05)
                                Text {
                                    id: examText
                                    anchors.centerIn: parent
                                    text: modelData.examType || ""
                                    font.pixelSize: 9
                                    color: modelData.typeColor || "#8E8E93"
                                    font.weight: Font.DemiBold
                                }
                            }
                            Rectangle {
                                visible: modelData.temp === true
                                width: 26
                                height: 13
                                radius: 6.5
                                color: Qt.rgba(1.0, 0.62, 0.04, 0.16)
                                Text {
                                    anchors.centerIn: parent
                                    text: "临时"
                                    font.pixelSize: 9
                                    color: "#C77700"
                                }
                            }
                            Rectangle {
                                visible: modelData.auto === true
                                width: 26
                                height: 13
                                radius: 6.5
                                color: Qt.rgba(0.039, 0.518, 1.0, 0.14)
                                Text {
                                    anchors.centerIn: parent
                                    text: "自动"
                                    font.pixelSize: 9
                                    color: "#0A6FD8"
                                }
                            }
                        }

                        Text {
                            visible: !!modelData.room
                            text: modelData.room || ""
                            font.pixelSize: 10
                            color: "#86868b"
                            leftPadding: 9
                            width: parent.width
                            elide: Text.ElideRight
                        }
                    }


                    // 交互层：右键看详情；左键按住上下拖动 → 与目标课程互换时间
                    Rectangle {
                        id: dragGhost
                        width: rowItem.width
                        height: rowCol.implicitHeight
                        radius: 8
                        color: Qt.rgba(1, 1, 1, 0.97)
                        border.width: 1
                        border.color: Qt.rgba(Backend.theme.r, Backend.theme.g, Backend.theme.b, 0.35)
                        visible: false
                        z: 200
                        Text {
                            anchors.centerIn: parent
                            text: rowItem.modelData.name || ""
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            color: "#1d1d1f"
                        }
                    }

                    MouseArea {
                        id: rowArea
                        anchors.fill: rowCol
                        preventStealing: true          // 拖动时不让卡片区域抢走
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        drag.target: dragGhost
                        drag.axis: Drag.YAxis
                        drag.threshold: 8              // 轻微移动不算拖动
                        acceptedButtons: Qt.LeftButton | Qt.RightButton

                        onPressed: function (mouse) {
                            if (mouse.button === Qt.RightButton) {
                                card.courseRightClicked(rowItem.modelData,
                                                        card.dayData.dateLabel || "",
                                                        card.dayData.dayLabel || "")
                            }
                        }

                        onReleased: {
                            if (!drag.active) {
                                dragGhost.visible = false
                                return
                            }
                            dragGhost.visible = false
                            // 找到落点所在的课程行 → 互换时间
                            var target = card.dropTargetAt(dragGhost.y + dragGhost.height / 2,
                                                           rowItem.index)
                            if (target) {
                                card.swapRequested(card.dayData.date || "",
                                                   rowItem.modelData.name || "",
                                                   rowItem.modelData.secStart || 0,
                                                   target.name || "",
                                                   target.secStart || 0)
                            }
                        }

                        onPositionChanged: {
                            if (drag.active) {
                                dragGhost.visible = true
                                dragGhost.z = 200
                            }
                        }
                    }

                    // 删除按钮（仅在主页开启"删除课程"模式时出现）
                    Rectangle {
                        id: delBtn
                        visible: card.deleteMode && !rowItem.deleting
                        width: 22
                        height: 22
                        radius: 11
                        anchors.right: parent.right
                        anchors.top: parent.top
                        color: delArea.pressed ? Qt.rgba(0, 0, 0, 0.14)
                               : (delArea.containsMouse ? Qt.rgba(0, 0, 0, 0.10)
                                                        : Qt.rgba(0, 0, 0, 0.05))

                        Text {
                            anchors.centerIn: parent
                            text: "\uE711"
                            font.family: "Segoe MDL2 Assets"
                            font.pixelSize: 9
                            color: delArea.containsMouse ? "#1d1d1f" : "#a1a1a6"
                        }

                        MouseArea {
                            id: delArea
                            anchors.fill: parent
                            hoverEnabled: true
                            // 卡片位于可滚动区域内，按下时的微小位移会被 Flickable 抢走，
                            // 导致点击丢失；这里禁止抢占。
                            preventStealing: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: jellyAnim.restart()
                        }
                    }

                    // 果冻动画：挤压回弹 → 塌缩 → 删除
                    SequentialAnimation {
                        id: jellyAnim

                        NumberAnimation { target: rowScale; property: "xScale"; to: 1.18; duration: 90; easing.type: Easing.OutQuad }
                        NumberAnimation { target: rowScale; property: "yScale"; to: 0.82; duration: 90; easing.type: Easing.OutQuad }
                        NumberAnimation { target: rowScale; property: "xScale"; to: 0.88; duration: 110; easing.type: Easing.InOutSine }
                        NumberAnimation { target: rowScale; property: "yScale"; to: 1.12; duration: 110; easing.type: Easing.InOutSine }
                        NumberAnimation { target: rowScale; property: "xScale"; to: 1.06; duration: 90 }
                        NumberAnimation { target: rowScale; property: "yScale"; to: 0.96; duration: 90 }
                        NumberAnimation { target: rowScale; property: "xScale"; to: 0.80; duration: 120; easing.type: Easing.InCubic }
                        NumberAnimation { target: rowScale; property: "yScale"; to: 0.80; duration: 120; easing.type: Easing.InCubic }
                        NumberAnimation { target: rowItem; property: "shrink"; to: 1.0; duration: 200; easing.type: Easing.InCubic }
                        ScriptAction {
                            script: rowItem.removeMe()
                        }
                    }

                    // 删除动画结束后回报给页面处理真实删除
                    Connections {
                        target: rowItem
                        function onRemoveMe() {
                            rowItem.deleting = true
                            card.deleteRequested(card.dayData.date || "",
                                                 rowItem.modelData.name || "",
                                                 rowItem.modelData.secStart || 0)
                        }
                    }
                }
            }
        }
    }
}
