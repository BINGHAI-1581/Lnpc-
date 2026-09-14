import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "widgets"

Rectangle {
    id: page
    objectName: "homePage"
    color: "transparent"

    property var backend
    property Item backdrop: null
    property bool deleteMode: false

    signal requestSettings()

    readonly property real stripSpacing: 10
    readonly property real cardWidth: Math.max(124, (strip.width - 6 * stripSpacing) / 7)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14

        // ---- 顶部：标题 + 操作 ----
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                spacing: 2
                Text {
                    text: Backend.viewTitle
                    font.pixelSize: 25
                    font.weight: Font.Bold
                    color: "#1d1d1f"
                }
                Text {
                    text: Backend.loggedIn
                          ? ("已同步 · " + Backend.lastUpdated)
                          : "登录后自动同步教务系统课表"
                    font.pixelSize: 12
                    color: "#6e6e73"
                }
            }

            Item { Layout.fillWidth: true }

            Btn {
                text: "复制消息"
                kind: "secondary"
                onClicked: Backend.copyPreview()
            }
            Btn {
                text: "发送到微信"
                busy: Backend.sendingState.indexOf("正在") === 0
                onClicked: Backend.sendNow()
            }
            Btn {
                text: "刷新"
                kind: "ghost"
                busy: Backend.loading
                onClicked: Backend.refresh()
            }
            Btn {
                text: page.deleteMode ? "完成" : "删除课程"
                kind: page.deleteMode ? "primary" : "ghost"
                onClicked: page.deleteMode = !page.deleteMode
            }
        }

        // ---- 周次导航 ----
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Btn {
                text: "上周"
                kind: "ghost"
                onClicked: Backend.shiftView(-7)
            }
            Btn {
                text: "本周"
                kind: Backend.dayOffset === 0 ? "primary" : "ghost"
                onClicked: Backend.resetView()
            }
            Btn {
                text: "下周"
                kind: "ghost"
                onClicked: Backend.shiftView(7)
            }
            Text {
                Layout.leftMargin: 6
                text: Backend.viewLabel
                font.pixelSize: 12
                font.weight: Font.DemiBold
                color: "#6e6e73"
                verticalAlignment: Text.AlignVCenter
            }
            Item { Layout.fillWidth: true }
        }

        // ---- 错误提示 ----
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 34 : 0
            visible: Backend.lastError !== ""
            radius: 10
            color: "#FFE5E5"
            Text {
                anchors.fill: parent
                anchors.leftMargin: 14
                verticalAlignment: Text.AlignVCenter
                text: Backend.lastError
                color: "#C0392B"
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }

        // ---- 删除模式提示 ----
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: page.deleteMode ? 32 : 0
            visible: page.deleteMode
            radius: 10
            color: Qt.rgba(Backend.theme.r, Backend.theme.g, Backend.theme.b, 0.12)
            Text {
                anchors.fill: parent
                anchors.leftMargin: 14
                verticalAlignment: Text.AlignVCenter
                text: "删除模式：点击课程右上角的 ✕ 可移除该课程（教务系统课程按当天隐藏，临时课程与自习会被永久移除）"
                color: Backend.theme.accentDark
                font.pixelSize: 11
                elide: Text.ElideRight
            }
        }

        // ---- 七天卡片区（滚动条固定在视口，不随内容移动）----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Flickable {
                id: strip
                anchors.fill: parent
                // 滚动条出现时给它留出位置，避免压住卡片底部
                anchors.bottomMargin: hbar.visible ? 15 : 0
                contentWidth: Math.max(7 * page.cardWidth + 6 * page.stripSpacing, width)
                contentHeight: height
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                Row {
                    spacing: page.stripSpacing
                    height: strip.height

                    Repeater {
                        model: Backend.days

                        delegate: DayCard {
                            required property var modelData
                            required property int index
                            dayData: modelData
                            backdrop: page.backdrop
                            isToday: modelData.isToday === true
                            deleteMode: page.deleteMode
                            width: page.cardWidth
                            height: strip.height
                            onDeleteRequested: function (date, name, secStart) {
                                Backend.deleteCourse(date, name, secStart)
                            }
                            onCourseRightClicked: function (course, dateLabel, dayLabel) {
                                dialog.openDetail(course, dateLabel, dayLabel)
                            }
                            onEmptyRightClicked: function (date, day) {
                                dialog.openAdd(day, 0)
                            }
                            onSwapRequested: function (date, nameA, secA, nameB, secB) {
                                // 两门课互换时间（各自移动到对方的大节）
                                Backend.moveCourse(date, nameA, secA, secB)
                                Backend.moveCourse(date, nameB, secB, secA)
                            }
                        }
                    }
                }
            }

            // 在卡片区空白处右键 → 直接添加课程
            MouseArea {
                id: blankArea
                anchors.fill: parent
                acceptedButtons: Qt.RightButton
                propagateComposedEvents: true
                z: -1
                onClicked: function (mouse) {
                    var day = 1
                    if (Backend.days.length > 0) {
                        // 用点击位置粗略判断是第几张卡片（每张卡片宽度固定）
                        var idx = Math.floor((mouse.x + strip.contentX) / (page.cardWidth + page.stripSpacing))
                        idx = Math.max(0, Math.min(Backend.days.length - 1, idx))
                        day = (Backend.days[idx] && Backend.days[idx].weekNum !== undefined)
                              ? (Backend.days[idx]["dayLabel"] === "周日" ? 7
                                 : ["周一","周二","周三","周四","周五","周六"].indexOf(Backend.days[idx]["dayLabel"]) + 1)
                              : 1
                    }
                    dialog.openAdd(day, 0)
                }
            }

            // 空状态：居中显示在卡片区域
            Column {
                id: emptyState
                anchors.centerIn: strip
                width: Math.min(strip.width - 80, 460)
                visible: Backend.days.length === 0
                spacing: 14

                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: Backend.loading ? "正在从教务系统获取课表…" : "还没有课表数据"
                    font.pixelSize: 17
                    font.weight: Font.DemiBold
                    color: "#6e6e73"
                }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    visible: !Backend.loading
                    text: Backend.needsOnboarding
                          ? "请先在「设置 → 登录信息」中填写学号与密码"
                          : "点击右上角「刷新」从教务系统同步课表"
                    font.pixelSize: 13
                    color: "#86868b"
                }
                BusySpinner {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: Backend.loading
                    size: 26
                }
                Btn {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: !Backend.loading
                    text: Backend.needsOnboarding ? "去填写登录信息" : "立即刷新"
                    onClicked: {
                        if (Backend.needsOnboarding) page.requestSettings()
                        else Backend.refresh()
                    }
                }
            }

            // 横向滚动条：自绘 + 轨道级拖拽（缩略图严格跟手）
            Item {
                id: hbar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 13
                visible: strip.contentWidth > strip.width + 1
                z: 10

                readonly property real maxScroll: Math.max(0, strip.contentWidth - strip.width)
                readonly property real thumbW: Math.max(36, width * strip.visibleArea.widthRatio)
                readonly property real thumbX: Math.max(0, Math.min(width - thumbW,
                                                          strip.visibleArea.xPosition * width))
                readonly property real usable: Math.max(1, width - thumbW)

                Rectangle {
                    id: hthumb
                    y: 2
                    height: parent.height - 4
                    x: hbar.thumbX
                    width: hbar.thumbW
                    radius: height / 2
                    color: hbarArea.pressed ? Qt.rgba(0.35, 0.35, 0.38, 0.55)
                           : (hbarArea.containsMouse ? Qt.rgba(0.42, 0.42, 0.45, 0.42)
                                                     : Qt.rgba(0.45, 0.45, 0.48, 0.30))
                    Behavior on color { ColorAnimation { duration: 150 } }
                }

                MouseArea {
                    id: hbarArea
                    anchors.fill: parent
                    hoverEnabled: true
                    preventStealing: true
                    property real grabOffset: 0

                    function scrollTo(mouseX) {
                        if (hbar.maxScroll <= 0)
                            return
                        var pos = Math.max(0, Math.min(hbar.usable, mouseX - grabOffset))
                        strip.cancelFlick()
                        strip.contentX = pos / hbar.usable * hbar.maxScroll
                    }

                    onPressed: function (mouse) {
                        grabOffset = (mouse.x >= hbar.thumbX && mouse.x <= hbar.thumbX + hbar.thumbW)
                                     ? (mouse.x - hbar.thumbX) : hbar.thumbW / 2
                        scrollTo(mouse.x)
                    }
                    onPositionChanged: function (mouse) {
                        if (pressed)          // 只在按住拖动时滚动
                            scrollTo(mouse.x)
                    }
                }
            }
        }

        // ---- 消息预览 ----
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Backend.days.length === 0 ? 0 : 112
            visible: Backend.days.length > 0
            radius: 16
            color: Backend.fancyUi ? "transparent" : Qt.rgba(1, 1, 1, 0.80)
            border.width: Backend.fancyUi ? 0 : 1
            border.color: Qt.rgba(1, 1, 1, 0.9)

            GlassSurface {
                visible: Backend.fancyUi
                anchors.fill: parent
                radius: 16
                edge: 18
                aberration: 1.1
                tint: 0.28
                refreshMs: 150
                backdrop: page.backdrop
                z: -1
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 13
                spacing: 5

                Text {
                    text: "微信消息预览"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    color: "#86868b"
                }
                ScrollPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TextEdit {
                        width: parent ? parent.width : 0
                        readOnly: true
                        selectByMouse: true
                        text: Backend.previewText
                        wrapMode: TextEdit.Wrap
                        font.pixelSize: 12
                        color: "#1d1d1f"
                    }
                }
            }
        }
    }


    // ---- 课程详情 / 添加课程 弹窗（放在布局之外，覆盖整页）----
    CourseDialog {
        id: dialog
        onCloseRequested: shown = false
        onAddRequested: function (payload) {
            if (Backend.addTempCourse(payload))
                shown = false
        }
    }
}
