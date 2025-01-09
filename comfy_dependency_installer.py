import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLineEdit, QLabel, 
                           QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
                           QFileDialog, QMessageBox, QProgressDialog, QDialog, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import subprocess
import pkg_resources

class InstallThread(QThread):
    output_received = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            # 设置环境变量以禁用输出缓冲
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            process = subprocess.Popen(
                self.cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )

            # 实时读取输出
            while True:
                # 读取一个字符
                char = process.stdout.read(1)
                if char:
                    # 收集字符直到遇到换行符
                    line = char
                    while char and char != '\n':
                        char = process.stdout.read(1)
                        line += char if char else ''
                    if line.strip():
                        self.output_received.emit(line.strip())

                # 读取错误输出
                error_char = process.stderr.read(1)
                if error_char:
                    # 收集字符直到遇到换行符
                    error_line = error_char
                    while error_char and error_char != '\n':
                        error_char = process.stderr.read(1)
                        error_line += error_char if error_char else ''
                    if error_line.strip():
                        self.output_received.emit(error_line.strip())

                # 检查进程是否结束
                if process.poll() is not None and not char and not error_char:
                    break

            if process.returncode == 0:
                self.finished.emit(True, "安装成功")
            else:
                stderr = process.stderr.read()
                self.finished.emit(False, f"安装失败:\n{stderr}")
        except Exception as e:
            self.finished.emit(False, f"安装过程出错: {str(e)}")

class InstallDialog(QDialog):
    def __init__(self, package_name, cmd, parent=None):
        super().__init__(parent)
        self.package_name = package_name
        self.cmd = cmd
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(f"安装 {self.package_name}")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # 命令显示标签
        cmd_label = QLabel("执行命令:")
        layout.addWidget(cmd_label)
        
        # 命令文本框
        self.cmd_text = QLineEdit(self.cmd)
        self.cmd_text.setReadOnly(True)
        layout.addWidget(self.cmd_text)

        # 输出文本框
        output_label = QLabel("安装输出:")
        layout.addWidget(output_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        # 设置等宽字体以更好地显示命令输出
        font = self.output_text.font()
        font.setFamily("Consolas")
        self.output_text.setFont(font)
        layout.addWidget(self.output_text)

        # 状态标签
        self.status_label = QLabel("正在安装...")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)

        # 关闭按钮（初始隐藏）
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        self.close_button.hide()
        layout.addWidget(self.close_button)

    def append_output(self, text):
        self.output_text.append(text)
        # 强制立即更新显示
        QApplication.processEvents()
        # 滚动到底部
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_finished(self, success, message):
        if success:
            self.status_label.setText("✅ " + message)
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("❌ " + message)
            self.status_label.setStyleSheet("color: red;")
        self.close_button.show()

