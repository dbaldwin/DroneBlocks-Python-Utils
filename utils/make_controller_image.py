import cv2
import numpy as np

if __name__ == '__main__':
    dim = (250,250)
    left_img = cv2.imread('./droneblocks/media/tello-controller-left.jpeg')
    left_img = cv2.resize(left_img, dim,  interpolation = cv2.INTER_AREA)
    print(left_img.shape)
    right_img = cv2.imread('./droneblocks/media/tello-controller-right.jpeg')
    right_img = cv2.resize(right_img, dim,  interpolation = cv2.INTER_AREA)
    print(right_img.shape)

    numpy_horizontal = np.hstack((left_img, right_img))

    cv2.imshow("result", numpy_horizontal)

    cv2.waitKey()

    cv2.imwrite('./droneblocks/media/tello-controller.png', numpy_horizontal)
