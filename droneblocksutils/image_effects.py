import cv2
import numpy as np
import time

def _clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

def _kernel_generator(size):
    kernel = np.zeros((size, size), dtype=np.int8)
    for i in range(size):
        for j in range(size):
            if i < j:
                kernel[i][j] = -1
            elif i > j:
                kernel[i][j] = 1
    return kernel


def _exponential_function(channel, exp):
    table = np.array([min((i ** exp), 255) for i in np.arange(0, 256)]).astype(
        "uint8")  # generating table for exponential function
    channel = cv2.LUT(channel, table)
    return channel


def duo_tone(img):
    # 7010
    # 7020
    # 2120
    exp = 2 # 0-10
    exp = 1 + exp / 100  # converting exponent to range 1-2
    s1 = 1 # 1-2
    s2 = 2 # 3-3
    s3 = 0 # 0-1
    res = img.copy()
    for i in range(3):
        if i in (s1, s2):  # if channel is present
            res[:, :, i] = _exponential_function(res[:, :, i], exp)  # increasing the values if channel selected
        else:
            if s3:  # for light
                res[:, :, i] = _exponential_function(res[:, :, i],
                                                     2 - exp)  # reducing value to make the channels light
            else:  # for dark
                res[:, :, i] = 0  # converting the whole channel to 0
    return res


def emboss(img, emboss_size=3):

    emboss_size = _clamp(emboss_size, 2, 10)  # adding 2 to kernel as it a size of 2 is the minimum required.
    s = 0
    height, width = img.shape[:2]
    y = np.ones((height, width), np.uint8) * 128
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    kernel = _kernel_generator(emboss_size)  # generating kernel for bottom left kernel
    kernel = np.rot90(kernel, s)  # switching kernel according to direction
    res = cv2.add(cv2.filter2D(gray, -1, kernel), y)

    return res

def sepia(sepia_image):
    # sepia_image = cv2.cvtColor(sepia_image, cv2.COLOR_BGR2RGB)  # converting to RGB as sepia matrix is for RGB
    sepia_image = np.array(sepia_image, dtype=np.float64)
    sepia_image = cv2.transform(sepia_image, np.matrix([[0.393, 0.769, 0.189],
                                                        [0.349, 0.686, 0.168],
                                                        [0.272, 0.534, 0.131]]))
    sepia_image[np.where(sepia_image > 255)] = 255  # clipping values greater than 255 to 255
    sepia_image = np.array(sepia_image, dtype=np.uint8)
    sepia_image = cv2.cvtColor(sepia_image, cv2.COLOR_RGB2BGR)

    return sepia_image

_style_model = None
_models = [
    "./models/starry_night.t7",
    "./models/candy.t7",
    "./models/feathers.t7",
    "./models/la_muse.t7",
    "./models/the_scream.t7",
    "./models/udnie.t7",
    "./models/mosaic.t7"

]

_model_index = 0

_time_between_styles = 3 # in seconds
_style_start_time = 0

def apply_style_transfer(frame, time_in_seconds=3):
    """
    Apply all of the style models for 'time_in_seconds' and then switch to a new style model
    :param frame: Image to apply the style model to
    :type frame:
    :param time_in_seconds: Number of seconds to apply the style model before moving to another style model
    :type time_in_seconds:
    :return:
    :rtype:
    """
    global _time_between_styles, _style_start_time, _model_index

    _time_between_styles = time_in_seconds
    if time.time() - _style_start_time > _time_between_styles:
        _style_start_time = time.time()
        reset_style_model()
        if _model_index == len(_models)-1:
            _model_index = 0
        else:
            _model_index += 1

    new_image = style_transfer(frame, _models[_model_index])
    return new_image


def reset_style_model():
    global  style_model
    style_model = None

def style_transfer(image, model_path):
    global style_model
    style_model = None

    # check to make sure we have an image to operate on
    if image is None:
        return image

    if style_model is None:
        style_model = cv2.dnn.readNetFromTorch(model_path)

    (h, w) = image.shape[:2]

    # construct a blob from the image, set the input, and then perform a
    # forward pass of the network
    blob = cv2.dnn.blobFromImage(image, 1.0, (w, h),
                                 (103.939, 116.779, 123.680), swapRB=False, crop=False)
    style_model.setInput(blob)
    output = style_model.forward()

    # reshape the output tensor, add back in the mean subtraction, and
    # then swap the channel ordering
    output = output.reshape((3, output.shape[2], output.shape[3]))
    output[0] += 103.939
    output[1] += 116.779
    output[2] += 123.680
    output /= 255.0
    output = output.transpose(1, 2, 0)

    return output

def line_drawing(image, inverse_image=True):
    """
    Convert an image into a line drawing highlighting the difference between light and dark edges
    :param image: The RGB image to modify
    :type image:
    :param inverse_image: True - black background with white lines.  False - white background with black lines
    :type inverse_image:
    :return: Image with visual effect applied
    :rtype: Image
    """
    threshold = 7
    block_size = 4
    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Changing last value higher makes lighter, but weird ,changing second to last value makes lines stronger
    if inverse_image:
        image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, threshold, block_size)
    else:
        image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, threshold, block_size)
    # cv.GaussianBlur(frame, (5, 5), -1)
    # image = cv2.medianBlur(image, 3)

    return image


def derivative(image):
    # "derivative", a very weird effect
    kern = np.array([[0, 0, 0], [-5.0, 0.0, 5.0], [0, 0, 0]])
    image = cv2.filter2D(image, -1, kern)

    return image

def inverse(image):
    image = cv2.bitwise_not(image)

    return image

def canny(image, min_value=75, max_value=170):
    image = cv2.Canny(image, min_value, max_value)
    return image


def oil_painting(image, neighbouring_size=7 ):
    """
    Convert an image to look as though it has been oil painted
    :param image: Original Image
    :type image: Image
    :param neighbouring_size: number of pixels to consider.  A lower number results in a more precise recreation.  A higher number makes the painting more abstract
    :type neighbouring_size:
    :return: Image with an oil painting visual effect
    :rtype: Image
    """
    dyn_ratio = 1
    res = cv2.xphoto.oilPainting(image, neighbouring_size, dyn_ratio)
    return res

def water_color(image):
    """
    Convert an image to look as though it has been painted with water colors
    :param image: Original Image in RGB format
    :type image:
    :return: Image with a water color visual effect
    :rtype: Image
    """

    # sigma_s controls the size of the neighborhood. Range 1 - 200
    # sigma_r controls the how dissimilar colors within the neighborhood will
    # be averaged. A larger sigma_r results in large regions of constant color.
    # Range 0 - 1
    res = cv2.stylization(image, sigma_s=60, sigma_r=0.8)
    return res

def pencil_sketch(image, color=True):
    """
    Convert an image to look as though it has been pencil sketched
    :param image: Original Image in RGB Format
    :type image:
    :param color: True - color pencil sketch, False - Gray scale pencil sketch
    :type color:
    :return: Image with a pencil sketch visual effect
    :rtype:
    """
    # sigma_s and sigma_r are the same as in stylization.
    # shade_factor is a simple scaling of the output image intensity. The higher the value, the brighter is the result. Range 0 - 0.1

#    dst_gray, dst_color = cv2.pencilSketch(image, sigma_s=60, sigma_r=0.07, shade_factor=0.05)

    dst_gray, dst_color = cv2.pencilSketch(image, sigma_s=60, sigma_r=0.04, shade_factor=0.1)
    if color:
        return dst_color
    else:
        return dst_gray

def enhance_details(image):
    res = cv2.detailEnhance(image, sigma_s=10, sigma_r=0.15)
    return res