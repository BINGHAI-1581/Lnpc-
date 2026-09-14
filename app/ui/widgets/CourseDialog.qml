import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 课程详情 / 添加课程 通用弹窗（Apple 风格卡片 + 半透明遮罩）
Item {
    id: root

    property bool shown: false
    property string mode: "detail"          // detail | add
    property var course: ({})
    property string dateLabel: ""
    property string dayLabel: ""

    // 添加模式下由外部填好的星期
    property int newDay: 1
    signal addRequested(var payload)
    signal closeRequested()

    anchors.fill: parent
    visible: shown
    z: 500

    // 遮罩
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.28)
        MouseArea {
            anchors.fill: parent
            preventStealing: true
            onClicked: root.closeRequested()
        }
    }

    Rectangle {
        id: panel
        width: Math.min(parent.width - 80, 420)
        height: content.implicitHeight + 40
        anchors.centerIn: parent
        radius: 20
        color: Qt.rgba(1, 1, 1, 0.96)
        border.width: 1
        border.color: Qt.rgba(0, 0, 0, 0.08)

        ColumnLayout {
            id: content
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: root.mode === "detail" ? "课程详情" : "添加课程"
                    font.pixelSize: 17
                    font.weight: Font.Bold
                    color: "#1d1d1f"
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "✕"
                    font.pixelSize: 14
                    color: "#a1a1a6"
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -8
                        preventStealing: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeRequested()
                    }
                }
            }

            // ---- 详情模式 ----
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10
                visible: root.mode === "detail"

                Repeater {
                    model: [
                        { k: "课程名称", v: root.course.name || "" },
                        { k: "授课老师", v: root.course.teacher || "未填写" },
                        { k: "授课地点", v: root.course.room || "未定义教室" },
                        { k: "授课时间", v: (root.course.timeText || "")
                              + (root.course.secText ? "　" + root.course.secText : "")
                              + (root.course.weeksText ? "　" + root.course.weeksText : "") },
                        { k: "课程类型", v: root.course.examType || "—" },
                        { k: "总课程节数", v: (root.course.hours || "")
                              + (root.course.hours ? "　" : "") + "本次 "
                              + ((root.course.secEnd && root.course.secStart)
                                 ? (root.course.secEnd - root.course.secStart + 1) : 2) + " 小节" },
                        { k: "现在是第几节", v: root.dateLabel + " " + root.dayLabel
                              + "　当天第 " + (root.course.dayIndex || 1) + " 门 / 共 "
                              + (root.course.dayTotal || 1) + " 门" }
                    ]
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: modelData.k
                            font.pixelSize: 12
                            color: "#86868b"
                            Layout.preferredWidth: 76
                        }
                        Text {
                            text: modelData.v
                            font.pixelSize: 13
                            color: "#1d1d1f"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // ---- 添加模式 ----
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10
                visible: root.mode === "add"

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 10

                    Text { text: "课程名称"; font.pixelSize: 12; color: "#86868b" }
                    Field { id: fName; Layout.fillWidth: true; placeholderText: "例如：自习" }

                    Text { text: "授课老师"; font.pixelSize: 12; color: "#86868b" }
                    Field { id: fTeacher; Layout.fillWidth: true; placeholderText: "可留空" }

                    Text { text: "星期"; font.pixelSize: 12; color: "#86868b" }
                    Select {
                        id: fDay
                        Layout.fillWidth: true
                        model: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                        currentIndex: Math.max(0, root.newDay - 1)
                    }

                    Text { text: "上课时间"; font.pixelSize: 12; color: "#86868b" }
                    Select {
                        id: fSlot
                        Layout.fillWidth: true
                        model: ["第1-2节 08:00-10:05", "第3-4节 10:25-12:00",
                                "第5-6节 13:30-15:05", "第7-8节 15:10-16:45",
                                "第9-10节 18:00-19:40"]
                        currentIndex: root.nextSlot
                    }

                    Text { text: "授课地点"; font.pixelSize: 12; color: "#86868b" }
                    Field { id: fRoom; Layout.fillWidth: true; placeholderText: "例如：求美楼（3614）" }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Btn {
                    visible: root.mode === "add"
                    text: "添加"
                    onClicked: {
                        if (!fName.text.trim()) {
                            fName.placeholderText = "请先填写课程名称"
                            return
                        }
                        root.addRequested({
                            "name": fName.text.trim(),
                            "teacher": fTeacher.text.trim(),
                            "day": fDay.currentIndex + 1,
                            "time": root.slotTime(fSlot.currentIndex),
                            "room": fRoom.text.trim(),
                            "weeks": ""
                        })
                    }
                }
                Btn {
                    visible: root.mode === "detail"
                    text: "知道了"
                    kind: "primary"
                    onClicked: root.closeRequested()
                }
            }
        }
    }

    // 添加模式：默认落在哪个大节（0..4）
    property int nextSlot: 0

    function slotTime(index) {
        var times = ["08:00-10:05", "10:25-12:00", "13:30-15:05",
                     "15:10-16:45", "18:00-19:40"]
        return times[Math.max(0, Math.min(4, index))] || "08:00-10:05"
    }

    function openDetail(c, dLabel, wLabel) {
        course = c
        dateLabel = dLabel
        dayLabel = wLabel
        mode = "detail"
        shown = true
    }

    function openAdd(day, slot) {
        newDay = day
        nextSlot = slot
        mode = "add"
        shown = true
    }
}
