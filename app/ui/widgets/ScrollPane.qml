import QtQuick

// 可滚动面板：Flickable + 自绘滚动条（拖动 1:1 跟手）。
//
// 刻意不用 QtQuick.Controls 的 ScrollBar：
//  1) 作为 Flickable 的 attached 属性时，在嵌套布局里不会被自动定位（会缩成小方块停在左上角）；
//  2) 它的 contentItem 会被样式系统再次收缩，导致缩略图只剩 1px 宽。
//
// 跟手的关键：拖拽事件监听在**整条轨道**上（轨道不随滚动移动），
// 用鼠标在轨道中的绝对位置换算内容位置；若监听在缩略图自身上，缩略图会随
// 滚动一起移动，鼠标局部坐标被重复计算，视觉上就会"跑得比手快"。
Item {
    id: pane

    default property alias contentData: holder.data
    property alias flickable: flick
    property alias contentY: flick.contentY
    property alias moving: flick.moving
    property alias contentHeight: flick.contentHeight
    property int barWidth: 11
    property int thumbMinHeight: 36
    property real wheelStep: 1.0        // 滚轮灵敏度（每格滚动的内容像素比例）

    // 内容放进 Flickable 内部的 holder，高度由 childrenRect 自动推导
    Flickable {
        id: flick
        anchors.fill: parent
        anchors.rightMargin: pane.barWidth
        clip: true
        contentWidth: width
        contentHeight: Math.max(height, holder.height)
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick

        Item {
            id: holder
            width: flick.width
            height: childrenRect.height
        }

        // 平滑滚轮：按目标位置做短动画，避免整格跳动
        WheelHandler {
            id: wheel
            onWheel: function (event) {
                var maxY = Math.max(0, flick.contentHeight - flick.height)
                if (maxY <= 0) {
                    event.accepted = false
                    return
                }
                var target = Math.max(0, Math.min(maxY,
                        flick.contentY - event.angleDelta.y * pane.wheelStep))
                smooth.stop()
                smooth.from = flick.contentY
                smooth.to = target
                smooth.restart()
                console.log("[wheel] from=" + flick.contentY.toFixed(1) + " target=" + target.toFixed(1))
                event.accepted = true
            }
        }

        NumberAnimation {
            id: smooth
            target: flick
            property: "contentY"
            duration: 160
            easing.type: Easing.OutCubic
        }
    }

    // ---- 滚动条 ----
    readonly property bool needBar: flick.contentHeight > flick.height + 1

    Item {
        id: track
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        width: pane.barWidth
        visible: pane.needBar

        readonly property real maxScroll: Math.max(0, flick.contentHeight - flick.height)
        readonly property real thumbH: Math.max(pane.thumbMinHeight,
                                               track.height * flick.visibleArea.heightRatio)
        readonly property real thumbY: Math.max(0, Math.min(track.height - thumbH,
                                                     flick.visibleArea.yPosition * track.height))
        readonly property real usable: Math.max(1, track.height - thumbH)

        Rectangle {
            id: thumb
            x: 2
            width: parent.width - 4
            y: track.thumbY
            height: track.thumbH
            radius: width / 2
            color: trackArea.pressed ? Qt.rgba(0.35, 0.35, 0.38, 0.55)
                   : (trackArea.containsMouse ? Qt.rgba(0.42, 0.42, 0.45, 0.42)
                                              : Qt.rgba(0.45, 0.45, 0.48, 0.30))
            Behavior on color { ColorAnimation { duration: 150 } }
        }

        MouseArea {
            id: trackArea
            anchors.fill: parent
            hoverEnabled: true
            preventStealing: true
            property real grabOffset: 0

            function scrollTo(mouseY) {
                if (track.maxScroll <= 0)
                    return
                var pos = Math.max(0, Math.min(track.usable, mouseY - grabOffset))
                flick.cancelFlick()
                flick.contentY = pos / track.usable * track.maxScroll
            }

            onPressed: function (mouse) {
                // 按在缩略图上：保持原来的相对位置；按在空白处：缩略图中心对齐光标
                grabOffset = (mouse.y >= track.thumbY && mouse.y <= track.thumbY + track.thumbH)
                             ? (mouse.y - track.thumbY) : track.thumbH / 2
                scrollTo(mouse.y)
            }
            onPositionChanged: function (mouse) {
                if (pressed)          // 只在按住拖动时滚动；划过不改变内容位置
                    scrollTo(mouse.y)
            }
        }
    }
}
