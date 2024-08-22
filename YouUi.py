import os
import torch
import ctypes

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, \
    QComboBox, QFileDialog, QGroupBox, QProgressBar, QTextEdit
from PyQt5.QtCore import Qt, QDir
import sys
from PIL import Image
import cv2
import xml.etree.ElementTree as ET
from TreeMain import main1, main2
from PyQt5.QtCore import pyqtSignal






class YOLOv5GUI(QMainWindow):
    image_cropped_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("oip.ico"))
        # 连接信号与槽
        self.image_cropped_signal.connect(self.on_image_cropped)

        self.setWindowTitle("圆盘分割器")
        self.setGeometry(100, 100, 400, 800)

        # 初始化状态
        self.image_files = []  # 存储选择的图片文件列表
        self.model = None  # 用于存储加载的YOLOv5模型

        # 创建主部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 左侧控制面板布局
        left_panel = QVBoxLayout()

        # Input部分
        input_group = QGroupBox("Input")
        input_group.setFixedWidth(350)
        input_group.setFixedHeight(100)
        input_layout = QVBoxLayout()
        self.open_file_button = QPushButton("选择文件夹")
        self.open_file_button.clicked.connect(self.open_folder)
        input_layout.addWidget(self.open_file_button)
        input_group.setLayout(input_layout)
        left_panel.addWidget(input_group)

        # 模型选择部分
        model_group = QGroupBox("Model")
        model_group.setFixedWidth(350)
        model_group.setFixedHeight(200)
        model_layout = QVBoxLayout()
        self.model_combobox = QComboBox()
        self.populate_model_combobox()
        model_layout.addWidget(self.model_combobox)

        # Detect按钮
        self.detect_button = QPushButton("Detect")
        self.detect_button.clicked.connect(self.detect)
        model_layout.addWidget(self.detect_button)

        # 进度条
        self.progress_bar = QProgressBar()
        model_layout.addWidget(self.progress_bar)

        model_group.setLayout(model_layout)
        left_panel.addWidget(model_group)

        # 图片数量显示和开始分割按钮
        self.image_count_label = QLabel()
        left_panel.addWidget(self.image_count_label)

        self.start_button = QPushButton("Split it！")
        self.start_button.clicked.connect(self.start_split)
        self.start_button.setFixedSize(120, 40)
        font = QFont()
        font.setPointSize(14)
        self.start_button.setFont(font)
        self.start_button.setStyleSheet("color: blue;")
        left_panel.addWidget(self.start_button, alignment=Qt.AlignCenter)

        # 处理信息文本框
        self.info_text_edit = QTextEdit()
        self.info_text_edit.setReadOnly(True)
        self.info_text_edit.setFixedHeight(400)
        left_panel.addWidget(self.info_text_edit)

        main_layout.addLayout(left_panel)
        self.setFocusPolicy(Qt.NoFocus)

    def on_image_cropped(self, message):
        self.append_to_info_text(message)

    def populate_model_combobox(self):
        pt_directory = "pt"
        if os.path.exists(pt_directory) and os.path.isdir(pt_directory):
            pt_files = [f for f in os.listdir(pt_directory) if f.endswith(".pt")]
            if pt_files:
                self.model_combobox.addItems(pt_files)
            else:
                self.model_combobox.addItem("No .pt files found")
        else:
            self.model_combobox.addItem("Directory not found")

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", QDir.homePath())
        if folder_path:
            self.image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
                                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
            if self.image_files:
                self.image_count_label.setText(f"共 {len(self.image_files)} 张图片")
            else:
                self.image_count_label.setText("文件夹中没有图片")
            self.input_folder = folder_path  # 保存选择的文件夹路径

    def detect(self):
        if not self.image_files:
            self.append_to_info_text("没有选择图片文件。")
            return

        try:
            # Assuming your model is in a subfolder 'pt' within your project
            model_dir = "pt"
            selected_model_name = self.model_combobox.currentText()
            selected_model_path = os.path.join(model_dir, selected_model_name)

            # Load the YOLOv5 model
            if self.model is None:
                self.model = torch.hub.load('yolov5-master', 'custom', path=selected_model_path,force_reload=True,source='local')
                self.model.eval()  # Set the model to evaluation mode

            # Ensure model loaded successfully
            if self.model is not None:
                self.append_to_info_text("模型加载成功")
            else:
                self.append_to_info_text("模型加载失败")
                return

            # Create folders
            inference_folder = os.path.join(os.path.dirname(self.image_files[0]), 'DetectResults')
            os.makedirs(inference_folder, exist_ok=True)
            self.NeedPath = inference_folder
            txt_folder = os.path.join(inference_folder, 'gen-txt')
            os.makedirs(txt_folder, exist_ok=True)
            self.xml_folder = os.path.join(inference_folder, 'gen-xml')
            os.makedirs(self.xml_folder, exist_ok=True)

            # Batch inference
            num_files = len(self.image_files)
            self.progress_bar.setRange(0, num_files)
            self.progress_bar.setValue(0)

            for i, img_path in enumerate(self.image_files):
                try:
                    # Convert OpenCV image to PIL Image
                    img = cv2.imread(img_path)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(img)

                    # Perform inference
                    results = self.model(img_pil)
                    W, H = img.shape[1], img.shape[0]  # Update dimensions

                    # Save result image
                    result_img = results.render()[0]
                    inferred_image_path = os.path.join(inference_folder, os.path.basename(img_path))
                    cv2.imwrite(inferred_image_path, cv2.cvtColor(result_img, cv2.COLOR_RGB2BGR))

                    # Save bbox txt file
                    txt_file_path = os.path.join(txt_folder,
                                                 os.path.basename(img_path).replace('.jpg', '.txt').replace('.png',
                                                                                                            '.txt'))
                    with open(txt_file_path, 'w') as f:
                        for *box, conf, cls in results.xyxy[0].tolist():
                            f.write(f"{int(cls)} {conf:.2f} {box[0]:.2f} {box[1]:.2f} {box[2]:.2f} {box[3]:.2f}\n")

                    self.append_to_info_text(f"推理后的图片保存到: {inferred_image_path}")

                    # Save dimensions for use in XML conversion
                    self.W = W
                    self.H = H

                    # Convert txt to xml
                    xml_file_path = os.path.join(self.xml_folder,
                                                 os.path.basename(txt_file_path).replace('.txt', '.xml'))
                    self.convert_txt_to_xml(txt_file_path, xml_file_path)

                    # Update progress bar
                    self.progress_bar.setValue(i + 1)

                except Exception as img_error:
                    error_message = f"Error processing image {os.path.basename(img_path)}: {str(img_error)}"
                    self.append_to_info_text(error_message)

            self.info_text_edit.setTextColor(Qt.green)
            self.append_to_info_text("推理完成！请split")
            self.info_text_edit.setTextColor(Qt.black)  # Reset to default color

        except Exception as e:
            error_message = f"Error during detection: {str(e)}"
            self.append_to_info_text(error_message)

    def start_split(self):
        try:
            if not hasattr(self, 'W') or not hasattr(self, 'H'):
                raise ValueError("Image dimensions not set. Run detection first.")
            #
            # print(f"XML Folder: {self.xml_folder}")
            crop_folder = os.path.join(self.NeedPath, "crop")
            os.makedirs(crop_folder, exist_ok=True)
            # print(f"Crop Folder: {crop_folder}")
            # print(f"Input Folder: {self.input_folder}")
            #
            # # Pass the append_to_info_text method as a callback
            # main1(self.xml_folder, self.xml_folder)
            # main2(self.input_folder, self.xml_folder, crop_folder, self.append_to_info_text)

            main1(self.xml_folder, self.xml_folder)
            main2(self.input_folder, self.xml_folder, crop_folder, gui_instance=self)

            html_text = '<font color="green" size="24">圆盘分割成功！</font>'
            self.append_to_info_text(html_text)
        except Exception as e:
            self.append_to_info_text(f"Error during split: {str(e)}")
            print(f"Error during split: {str(e)}")

    def append_to_info_text(self, message):
        self.info_text_edit.append(message)

    def convert_txt_to_xml(self, txt_file_path, xml_file_path):
        try:
            root = ET.Element('annotation')

            # Add image size information
            size = ET.SubElement(root, 'size')
            ET.SubElement(size, 'width').text = str(self.W)
            ET.SubElement(size, 'height').text = str(self.H)
            ET.SubElement(size, 'depth').text = '3'  # Assuming RGB images

            # Parse the TXT file
            with open(txt_file_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 6:
                        cls, conf, xmin, ymin, xmax, ymax = parts

                        obj = ET.SubElement(root, 'object')
                        ET.SubElement(obj, 'name').text = cls
                        ET.SubElement(obj, 'confidence').text = conf

                        bndbox = ET.SubElement(obj, 'bndbox')
                        ET.SubElement(bndbox, 'xmin').text = xmin
                        ET.SubElement(bndbox, 'ymin').text = ymin
                        ET.SubElement(bndbox, 'xmax').text = xmax
                        ET.SubElement(bndbox, 'ymax').text = ymax

            tree = ET.ElementTree(root)
            tree.write(xml_file_path)
            self.append_to_info_text(f"转换完成: {xml_file_path}")
        except Exception as e:
            self.append_to_info_text(f"Error converting {txt_file_path} to XML: {str(e)}")

    def trigger_image_cropped_signal(self, message):
        self.image_cropped_signal.emit(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myappid = 'mycompany.myproduct.subproduct.version'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    window = YOLOv5GUI()
    window.show()
    sys.exit(app.exec_())
