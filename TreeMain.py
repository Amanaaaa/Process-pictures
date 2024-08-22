from PIL import Image
import xml.etree.ElementTree as ET


def parse_xml(xml_file):
    """
    解析XML文件，提取所有标注框信息。
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # 获取图像尺寸
    size_element = root.find('size')
    width = int(size_element.find('width').text)
    height = int(size_element.find('height').text)

    boxes = []
    for obj in root.findall('object'):
        name = obj.find('name').text
        bbox = obj.find('bndbox')
        xmin = int(bbox.find('xmin').text)
        ymin = int(bbox.find('ymin').text)
        xmax = int(bbox.find('xmax').text)
        ymax = int(bbox.find('ymax').text)

        # 计算宽度和高度
        box_width = xmax - xmin
        box_height = ymax - ymin

        # 计算中心点坐标
        center_x = xmin + box_width // 2
        center_y = ymin + box_height // 2

        boxes.append((name, xmin, ymin, box_width, box_height, center_x, center_y))

    return boxes, width, height


def find_geometric_center(boxes):
    """
    找到所有标注框中心点的几何中心。
    """
    centers_x = [box[5] for box in boxes]
    centers_y = [box[6] for box in boxes]

    # 计算几何中心
    geometric_center_x = sum(centers_x) / len(centers_x)
    geometric_center_y = sum(centers_y) / len(centers_y)

    return geometric_center_x, geometric_center_y


def find_dividing_line(geometric_center_x, width):
    """
    根据几何中心和图像宽度确定分割线的位置。
    """
    # 分割线位于几何中心x坐标的垂直线上
    dividing_line = geometric_center_x

    # 如果几何中心在图像的右侧，则将分割线调整到左侧
    if dividing_line > width / 2:
        dividing_line = width - dividing_line

    return dividing_line


def calculate_distance_to_dividing_line(center_x, dividing_line):
    """
    计算标注框中心点到分割线的距离。
    """
    return abs(center_x - dividing_line)


def sort_boxes_by_side(boxes, dividing_line, width):
    """
    根据中心点坐标对标注框进行排序，先按左右分组，再按自上而下的顺序排列。
    """
    # 检查是否有3个或更少的标注框
    if len(boxes) <= 3:
        # 计算每个标注框中心点到分割线的距离
        distances = [calculate_distance_to_dividing_line(box[5], dividing_line) for box in boxes]

        # 计算最小标注框的半径
        min_radius = min([box[3] / 2 for box in boxes])

        # 检查所有距离是否都小于最小半径
        if all(distance < min_radius for distance in distances):
            # 直接按照从上到下的顺序排序
            sorted_boxes = sorted(boxes, key=lambda x: x[6])
            return sorted_boxes

    # 如果不是上述情况，继续按照原逻辑执行
    left_boxes = [box for box in boxes if box[5] < dividing_line]
    right_boxes = [box for box in boxes if box[5] >= dividing_line]

    # 左侧按y坐标升序排序
    left_sorted = sorted(left_boxes, key=lambda x: x[6])
    # 右侧按y坐标升序排序
    right_sorted = sorted(right_boxes, key=lambda x: x[6])

    # 如果只有一边有标注框
    if not left_boxes:
        return right_sorted
    elif not right_boxes:
        return left_sorted

    # 合并排序后的结果
    sorted_boxes = left_sorted + right_sorted

    return sorted_boxes


def update_xml(xml_file, sorted_boxes, width, height, output_folder):
    """
    更新XML文件中的标注框顺序，并保存到输出文件夹。
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # 更新图像尺寸
    size_element = root.find('size')
    size_element.find('width').text = str(width)
    size_element.find('height').text = str(height)

    # 移除原有的object标签
    for obj in root.findall('object'):
        root.remove(obj)

    # 添加新的object标签
    for box in sorted_boxes:
        obj = ET.SubElement(root, 'object')
        name = ET.SubElement(obj, 'name')
        name.text = box[0]

        bndbox = ET.SubElement(obj, 'bndbox')
        xmin = ET.SubElement(bndbox, 'xmin')
        xmin.text = str(box[1])
        ymin = ET.SubElement(bndbox, 'ymin')
        ymin.text = str(box[2])
        xmax = ET.SubElement(bndbox, 'xmax')
        xmax.text = str(box[1] + box[3])
        ymax = ET.SubElement(bndbox, 'ymax')
        ymax.text = str(box[2] + box[4])

    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 构造输出文件路径
    output_file_path = os.path.join(output_folder, os.path.basename(xml_file))

    # 写入更新后的XML文件
    tree.write(output_file_path)

    return output_file_path


def process_files(input_folder, output_folder):
    """
    处理指定文件夹下的所有XML文件，并将处理后的文件保存到另一个指定文件夹。
    """
    # 遍历输入文件夹中的所有文件
    for file_name in os.listdir(input_folder):
        if file_name.endswith('.xml'):
            xml_file = os.path.join(input_folder, file_name)
            boxes, width, height = parse_xml(xml_file)
            geometric_center_x, _ = find_geometric_center(boxes)
            dividing_line = find_dividing_line(geometric_center_x, width)
            sorted_boxes = sort_boxes_by_side(boxes, dividing_line, width)
            output_file_path = update_xml(xml_file, sorted_boxes, width, height, output_folder)
            # print(f"Processed {file_name} and saved to {output_file_path}")