class DependencyInstaller(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python依赖安装工具")
        self.setGeometry(100, 100, 1000, 600)
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 依赖文件选择区域
        req_layout = QHBoxLayout()
        self.req_path = QLineEdit()
        self.req_path.setPlaceholderText("选择requirements.txt文件路径")
        req_btn = QPushButton("选择文件")
        req_btn.clicked.connect(self.select_requirements)
        req_layout.addWidget(QLabel("依赖文件:"))
        req_layout.addWidget(self.req_path)
        req_layout.addWidget(req_btn)
        layout.addLayout(req_layout)
        
        # Python环境选择区域
        python_layout = QHBoxLayout()
        self.python_path = QLineEdit()
        self.python_path.setPlaceholderText("选择Python环境路径")
        python_btn = QPushButton("选择文件夹")
        python_btn.clicked.connect(self.select_python_path)
        python_layout.addWidget(QLabel("Python环境:"))
        python_layout.addWidget(self.python_path)
        python_layout.addWidget(python_btn)
        layout.addLayout(python_layout)
        
        # 镜像源选择
        mirror_layout = QHBoxLayout()
        self.mirror_combo = QComboBox()
        self.mirror_combo.addItems([
            "默认源",
            "阿里云 https://mirrors.aliyun.com/pypi/simple/",
            "清华源 https://pypi.tuna.tsinghua.edu.cn/simple",
            "豆瓣源 https://pypi.doubanio.com/simple/"
        ])
        mirror_layout.addWidget(QLabel("pip镜像源:"))
        mirror_layout.addWidget(self.mirror_combo)
        layout.addLayout(mirror_layout)
        
        # 依赖列表
        self.dep_table = QTableWidget()
        self.dep_table.setColumnCount(4)
        self.dep_table.setHorizontalHeaderLabels(["依赖项", "要求版本", "安装状态", "操作"])
        # 设置列宽比例
        self.dep_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # 依赖项列自适应
        self.dep_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 版本列适应内容
        self.dep_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 状态列适应内容
        self.dep_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)  # 操作列固定宽度
        self.dep_table.setColumnWidth(3, 150)  # 增加操作列宽度到150像素
        layout.addWidget(self.dep_table)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.do_refresh)
        install_all_btn = QPushButton("全部安装")
        uninstall_all_btn = QPushButton("全部卸载")
        
        install_all_btn.clicked.connect(self.install_all)
        uninstall_all_btn.clicked.connect(self.uninstall_all)
        
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(install_all_btn)
        btn_layout.addWidget(uninstall_all_btn)
        layout.addLayout(btn_layout)
        
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

    def do_refresh(self):
        """处理刷新按钮点击事件"""
        # 检查是否选择了requirements.txt文件
        if not self.req_path.text():
            QMessageBox.warning(self, "警告", "请先选择requirements.txt文件")
            return
        if not os.path.exists(self.req_path.text()):
            QMessageBox.warning(self, "警告", "所选的requirements.txt文件不存在")
            return
            
        # 检查是否选择了Python环境
        if not self.python_path.text():
            QMessageBox.warning(self, "警告", "请先选择Python环境目录")
            return
            
        python_exe = os.path.join(self.python_path.text(), "python.exe")
        if not os.path.exists(python_exe):
            QMessageBox.warning(self, "警告", "所选目录不包含python.exe文件")
            return
            
        # 测试Python环境
        try:
            cmd = f'"{python_exe}" -c "import sys; print(sys.executable)"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                QMessageBox.warning(
                    self,
                    "警告",
                    "所选Python环境可能无法正常工作，请检查是否选择了正确的Python目录"
                )
                return
        except Exception as e:
            QMessageBox.warning(
                self,
                "警告",
                f"测试Python环境时出错: {str(e)}"
            )
            return
            
        # 所有检查都通过，执行刷新
        self.refresh_dependencies()
        self.status_label.setText("刷新完成")

    def select_requirements(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择requirements.txt文件",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.req_path.setText(file_path)
            if self.python_path.text() and os.path.exists(os.path.join(self.python_path.text(), "python.exe")):
                self.refresh_dependencies()
            else:
                QMessageBox.information(self, "提示", "请选择Python环境目录")
                self.dep_table.setRowCount(0)  # 清空依赖列表
            
    def select_python_path(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择Python环境目录"
        )
        if folder_path:
            python_exe = os.path.join(folder_path, "python.exe")
            if os.path.exists(python_exe):
                self.python_path.setText(folder_path)
                # 测试Python环境
                try:
                    cmd = f'"{python_exe}" -c "import sys; print(sys.executable)"'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.refresh_dependencies()
                    else:
                        QMessageBox.warning(
                            self,
                            "警告",
                            "所选Python环境可能无法正常工作，请检查是否选择了正确的Python目录"
                        )
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "警告",
                        f"测试Python环境时出错: {str(e)}"
                    )
            else:
                QMessageBox.warning(
                    self,
                    "警告",
                    "所选目录不包含python.exe文件，请选择正确的Python环境目录"
                )
        
    def get_installed_version(self, package_name):
        try:
            # 如果是git仓库格式，提取包名
            if package_name.startswith('git+'):
                # 从URL中提取包名
                package_name = os.path.splitext(os.path.basename(package_name))[0]
            else:
                # 如果包名包含可选依赖（如 package[extra]），只取基础包名
                package_name = package_name.split('[')[0]
            return pkg_resources.get_distribution(package_name).version
        except (pkg_resources.DistributionNotFound, Exception):
            return None
        
    def refresh_dependencies(self):
        if not self.req_path.text() or not os.path.exists(self.req_path.text()):
            QMessageBox.warning(self, "警告", "请先选择有效的requirements.txt文件")
            return
            
        if not self.python_path.text() or not os.path.exists(os.path.join(self.python_path.text(), "python.exe")):
            QMessageBox.warning(self, "警告", "请先选择有效的Python环境目录")
            self.dep_table.setRowCount(0)  # 清空依赖列表
            return
            
        try:
            with open(self.req_path.text(), 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            self.dep_table.setRowCount(len(requirements))
            
            for i, req in enumerate(requirements):
                # 解析包名和版本要求
                if req.startswith('git+'):
                    # 处理git仓库格式的依赖
                    package_name = req
                    required_version = "git仓库"
                else:
                    # 处理带环境标记的依赖
                    if ';' in req:
                        package_spec, env_marker = req.split(';', 1)
                        package_spec = package_spec.strip()
                        env_marker = env_marker.strip()
                    else:
                        package_spec = req
                        env_marker = ""

                    # 处理标准pip包格式的依赖
                    if '==' in package_spec:
                        package_name, required_version = package_spec.split('==', 1)
                    else:
                        # 处理其他格式的版本要求（如 >=, <=, ~=, > 等）
                        package_name = package_spec
                        for op in ['>=', '<=', '~=', '>', '<', '=']:
                            if op in package_spec:
                                package_name = package_spec.split(op)[0].strip()
                                required_version = package_spec[len(package_name):].strip()
                                break
                        else:
                            required_version = "任意"
                    
                    # 如果有环境标记，添加到版本信息中
                    if env_marker:
                        required_version = f"{required_version} ; {env_marker}" if required_version != "任意" else f"; {env_marker}"
                
                # 获取已安装版本
                try:
                    installed_version = self.get_installed_version(package_name.split('/')[-1].replace('.git', '') if package_name.startswith('git+') else package_name)
                    status = f"已安装 ({installed_version})" if installed_version else "未安装"
                except:
                    installed_version = None
                    status = "未安装"
                
                # 设置表格内容
                self.dep_table.setItem(i, 0, QTableWidgetItem(package_name.strip()))
                self.dep_table.setItem(i, 1, QTableWidgetItem(required_version.strip()))
                self.dep_table.setItem(i, 2, QTableWidgetItem(status))
                
                # 添加安装/卸载按钮
                is_installed = installed_version is not None
                btn = QPushButton("卸载" if is_installed else "安装")
                
                # 设置按钮样式
                if is_installed:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #d9534f;
                            color: white;
                            border: none;
                            border-radius: 0px;
                            padding: 0px;
                            margin: 0px;
                            font-size: 12pt;
                            font-family: "Microsoft YaHei";
                            text-align: center;
                            width: 100%;
                            height: 100%;
                        }
                        QPushButton:hover {
                            background-color: #c9302c;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #337ab7;
                            color: white;
                            border: none;
                            border-radius: 0px;
                            padding: 0px;
                            margin: 0px;
                            font-size: 12pt;
                            font-family: "Microsoft YaHei";
                            text-align: center;
                            width: 100%;
                            height: 100%;
                        }
                        QPushButton:hover {
                            background-color: #286090;
                        }
                    """)
                
                btn.clicked.connect(lambda checked, row=i: self.handle_package_action(row))
                self.dep_table.setCellWidget(i, 3, btn)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"刷新依赖列表时出错: {str(e)}")

    def get_pip_command(self):
        if not self.python_path.text():
            return None
            
        python_exe = os.path.join(self.python_path.text(), "python.exe")
        if not os.path.exists(python_exe):
            QMessageBox.warning(self, "警告", f"Python解释器不存在: {python_exe}")
            return None
            
        # 使用完整路径，并确保使用正斜杠
        return f'"{python_exe.replace(os.sep, "/")}" -m pip'

    def get_mirror_url(self):
        mirror_text = self.mirror_combo.currentText()
        if "默认源" in mirror_text:
            return ""
        return f"-i {mirror_text.split()[-1]}"

    def handle_package_action(self, row):
        package_name = self.dep_table.item(row, 0).text()
        required_version = self.dep_table.item(row, 1).text()
        
        try:
            # 获取基础包名用于检查安装状态
            if package_name.startswith('git+'):
                base_package = os.path.splitext(os.path.basename(package_name))[0]
            else:
                base_package = package_name.split('[')[0]
            
            installed_version = self.get_installed_version(base_package)
            
            if installed_version:
                self.uninstall_package(base_package)  # 卸载时使用基础包名
            else:
                self.install_package(package_name, required_version)  # 安装时使用完整包名
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理依赖时出错: {str(e)}")

    def uninstall_all(self):
        reply = QMessageBox.question(
            self,
            "确认卸载",
            "确定要卸载所有依赖吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
            
        for row in range(self.dep_table.rowCount()):
            package_name = self.dep_table.item(row, 0).text()
            installed_version = self.get_installed_version(package_name)
            if installed_version:
                self.uninstall_package(package_name)

    def install_all(self):
        if not self.req_path.text() or not os.path.exists(self.req_path.text()):
            QMessageBox.warning(self, "警告", "请先选择有效的requirements.txt文件")
            return
            
        pip_cmd = self.get_pip_command()
        if not pip_cmd:
            QMessageBox.warning(self, "警告", "请先选择Python环境")
            return
            
        mirror_url = self.get_mirror_url()
        cmd = f'{pip_cmd} install -r "{self.req_path.text()}" {mirror_url}'
        
        # 创建并显示安装对话框
        dialog = InstallDialog("所有依赖", cmd, self)
        
        # 创建安装线程
        install_thread = InstallThread(cmd)
        install_thread.output_received.connect(dialog.append_output)
        install_thread.finished.connect(lambda success, msg: self.handle_install_finished(success, msg, dialog))
        
        # 启动线程
        install_thread.start()
        
        # 显示对话框
        dialog.exec_()

    def handle_install_finished(self, success, message, dialog):
        try:
            dialog.set_finished(success, message)
            if success:
                self.status_label.setText(f"成功安装 {dialog.package_name}")
                # 安装成功后等待一小段时间再刷新，确保pip已经完成所有操作
                QTimer.singleShot(1000, self.refresh_dependencies)
            else:
                self.status_label.setText(f"安装失败: {dialog.package_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理安装结果时出错: {str(e)}")

    def install_package(self, package_name, version=""):
        pip_cmd = self.get_pip_command()
        if not pip_cmd:
            QMessageBox.warning(self, "警告", "请先选择Python环境")
            return
            
        mirror_url = self.get_mirror_url()
        
        if package_name.startswith('git+'):
            # git仓库安装不需要镜像源
            cmd = f'{pip_cmd} install {package_name}'
        else:
            # 标准包安装
            if version and version != "任意":
                if ';' in version:
                    # 处理带环境标记的版本
                    version_spec, env_marker = version.split(';', 1)
                    version_spec = version_spec.strip()
                    env_marker = env_marker.strip()
                    if version_spec:
                        package_spec = f"{package_name}{version_spec}"
                    else:
                        package_spec = package_name
                    package_spec = f"{package_spec} ; {env_marker}"
                elif version.startswith(('>=', '<=', '~=', '>', '<')):
                    # 对于范围版本要求，直接使用原始的版本字符串
                    package_spec = f"{package_name}{version}"
                else:
                    # 对于明确的版本要求，使用 ==
                    package_spec = f"{package_name}=={version}"
            else:
                # 没有版本要求时直接安装最新版
                package_spec = package_name
                
            # 组装完整命令
            cmd_parts = [pip_cmd, "install"]
            if mirror_url:
                cmd_parts.append(mirror_url)
            cmd_parts.append(package_spec)
            cmd = " ".join(cmd_parts)

        try:
            # 创建并显示安装对话框
            dialog = InstallDialog(package_name, cmd, self)
            
            # 创建安装线程
            install_thread = InstallThread(cmd)
            install_thread.output_received.connect(dialog.append_output)
            install_thread.finished.connect(lambda success, msg: self.handle_install_finished(success, msg, dialog))
            
            # 启动线程
            install_thread.start()
            
            # 显示对话框并等待完成
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"安装过程出错: {str(e)}")

    def handle_uninstall_finished(self, success, message, dialog):
        dialog.set_finished(success, message)
        if success:
            self.status_label.setText(f"成功卸载 {dialog.package_name}")
            # 卸载成功后等待一小段时间再刷新，确保pip已经完成所有操作
            QTimer.singleShot(1000, self.refresh_dependencies)
        else:
            self.status_label.setText(f"卸载失败: {dialog.package_name}")

    def uninstall_package(self, package_name):
        pip_cmd = self.get_pip_command()
        if not pip_cmd:
            QMessageBox.warning(self, "警告", "请先选择Python环境")
            return
            
        # 如果包名包含可选依赖，只取基础包名
        base_package = package_name.split('[')[0]
            
        reply = QMessageBox.question(
            self,
            "确认卸载",
            f"确定要卸载 {base_package} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
            
        cmd = f'{pip_cmd} uninstall -y {base_package}'
        
        # 创建并显示卸载对话框
        dialog = InstallDialog(f"卸载 {package_name}", cmd, self)
        
        # 创建卸载线程
        install_thread = InstallThread(cmd)
        install_thread.output_received.connect(dialog.append_output)
        install_thread.finished.connect(lambda success, msg: self.handle_uninstall_finished(success, msg, dialog))
        
        # 启动线程
        install_thread.start()
        
        # 显示对话框
        dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = app.font()
    font.setFamily("Microsoft YaHei")  # 使用微软雅黑
    font.setPointSize(10)  # 设置字体大小
    app.setFont(font)
    
    # 设置全局样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QLabel {
            font-size: 10pt;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #ddd;
            border-radius: 3px;
            background-color: white;
            font-size: 10pt;
        }
        QComboBox {
            padding: 5px;
            border: 1px solid #ddd;
            border-radius: 3px;
            background-color: white;
            font-size: 10pt;
        }
        QPushButton {
            padding: 5px 15px;
            font-size: 10pt;
        }
        QTableWidget {
            font-size: 10pt;
            border: 1px solid #ddd;
            background-color: white;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 5px;
            border: none;
            border-right: 1px solid #ddd;
            border-bottom: 1px solid #ddd;
            font-weight: bold;
        }
    """)
    
    window = DependencyInstaller()
    window.show()
    sys.exit(app.exec_()) 