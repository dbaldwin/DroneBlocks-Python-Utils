import pkgutil
import sys

from droneblocks.uielements import SolidColorRect, CircleButton, RectButton
import csv
import numpy as np
import argparse
import cv2
from droneblocks.uielements import read_image
from pathlib import Path

def read_normalized_rects_from_file(filename):
    rects = []

    with open(filename, "r") as f:
        csv_reader = csv.reader(f, delimiter=',')
        for row in csv_reader:
            row = list(np.float_(row))
            rects.append((row[0], row[1], row[2], row[3]))
    return rects


def denormalize_rectangles(rect_list, image_width, image_height):
    denorm_rects = []
    for rect in rect_list:
        x1 = rect[0] * image_width
        y1 = rect[1] * image_height
        x2 = rect[2] * image_width
        y2 = rect[3] * image_height
        denorm_rects.append((int(x1), int(y1), int(x2), int(y2)))

    return denorm_rects


def create_solidcolor_rects(rect_list):
    solid_rects = []
    for rect in rect_list:
        solid_rects.append(SolidColorRect(rect, colors=[(0,0,255), (255,0,0), (255, 32, 240)]))

    return solid_rects


solid_rects_to_show = []
ui_elements = []
solid_rects = None
copy_of_image=None

def _clear_solid_rects():
    global solid_rects_to_show
    solid_rects_to_show=[]
    for i, solid_rect in enumerate(solid_rects):
        solid_rect.reset_color_index()

def mouse_events(event, x, y,
                 flags, param):
    global image

    if event == cv2.EVENT_LBUTTONDOWN:
        for i, solid_rect in enumerate(solid_rects):
            if solid_rect.is_point_inside(x, y):
                solid_rect.process_point(x,y, image)
                for solid_rect_to_show in solid_rects_to_show:
                    if solid_rect_to_show.id == solid_rect.id:
                        break
                else:
                    solid_rects_to_show.append(solid_rect)

    if event == cv2.EVENT_RBUTTONDOWN:
        for i, solid_rect in enumerate(solid_rects_to_show):
            if solid_rect.is_point_inside(x, y):
                solid_rect.reset_color_index()
                del solid_rects_to_show[i]

    image = copy_of_image.copy()
    for solid_rect in solid_rects_to_show:
        solid_rect.draw(image)

    for ui_element in ui_elements:
        ui_element.process_point(x, y, image, event)
        ui_element.draw(image)

    cv2.imshow(WINDOW_NAME, image)




WINDOW_NAME = 'DroneBlocks TT Pattern Generator'


def _generate_display_string():
    global flattened_image
    tt_colors = ['r', 'b', 'p']
    flatten_display_color_values = []
    for solid_rect in solid_rects:
        for solid_rect_to_show in solid_rects_to_show:
            if solid_rect.id == solid_rect_to_show.id:
                flatten_display_color_values.append(tt_colors[solid_rect.color_index])
                break
        else:
            flatten_display_color_values.append('0')
    flattened_image = ''.join(flatten_display_color_values)
    print(f'image_string = "{flattened_image}"')

def _close_window():
    cv2.destroyAllWindows()
    sys.exit(0)

def main():
    global solid_rects, copy_of_image
    """
    --image-path
./images/8x8matrix_expansion.png
--filename
./hotspots/8x8-matrix-hotspots2.csv
--width
600
--mask-transparent
    """

    ap = argparse.ArgumentParser()
    ap.add_argument("--image-path", type=str, required=False, default="./media/8x8matrix_expansion.png", help="Path to the image to load")
    ap.add_argument("--width", type=int, required=False, default=600, help="Resize image to specified width")
    ap.add_argument("--height", type=int, required=False, default=None, help="Resize image to specified height")

    ap.add_argument("--filename", required=False, default="./data/8x8-matrix-hotspots2.csv",
                    help="Optional. Filename to save hotspot data if provided")

    args = vars(ap.parse_args())

    image_path = args['image_path']
    width = args['width']
    height = args['height']
    filename = args['filename']

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, mouse_events)

    image = read_image(image_path, width, height, True)
    if image is None:
        raise(f"Could not locate image at: {image_path}")

    if not Path(filename).exists():
        droneblocks_package = pkgutil.get_loader("droneblocks")
        droneblocks_init_file_path = droneblocks_package.get_filename()
        # '/Users/patrickryan/Development/junk-projects/junk11/venv/lib/python3.8/site-packages/droneblocks/__init__.py'
        package_image_path = droneblocks_init_file_path.replace("__init__.py", filename)
        print(package_image_path)
        filename = package_image_path

    solid_rects = create_solidcolor_rects(
        denormalize_rectangles(read_normalized_rects_from_file(filename), image.shape[1], image.shape[0]))

    copy_of_image = image.copy()

    rect_btn = RectButton(int(image.shape[1]*0.25),int(image.shape[0]*.9), "Clear", (255,0,0), (0,0,255), (64,64,64))
    rect_btn.set_click_callback(_clear_solid_rects)
    rect_btn.draw(image)
    ui_elements.append(rect_btn)

    gen_btn = RectButton(int(image.shape[1]*0.1),int(image.shape[0]*.9), "Gen", (255,0,0), (0,0,255), (64,64,64))
    gen_btn.set_click_callback(_generate_display_string)
    gen_btn.draw(image)
    ui_elements.append(gen_btn)

    close_btn = RectButton(int(image.shape[1]*0.70),int(image.shape[0]*.9), "Close", (255,0,0), (0,0,255), (64,64,64))
    close_btn.set_click_callback(_close_window)
    close_btn.draw(image)
    ui_elements.append(close_btn)

    cv2.imshow(WINDOW_NAME, image)
    cv2.waitKey(0)

if __name__ == '__main__':
    main()