def extract_number_from_basename(basename):
    """
    从basename字符串中提取最后一个左括号后面的第一个数字，并返回去除左括号后面字符并且去除左括号前面的“-”之后的basename字符串。

    :param basename: 输入的basename字符串
    :return: 一个元组 (number, new_basename)，其中 number 是最后一个左括号后面的第一个数字，
             new_basename 是去除左括号后面字符并且去除左括号前面的“-”之后的basename字符串
    """
    # 寻找最后一个左括号（中文或英文）的位置
    last_left_parenthesis_index = max(basename.rfind('（'), basename.rfind('('))

    # 如果找不到左括号，则返回None
    if last_left_parenthesis_index == -1:
        return -1, None

    # 提取括号内的字符串
    number_str = basename[last_left_parenthesis_index + 1:]

    # 寻找第一个完整的数字
    first_number = None
    for i, char in enumerate(number_str):
        if char.isdigit():
            # 开始寻找数字
            if first_number is None:
                first_number = ''
            first_number += char
        else:
            # 结束寻找数字
            if first_number is not None:
                break

    if first_number is not None:
        number = int(first_number)
    else:
        number = -1

    # 构建新的basename
    new_basename = basename[:last_left_parenthesis_index].rstrip('-')

    return number, new_basename


# def crop_image_based_on_xml(xml_file, image_file, output_dir, update_info_callback=None):
#     # 解析XML文件
#     tree = ET.parse(xml_file)
#     root = tree.getroot()
#
#     # 加载图像
#     img = Image.open(image_file)
#
#     # 遍历所有<object>标签
#     for idx, obj in enumerate(root.findall('object')):
#         bndbox = obj.find('bndbox')
#         # 获取当前的边界框坐标
#         xmin = int(bndbox.find('xmin').text)
#         ymin = int(bndbox.find('ymin').text)
#         xmax = int(bndbox.find('xmax').text)
#         ymax = int(bndbox.find('ymax').text)
#
#         # 裁剪图像
#         cropped_img = img.crop((xmin, ymin, xmax, ymax))
#
#         # 构建输出文件路径
#         base_name, ext = os.path.splitext(os.path.basename(image_file))
#         output_dir1 = os.path.join(output_dir, base_name)
#         os.makedirs(output_dir1, exist_ok=True)
#
#         result, new_basename = extract_number_from_basename(base_name)
#         if result >= 0:
#             output_image_file = os.path.join(output_dir1, f"{new_basename}-{idx + result}.jpg")
#         else:
#             output_image_file = os.path.join(output_dir1, f"{base_name}-{idx}.jpg")
#
#         # 保存裁剪后的图像
#         cropped_img.save(output_image_file)
#
#         # Update the info text in the GUI
#         if update_info_callback:
#             update_info_callback(f"<font color='green'>Split finished! saved to{output_image_file}</font>")
def crop_image_based_on_xml(xml_file, image_file, output_dir, gui_instance=None):
    # 解析XML文件
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # 加载图像
    img = Image.open(image_file)

    # 遍历所有<object>标签
    for idx, obj in enumerate(root.findall('object')):
        bndbox = obj.find('bndbox')
        # 获取当前的边界框坐标
        xmin = int(bndbox.find('xmin').text)
        ymin = int(bndbox.find('ymin').text)
        xmax = int(bndbox.find('xmax').text)
        ymax = int(bndbox.find('ymax').text)

        # 裁剪图像
        cropped_img = img.crop((xmin, ymin, xmax, ymax))

        # 构建输出文件路径
        base_name, ext = os.path.splitext(os.path.basename(image_file))
        output_dir1 = str(os.path.join(output_dir, base_name))
        os.makedirs(output_dir1, exist_ok=True)

        result, new_basename = extract_number_from_basename(base_name)

        if result >= 0:
            output_image_file = os.path.join(output_dir1, f"{new_basename}-{idx + result}.jpg")
        else:
            output_image_file = os.path.join(output_dir1, f"{base_name}-{idx}.jpg")

        # 保存裁剪后的图像
        cropped_img.save(output_image_file)

        # 发送信号更新文本框信息
        if gui_instance:
            gui_instance.image_cropped_signal.emit(f"已裁剪图片: {output_image_file}")


import os


def main1(input_folder, output_folder):
    """标签排序，先左右，后上下"""
    process_files(input_folder, output_folder)


def main2(input_dir, xml_dir, output_dir, gui_instance):
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 遍历XML文件夹中的所有XML文件
    for file_name in os.listdir(xml_dir):
        if file_name.endswith('.xml'):
            xml_file = os.path.join(xml_dir, file_name)
            image_file = os.path.join(input_dir, file_name.replace('.xml', '.jpg'))
            crop_image_based_on_xml(xml_file, image_file, output_dir, gui_instance)


# def main3():
#     """移动子文件下的所有文件到指定单个文件夹"""
#     source_folder = r"C:\Users\A\Desktop\yousong\corp"  # 源文件夹地址
#     target_folder = r"C:\Users\A\Desktop\cc\corp"  # 目标文件夹地址
#     os.makedirs(target_folder, exist_ok=True)
#     # 遍历源文件夹及其子文件夹下的所有文件
#     for root, dirs, files in os.walk(source_folder):
#         for file in files:
#             source_file_path = os.path.join(root, file)  # 源文件路径
#             target_file_path = os.path.join(target_folder, file)  # 目标文件路径
#             # 移动文件到目标文件夹
#             shutil.move(source_file_path, target_file_path)
#             # print(f"Moved {source_file_path} to {target_file_path}")


if __name__ == "__main__":
    main1()  # 标签排序
    main2()  # 标签裁剪
#  main3()  # 移动图片
