#!/bin/python

import argparse
import random
import numpy as np
import copy
import cv2
import os
from astropy.io import fits
from astropy.utils.data import download_file
import matplotlib.pyplot as plt
from scipy.signal import convolve2d
import scipy.stats as st
from scipy.signal import medfilt2d



def create_artificial_background(image):
    background = np.zeros(image.shape)
    width = image.shape[0] //2
    height = image.shape[1] //2
    background[height:,width:] = -200
    background[height-100:height+100,width-100:width+100] = -200
    background = convolve(background, 86, 'gaussian')
    np.save('data/background_map.npy', background)
    return background

def convolve( image, size, kernel_recipe='gaussian'):
    kernel = None
    if kernel_recipe == 'gaussian':
        if size == 3:
            kernel = np.array([[1/16, 1/8, 1/16],[1/8, 1/4, 1/8],[1/16, 1/8, 1/16]])
        else:
            kernel = gauss_kernel(size)
    if kernel is None:
        raise Exception('Unknown kernel')
    image = convolve2d(image, kernel, mode='same', boundary='fill')
    return image

def gauss_kernel( kernlen=3, sigma=3):
    interval = (2*sigma+1.)/(kernlen)
    x = np.linspace(-sigma-interval/2., sigma+interval/2., kernlen+1)
    kern1d = np.diff(st.norm.cdf(x))
    kernel_raw = np.sqrt(np.outer(kern1d, kern1d))
    kernel = kernel_raw/kernel_raw.sum()
    return kernel

def iterative_sigma_clipping(original_image, preprocessed_image, curr_iter, last_iter_background):
    if curr_iter == 0:
        return original_image - preprocessed_image
    else:
        standard_deviation = np.std(last_iter_background)
        mean_deviation = np.mean(last_iter_background)

        new_iter_background = np.zeros(last_iter_background.shape)
        for num_col in range(last_iter_background.shape[0]):
            for num_row in range(last_iter_background.shape[1]):
                term = np.absolute(last_iter_background[num_col,num_row] - mean_deviation)
                if term < 3*standard_deviation:
                    new_iter_background[num_col,num_row] = last_iter_background[num_col,num_row]
                else:
                    new_iter_background[num_col,num_row] = mean_deviation
        return new_iter_background



def perform_sigma_clipping(original_image, number_of_iterations=5):
    preprocessed_image = image_preprocess(original_image)
    assert original_image.shape == preprocessed_image.shape

    estimated_background = np.zeros(original_image.shape)
    last_iter_background = None
    for curr_iter in range(number_of_iterations):
        estimated_background = iterative_sigma_clipping(original_image, preprocessed_image, curr_iter, last_iter_background)
        last_iter_background = estimated_background
    return preprocessed_image + estimated_background

def image_preprocess(image):
    initial_shape = image.shape
    small_shape = round(initial_shape[0]*0.1), round(initial_shape[1]*0.1)

    image = cv2.resize(image, dsize=small_shape, interpolation=cv2.INTER_CUBIC )
    image = cv2.resize(image, dsize=initial_shape, interpolation=cv2.INTER_CUBIC)

    image = medfilt2d(image.astype(np.uint8), 15)
    image = convolve(image, 15)
    # image = image + random.randint(5,500)
    return image

def show_hist(image):
    flattened = image.flatten()
    x1,x2,y1,y2 = plt.axis()
    plt.hist(flattened, np.unique(flattened).shape[0])
    plt.axis((np.min(flattened)-10, np.max(flattened)+10, 0, 10000))
    plt.show()

def sigma_clipper( image, num_tiles_width = 1, num_tiles_height = 1 , iterations = 5):
    if num_tiles_width != 1 or num_tiles_height != 1:
        tile_rows = np.array_split(image, num_tiles_height)
        final = np.zeros(image.shape)
        curr_x = 0
        curr_y = 0
        for row_i,row in enumerate(tile_rows):
            tiles_in_row = np.array_split(row, num_tiles_width, axis=1)
            tile_shape_1 = None
            for col_i, tile in enumerate(tiles_in_row):
                tile = perform_sigma_clipping(tile, iterations)
                final[curr_y:(curr_y+tile.shape[0]),curr_x:(curr_x+tile.shape[1])] = tile
                curr_x += tile.shape[1]
                tile_shape_1 = tile.shape[0]
            curr_y += tile_shape_1
            curr_x = 0
    else:
        final = perform_sigma_clipping(image, iterations)
    return cv2.blur(final,(30,30))

def fix_sizes(a1, a2):
    if a1.shape == a2.shape:
        return a1,a2
    if a1.shape[0] > a2.shape[0] and a1.shape[1] > a2.shape[1]:
        bigger = a1
        smaller = a2
    else:
        bigger = a2
        smaller = a1
    difference = (bigger.shape[0] - smaller.shape[0],bigger.shape[1] - smaller.shape[1])
    first = difference[0] // 2
    second = difference[1] // 2
    if bigger is a1:
        return a1[first:-first, second:-second], a2
    else:
        return a1, a2[first:-first, second:-second]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="file to extract background from")
    parser.add_argument("-i", help="number of iterations(default = 5)", type=int)
    parser.add_argument("-a", help="file is in absolute path format", action="store_true")
    parser.add_argument("-o", help="name of background file(default = file + _bg)")
    args = parser.parse_args()
    if '/' not in args.file:
        directory = os.getcwd()
        input_file = directory + '/' + args.file.split('/')[-1]
    else:
        if args.a:
            input_file = args.file
            directory = '/'.join(input_file.split('/')[:-1])
        else:
            directory = os.getcwd()
            input_file = directory + '/' + args.file

    image = fits.getdata(input_file)

    file_name, extension = os.path.basename(input_file).split('.')
    if args.i:
        extracted_background = sigma_clipper(image, iterations=args.i)
        my_comment = "Extracted background with {} iterations".format(args.i)
        print(my_comment)
        print(extracted_background)
    else:
        extracted_background = sigma_clipper(image)
        my_comment = "Extracted background with {} iterations".format(5)
