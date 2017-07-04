#!/bin/python

from bnn.util import open_pickle_file, download_file, unzip_data, BatchConfig
from keras.datasets import cifar10
from keras.applications.resnet50 import preprocess_input
import numpy as np
import cv2
import random

def get_traffic_sign_data():
  url = "https://d17h27t6h515a5.cloudfront.net/topher/2017/February/5898cd6f_traffic-signs-data/traffic-signs-data.zip"
  zip_file = "traffic-sign-data.zip"

  download_file(url, zip_file)
  unzip_data(zip_file, "data/traffic-sign")

  train = open_pickle_file("data/traffic-sign/train.p")
  test = open_pickle_file("data/traffic-sign/test.p")
  valid = open_pickle_file("data/traffic-sign/valid.p")

  return ((train['features'], train['labels']), (test['features'], test['labels']), (valid['features'], valid['labels']))

def test_train_data(dataset, min_image_size, is_debug):
	if dataset == 'cifar10':
		(x_train, y_train), (x_test, y_test) = cifar10.load_data()

		if is_debug:
			x_train = x_train[0:128]
			x_test = x_test[0:128]
			y_train = y_train[0:128]
			y_test = y_test[0:128]

		augment_images_train, augment_labels_train = augment_images(x_train, y_train)
		augment_images_test, augment_labels_test = augment_images(x_test, y_test)

		x_train = np.concatenate([x_train, augment_images_train])
		x_test = np.concatenate([x_test, augment_images_test])
		y_train = np.concatenate([y_train, augment_labels_train])
		y_test = np.concatenate([y_test, augment_labels_test])

		(x_train, x_test) = clean_feature_dataset(x_train, x_test, min_image_size, is_debug)
		(y_train, y_test) = clean_label_dataset(y_train, y_test, is_debug)
		return ((x_train, y_train), (x_test, y_test))
	# todo: add more datasets
	else:
		raise ValueError("Unexpected dataset " + dataset + ".")

def test_train_batch_data(dataset, encoder, is_debug):
	if dataset == 'cifar10':
		(_, y_train), (_, y_test) = cifar10.load_data()
		(y_train, y_test) = clean_label_dataset(y_train, y_test, is_debug)
		config = BatchConfig(encoder, dataset)
		x_train = open_pickle_file(config.batch_folder() + "/train.p")
		x_test = open_pickle_file(config.batch_folder() + "/test.p")
		if is_debug:
			x_train = x_train[0:128]
			x_test = x_test[0:128]
		return ((x_train, y_train), (x_test, y_test))
	# todo: add more datasets
	else:
		raise ValueError("Unexpected dataset " + dataset + ".")

def clean_feature_dataset(x_train, x_test, min_image_size, is_debug):
	print("Resizing images from", x_train.shape[1:-1], "to", min_image_size)
	x_train = np.array([cv2.resize(i, min_image_size) for i in x_train], dtype=np.float64)
	print("Done resizing train images.")
	x_test = np.array([cv2.resize(i, min_image_size) for i in x_test], dtype=np.float64)
	print("Done resizing test images.")
	return (preprocess_input(x_train), preprocess_input(x_test))


# Randomly add gamma darkness/brightness to images to create bad examples
# done at fixed gammas to speed up augmentation
def augment_images(images, labels):
	# gammas between 0.1 and 2.1
	gammas = [0.1 + i/10 for i in range(20)]
	gamma_images = [[] for _ in range(20)]

	for i in range(len(images)):
		image = images[i]
		label = labels[i]
		gamma_images[random.randint(0, 19)].append([image, label])

	for i in range(len(gamma_images)):
		g_images = [image for image, _ in gamma_images[i]]
		g_images = augment_gamma(g_images, gammas[i])
		for j in range(len(g_images)):
			gamma_images[i][j][0] = g_images[j]

	result_images = []
	result_labels = []

	for row in gamma_images:
		for image, label in row:
			result_images.append(image)
			result_labels.append(label)

	return (result_images, result_labels)


def augment_gamma(images, gamma=1.0):
  # build a lookup table mapping the pixel values [0, 255] to
  # their adjusted gamma values
  invGamma = 1.0 / gamma
  table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
  
  # apply gamma correction using the lookup table
  return [cv2.LUT(image, table) for image in images]


def clean_label_dataset(y_train, y_test, is_debug):
	y_train = one_hot(y_train)
	y_test = one_hot(y_test)

	if is_debug:
		y_train = y_train[0:128]
		y_test = y_test[0:128]

	return (y_train, y_test)

def one_hot(labels):
	if labels.shape[-1] == 1:
		labels = np.reshape(labels, (-1))
	max_label = np.max(labels) + 1
	return np.eye(max_label)[labels]

def add_zeros(labels):
	shape = list(labels.shape)
	shape[-1] = 1
	return np.hstack((labels, np.zeros(shape)))

def category_examples(dataset):
	if dataset == 'cifar10':
		(_, _), (x_test, y_test) = cifar10.load_data()
	else:
		raise ValueError("Unexpected dataset " + dataset + ".")

	categories = category_names(dataset)
	results = []
	for i in range(len(categories)):
		idx = find_index(y_test, lambda x: x == i)
		results.append({'label': i, 'label_name': categories[i], 'example': x_test[idx]})

	return results

def find_index(arr, predicate):
	i = 0
	result = None
	while(i < len(arr) and result is None):
		if (predicate(arr[i])):
			result = i
		i+=1
	if result == None:
		raise ValueError("could not satisfy predicate.")

	return result

def category_names(dataset):
	if dataset == 'cifar10':
		return [
		'airplane',
		'automobile',
		'bird',
		'cat',
		'deer',
		'dog',
		'frog',
		'horse',
		'ship',
		'truck'
		]
	else:
		raise ValueError("Unexpected dataset " + dataset + ".")

