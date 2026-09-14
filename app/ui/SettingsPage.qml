import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "widgets"

// 设置页：整页内容放在一个圆角面板内，滚动发生在面板内部，
// 因此不会有任何直角内容切到窗口圆角。
Item {
    id: page

    property var backend
    property var s: ({})
    property Item backdrop: null

    function reload() { s = Backend.settings }

    function save() {
        var m = {
            "send_mode": sendModeSel.currentIndex === 0 ? "manual" : "scheduled",
            "send_target": targetInput.text,
            "scope": scopeSel.currentIndex === 0 ? "today" : "seven",
            "style": styleSel.currentIndex === 0 ? "detailed" : "compact",
            "emoji": emojiToggle.checked,
            "auto_study": autoStudyToggle.checked,
            "class_name": classField.text,
            "school_base": baseInput.text,
            "send_hour": hourSpin.value,
            "send_minute": minuteSpin.value,
            "autostart": autoToggle.checked,
            "wechat_path": pathInput.text
        }
        Backend.saveSettings(m)
    }

    Component.onCompleted: reload()

    Connections {
        target: Backend
        function onStateChanged() {
            if (Backend.account !== page.s.account) page.reload()
        }
    }

    // ---- 圆角面板（美化风格下为毛玻璃）----
    Rectangle {
        id: panel
        anchors.fill: parent
        anchors.margins: 22
        radius: 20
        color: Backend.fancyUi ? "transparent" : Qt.rgba(0, 0, 0, 0.045)
        border.width: Backend.fancyUi ? 0 : 1
        border.color: Qt.rgba(1, 1, 1, 0.65)
        clip: true

        GlassSurface {
            visible: Backend.fancyUi
            anchors.fill: parent
            radius: 20
            edge: 22
            aberration: 1.2
            tint: 0.34
            backdrop: page.backdrop
            z: -1
        }

        ScrollPane {
            id: scroller
            anchors.fill: parent
            anchors.margins: 6
            readonly property real pad: 22

            ColumnLayout {
                id: contentCol
                x: scroller.pad
                y: scroller.pad
                width: scroller.flickable.width - scroller.pad * 2
                spacing: 18

                Text {
                    text: "设置"
                    font.pixelSize: 25
                    font.weight: Font.Bold
                    color: "#1d1d1f"
                }

                // ==================== 登录信息 ====================
                SectionTitle { text: "登录信息" }

                Card {
                    Layout.fillWidth: true
                    backdrop: page.backdrop

                    GridLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        columns: 2
                        columnSpacing: 16
                        rowSpacing: 13

                        Label2 { Layout.preferredWidth: 88; text: "教务系统地址" }
                        Field {
                            id: baseInput
                            Layout.fillWidth: true
                            Layout.maximumWidth: 420
                            placeholderText: "例如：http://jw.example.edu.cn/jsxsd"
                            text: s.school_base || ""
                            onEditingFinished: page.save()
                        }

                        Label2 { Layout.preferredWidth: 88; text: "学号" }
                        Field {
                            id: accInput
                            Layout.fillWidth: true
                            Layout.maximumWidth: 420
                            placeholderText: "请输入学号"
                            text: s.account || ""
                        }

                        Label2 { Layout.preferredWidth: 88; text: "密码" }
                        Field {
                            id: pwdInput
                            Layout.fillWidth: true
                            Layout.maximumWidth: 420
                            placeholderText: s.hasPassword ? "已保存（输入新密码可修改）" : "请输入密码"
                            echoMode: TextInput.Password
                        }

                        Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
                        Row {
                            Layout.fillWidth: true
                            spacing: 10
                            Btn {
                                text: "保存并重新登录"
                                busy: Backend.loading
                                onClicked: {
                                    Backend.saveLogin(accInput.text, pwdInput.text)
                                    pwdInput.clear()
                                }
                            }
                            Btn {
                                text: "测试连接"
                                kind: "secondary"
                                onClicked: Backend.testLogin(
                                    accInput.text,
                                    pwdInput.text.length > 0 ? pwdInput.text : "__SAVED__")
                            }
                        }
                    }
                }

                // ==================== 外观 ====================
                SectionTitle { text: "外观" }

                Card {
                    Layout.fillWidth: true
                    backdrop: page.backdrop

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 16
                            rowSpacing: 13

                            Label2 { Layout.preferredWidth: 88; text: "界面风格" }
                            Row {
                                Layout.fillWidth: true
                                spacing: 10
                                Select {
                                    id: styleSel2
                                    Layout.preferredWidth: 220
                                    model: ["正常", "美化"]
                                    currentIndex: Backend.uiStyle === "beautify" ? 1 : 0
                                    onActivated: {
                                        Backend.saveSettings({
                                            "ui_style": currentIndex === 1 ? "beautify" : "normal"
                                        })
                                    }
                                }
                                Text {
                                    text: "美化 = 全界面液态玻璃（背景模糊 / 高光 / 更通透）"
                                    font.pixelSize: 11
                                    color: "#86868b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Label2 { Layout.preferredWidth: 88; text: "强调色" }
                            Row {
                                Layout.fillWidth: true
                                spacing: 8
                                Repeater {
                                    model: ["#0A84FF", "#5E5CE6", "#FF375F", "#34C759",
                                            "#FF9F0A", "#00C7BE", "#8E8E93"]
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: 26; height: 26; radius: 13
                                        color: modelData
                                        border.width: Backend.accent === modelData ? 3 : 1
                                        border.color: Backend.accent === modelData ? "#ffffff"
                                                                                   : Qt.rgba(0,0,0,0.12)
                                        anchors.verticalCenter: parent.verticalCenter
                                        MouseArea {
                                            anchors.fill: parent
                                            preventStealing: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: Backend.saveTheme(modelData, "",
                                                                          "", "")
                                        }
                                    }
                                }
                                Text {
                                    text: Backend.accent
                                    font.pixelSize: 11
                                    color: "#a1a1a6"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Label2 { Layout.preferredWidth: 88; text: "背景" }
                            Row {
                                Layout.fillWidth: true
                                spacing: 8
                                Repeater {
                                    model: [
                                        { n: "晨雾", t: "#eaf2ff", m: "#e6ecff", b: "#eef0ff" },
                                        { n: "薄紫", t: "#f0eaff", m: "#eae4ff", b: "#f2eaff" },
                                        { n: "薄荷", t: "#e6f7ef", m: "#e2f2ea", b: "#ecf7f2" },
                                        { n: "樱花", t: "#ffeaf2", m: "#fbe6ee", b: "#fdeef4" },
                                        { n: "暖沙", t: "#fdf3e4", m: "#f8eedd", b: "#fdf5ea" },
                                        { n: "石墨", t: "#e8e8ee", m: "#e2e2ea", b: "#ececf2" }
                                    ]
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: 46; height: 26; radius: 8
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: modelData.t }
                                            GradientStop { position: 1.0; color: modelData.b }
                                        }
                                        border.width: Backend.bgTop === modelData.t ? 2 : 1
                                        border.color: Backend.bgTop === modelData.t ? Backend.accent
                                                                                    : Qt.rgba(0,0,0,0.10)
                                        anchors.verticalCenter: parent.verticalCenter
                                        MouseArea {
                                            anchors.fill: parent
                                            preventStealing: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: Backend.saveTheme("", modelData.t,
                                                                          modelData.m, modelData.b)
                                        }
                                    }
                                }
                                Text {
                                    text: "点色块即应用"
                                    font.pixelSize: 11
                                    color: "#a1a1a6"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }
                }

                // ==================== 格式转换 ====================
                SectionTitle { text: "格式转换" }

                Card {
                    Layout.fillWidth: true
                    backdrop: page.backdrop

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 16
                            rowSpacing: 13

                            Label2 { Layout.preferredWidth: 88; text: "发送范围" }
                            Select {
                                id: scopeSel
                                Layout.fillWidth: true
                            Layout.maximumWidth: 420
                                model: ["仅今天", "近七天"]
                                currentIndex: s.scope === "seven" ? 1 : 0
                                onActivated: page.save()
                            }

                            Label2 { Layout.preferredWidth: 88; text: "排版风格" }
                            Select {
                                id: styleSel
                                Layout.fillWidth: true
                            Layout.maximumWidth: 420
                                model: ["详细（日期+时间+教室）", "紧凑（一行一门课）"]
                                currentIndex: s.style === "compact" ? 1 : 0
                                onActivated: page.save()
                            }

                            Label2 { Layout.preferredWidth: 88; text: "表情符号" }
                            Toggle {
                                id: emojiToggle
                                checked: s.emoji !== false
                                onToggled: page.save()
                            }

                            Label2 {
                                Layout.preferredWidth: 88
                                text: "自动补自习"
                            }
                            Row {
                                Layout.fillWidth: true
                                spacing: 10
                                Toggle {
                                    id: autoStudyToggle
                                    checked: s.auto_study !== false
                                    onToggled: page.save()
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    text: "上午（第1-2节）没课时自动加一节自习"
                                    font.pixelSize: 11
                                    color: "#86868b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Qt.rgba(0, 0, 0, 0.07)
                        }

                        // 节次对应的上课时间（详细风格按此换算）
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Label2 { Layout.preferredWidth: 88; text: "节次时间" }
                            Text {
                                text: "详细风格按此换算上课时间，如与学校不同请修改"
                                font.pixelSize: 11
                                color: "#a1a1a6"
                            }
                            Item { Layout.fillWidth: true }
                            Btn {
                                text: "保存时间"
                                kind: "secondary"
                                onClicked: {
                                    var list = []
                                    for (var i = 0; i < 5; i++)
                                        list.push(ptRepeater.itemAt(i).text)
                                    Backend.savePeriodTimes(list)
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 5
                            columnSpacing: 10
                            rowSpacing: 6

                            Repeater {
                                model: ["第01-02节", "第03-04节", "第05-06节", "第07-08节", "第09-10节"]
                                delegate: Text {
                                    required property var modelData
                                    text: modelData
                                    font.pixelSize: 11
                                    color: "#86868b"
                                    horizontalAlignment: Text.AlignHCenter
                                    Layout.fillWidth: true
                                }
                            }
                            Repeater {
                                id: ptRepeater
                                model: Backend.periodTimes
                                delegate: Field {
                                    required property var modelData
                                    text: modelData
                                    Layout.fillWidth: true
                                    horizontalAlignment: TextInput.AlignHCenter
                                    font.pixelSize: 12
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Qt.rgba(0, 0, 0, 0.07)
                        }

                        // 消息预览
                        RowLayout {
                            Layout.fillWidth: true
                            Label2 { Layout.preferredWidth: 88; text: "发送信息预览" }
                            Item { Layout.fillWidth: true }
                            Btn {
                                text: "复制"
                                kind: "ghost"
                                onClicked: Backend.copyPreview()
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 190
                            radius: 12
                            color: Qt.rgba(0, 0, 0, 0.035)
                            border.width: 1
                            border.color: Qt.rgba(0, 0, 0, 0.06)

                            ScrollPane {
                                anchors.fill: parent
                                anchors.margins: 10

                                TextEdit {
                                    width: parent ? parent.width : 0
                                    readOnly: true
                                    selectByMouse: true
                                    text: Backend.previewText
                                    wrapMode: TextEdit.Wrap
                                    font.pixelSize: 12
                                    font.family: "Consolas"
                                    color: "#1d1d1f"
                                }
                            }
                        }
                    }
                }

                // ==================== 课表文件导入 ====================
                SectionTitle { text: "课表文件导入" }

                Card {
                    Layout.fillWidth: true
                    backdrop: page.backdrop

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        Text {
                            Layout.fillWidth: true
                            text: "导入学校发的自习安排 / 临时调课文件（Excel、Word）。软件会读取教务系统里的班级，自动找出你自己班级那几行，把对应星期、节次的教室填进课表，无需手工对照。"
                            font.pixelSize: 11
                            color: "#86868b"
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 16
                            rowSpacing: 13

                            Label2 { Layout.preferredWidth: 88; text: "我的班级" }
                            Row {
                                Layout.fillWidth: true
                                spacing: 10
                                Field {
                                    id: classField
                                    Layout.preferredWidth: 220
                                    placeholderText: "填写你的班级名称"
                                    text: s.class_name || ""
                                    onEditingFinished: page.save()
                                }

                            }

                            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
                            Row {
                                Layout.fillWidth: true
                                spacing: 10
                                Btn {
                                    text: "选择文件导入"
                                    onClicked: Backend.pickAndImportFile()
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "支持 .xlsx / .docx，文件名含「第N周」会自动识别适用周次"
                                    font.pixelSize: 11
                                    color: "#a1a1a6"
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Qt.rgba(0, 0, 0, 0.07)
                        }

                        // ---- 手动输入描述，自动解析 ----
                        RowLayout {
                            Layout.fillWidth: true
                            Label2 { Layout.preferredWidth: 88; text: "手动描述" }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: "一行一条，自动识别星期/节次/教室/课程名"
                                font.pixelSize: 11
                                color: "#a1a1a6"
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 112
                            radius: 12
                            color: Qt.rgba(0, 0, 0, 0.035)
                            border.width: 1
                            border.color: Qt.rgba(0, 0, 0, 0.06)

                            ScrollPane {
                                anchors.fill: parent
                                anchors.margins: 10

                                TextEdit {
                                    id: manualText
                                    width: parent ? parent.width : 0
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    font.pixelSize: 12
                                    color: "#1d1d1f"
                                    text: "周二 一二节 3614
周三 3-4节 高等数学 求真楼1117"
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Field {
                                id: manualTitle
                                Layout.preferredWidth: 220
                                placeholderText: "备注名称（可选）"
                            }
                            Field {
                                id: manualWeek
                                Layout.preferredWidth: 120
                                placeholderText: "周次"
                                text: Backend.currentWeek > 0 ? String(Backend.currentWeek) : "1"
                            }
                            Btn {
                                text: "解析并应用"
                                onClicked: Backend.importText(manualText.text,
                                                              manualTitle.text,
                                                              parseInt(manualWeek.text) || 0)
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "示例：周二 一二节 3614 ／ 周三 3-4节 高等数学 求真楼1117 ／ 周四晚自习 18:00-19:40 3614"
                                font.pixelSize: 11
                                color: "#a1a1a6"
                                wrapMode: Text.WordWrap
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Qt.rgba(0, 0, 0, 0.07)
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: Backend.importedFiles.length === 0
                            text: "还没有导入文件。"
                            font.pixelSize: 11
                            color: "#a1a1a6"
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            visible: Backend.importedFiles.length > 0
                            color: Qt.rgba(0, 0, 0, 0.07)
                        }

                        Repeater {
                            model: Backend.importedFiles
                            delegate: Rectangle {
                                required property var modelData
                                required property int index
                                Layout.fillWidth: true
                                implicitHeight: 56
                                radius: 10
                                color: Qt.rgba(1, 1, 1, 0.72)
                                border.width: 1
                                border.color: Qt.rgba(0, 0, 0, 0.06)

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 8
                                    spacing: 10

                                    Rectangle {
                                        width: 3; height: 22; radius: 1.5
                                        color: modelData.matched ? "#34C759" : "#FF9F0A"
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Text {
                                            text: modelData.source
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                            color: "#1d1d1f"
                                            elide: Text.ElideMiddle
                                            Layout.fillWidth: true
                                        }
                                        Text {
                                            text: (modelData.week ? ("第" + modelData.week + "周") : "周次未识别")
                                                  + " · 班级 " + modelData.class
                                                  + " · " + modelData.slots.length + " 处安排"
                                                  + (modelData.matched ? "" : "（模糊匹配）")
                                            font.pixelSize: 11
                                            color: modelData.matched ? "#6e6e73" : "#C77700"
                                        }
                                    }

                                    Btn {
                                        text: "移除"
                                        kind: "ghost"
                                        onClicked: Backend.removeImportedFile(index)
                                    }
                                }
                            }
                        }
                    }
                }

                // ==================== 临时课程 ====================
                SectionTitle { text: "临时课程" }

                Card {
                    Layout.fillWidth: true
                    backdrop: page.backdrop

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        Text {
                            Layout.fillWidth: true
                            text: "教务系统里没有、但需要一起推送的课程（如自习、临时调课）。周次留空表示每周都显示。"
                            font.pixelSize: 11
                            color: "#86868b"
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 16
                            rowSpacing: 13

                            Label2 { Layout.preferredWidth: 88; text: "课程名称" }
                            Field {
                                id: tcName
                                Layout.fillWidth: true
                            Layout.maximumWidth: 420
                                placeholderText: "例如：自习"
                            }

                            Label2 { Layout.preferredWidth: 88; text: "星期" }
                            Select {
                                id: tcDay
                                Layout.fillWidth: true
                            Layout.maximumWidth: 420
                                model: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                                currentIndex: 0
                            }

                            Label2 { Layout.preferredWidth: 88; text: "上课时间" }
                            Field {
                                id: tcTime
                                Layout.fillWidth: true
                            Layout.maximumWidth: 420
                                placeholderText: "例如：08:30-10:05"
                            }

                            Label2 { Layout.preferredWidth: 88; text: "教室" }
                            Field {
                                id: tcRoom
                                Layout.fillWidth: true
                            Layout.maximumWidth: 420
                                placeholderText: "例如：求真楼（1117）"
                            }

                            Label2 { Layout.preferredWidth: 88; text: "周次" }
                            Field {
                                id: tcWeeks
                                Layout.fillWidth: true
                            Layout.maximumWidth: 420
                                placeholderText: "留空=每周；也可填 1-8,10 或 单周"
                            }

                            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
                            Btn {
                                text: "添加课程"
                                onClicked: {
                                    var ok = Backend.addTempCourse({
                                        "name": tcName.text,
                                        "day": tcDay.currentIndex + 1,
                                        "time": tcTime.text,
                                        "room": tcRoom.text,
                                        "weeks": tcWeeks.text
                                    })
                                    if (ok) {
                                        tcName.clear()
                                        tcTime.clear()
                                        tcRoom.clear()
                                        tcWeeks.clear()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            visible: Backend.tempCourses.length > 0
                            color: Qt.rgba(0, 0, 0, 0.07)
                        }

                        Repeater {
                            model: Backend.tempCourses
                            delegate: Rectangle {
                                required property var modelData
                                required property int index
                                Layout.fillWidth: true
                                implicitHeight: 44
                                radius: 10
                                color: Qt.rgba(1, 1, 1, 0.72)
                                border.width: 1
                                border.color: Qt.rgba(0, 0, 0, 0.06)

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 8
                                    spacing: 10

                                    Rectangle { width: 3; height: 18; radius: 1.5; color: "#FF9F0A" }
                                    Text {
                                        text: modelData.name
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        color: "#1d1d1f"
                                    }
                                    Text {
                                        text: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][modelData.day - 1]
                                        font.pixelSize: 12
                                        color: "#6e6e73"
                                    }
                                    Text {
                                        text: modelData.time || "时间待定"
                                        font.pixelSize: 12
                                        color: "#6e6e73"
                                    }
                                    Text {
                                        text: modelData.room || "未定义教室"
                                        font.pixelSize: 12
                                        color: "#6e6e73"
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        visible: !!modelData.weeks
                                        text: modelData.weeks
                                        font.pixelSize: 11
                                        color: "#a1a1a6"
                                    }
                                    Btn {
                                        text: "删除"
                                        kind: "ghost"
                                        onClicked: Backend.removeTempCourse(index)
                                    }
                                }
                            }
                        }
                    }
                }

                // ==================== 运行方式 ====================
                SectionTitle { text: "运行方式" }

                Card {
                    Layout.fillWidth: true
                    backdrop: page.backdrop

                    GridLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        columns: 2
                        columnSpacing: 16
                        rowSpacing: 13

                        Label2 { Layout.preferredWidth: 88; text: "发送方式" }
                        Select {
                            id: sendModeSel
                            Layout.fillWidth: true
                            Layout.maximumWidth: 420
                            model: ["手动发送（点按钮才发）", "指定时间自动发送"]
                            currentIndex: s.send_mode === "scheduled" ? 1 : 0
                            onActivated: page.save()
                        }

                        Label2 {
                            Layout.preferredWidth: 88
                            text: "发送时间"
                            opacity: sendModeSel.currentIndex === 1 ? 1 : 0.45
                        }
                        Row {
                            Layout.fillWidth: true
                            spacing: 8
                            opacity: sendModeSel.currentIndex === 1 ? 1 : 0.45

                            Number {
                                id: hourSpin
                                from: 0
                                to: 23
                                value: s.send_hour !== undefined ? s.send_hour : 7
                                onValueModified: page.save()
                            }
                            Text {
                                text: "时"
                                font.pixelSize: 13
                                color: "#6e6e73"
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Number {
                                id: minuteSpin
                                from: 0
                                to: 59
                                value: s.send_minute !== undefined ? s.send_minute : 30
                                onValueModified: page.save()
                            }
                            Text {
                                text: "分"
                                font.pixelSize: 13
                                color: "#6e6e73"
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        Label2 { Layout.preferredWidth: 88; text: "发送目标" }
                        Field {
                            id: targetInput
                            Layout.fillWidth: true
                            Layout.maximumWidth: 420
                            placeholderText: "微信群名或联系人"
                            text: s.send_target || ""
                            onEditingFinished: page.save()
                        }

                        Label2 { Layout.preferredWidth: 88; text: "微信路径" }
                        Field {
                            id: pathInput
                            Layout.fillWidth: true
                            Layout.maximumWidth: 560
                            placeholderText: "留空自动检测 WeChat.exe"
                            text: s.wechat_path || ""
                            onEditingFinished: page.save()
                        }

                        Label2 { Layout.preferredWidth: 88; text: "开机自启动" }
                        Toggle {
                            id: autoToggle
                            checked: s.autostart === true
                            onToggled: page.save()
                        }

                        Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
                        Row {
                            spacing: 10
                            Btn {
                                text: "发送测试消息"
                                kind: "secondary"
                                onClicked: Backend.sendTest()
                            }
                            Btn { text: "保存设置"; onClicked: page.save() }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: "定时发送说明：到达设定时间后软件会自动刷新课表，然后打开微信 → 粘贴 → 发送到目标会话。发送那几秒请勿操作键盘鼠标。"
                    font.pixelSize: 11
                    color: "#86868b"
                    wrapMode: Text.Wrap
                }

                Item { Layout.preferredHeight: 6 }
            }
        }
    }
}
