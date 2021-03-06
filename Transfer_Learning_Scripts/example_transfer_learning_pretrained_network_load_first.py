## from https://medium.com/@14prakash/transfer-learning-using-keras-d804b2e04ef8

print("[INFO] Loading necessary libraries.")
from keras import applications
from keras import backend as k 
from keras import optimizers

from keras.applications import inception_v3 as PreTrainedModelSystem
from keras.applications import InceptionV3 as PreTrainedModel

from keras.models import Sequential, Model 
from keras.layers import Dropout, Flatten, Dense, GlobalAveragePooling2D
from keras.preprocessing import image
from keras.preprocessing.image import ImageDataGenerator

from keras.callbacks import ModelCheckpoint, LearningRateScheduler, TensorBoard, EarlyStopping

from glob import glob
from sklearn.preprocessing import LabelBinarizer
from time import time
from tqdm import tqdm

import numpy as np
import os
import random

def glob_subdirectories(base_dir, verbose=False):
    list_of_files = []
    if verbose: print('[INFO] Globbing {}'.format('{}/*'.format(base_dir)))
    for subdir in glob('{}/*'.format(base_dir)):
        if verbose: print('[INFO] Globbing {}'.format('{}/*'.format(subdir)))
        list_of_files.extend(glob('{}/*'.format(subdir)))
    
    return list_of_files

def load_data_from_file(filenames, img_size=256):
    
    print('[INFO] Loading images and reshaping to {}x{}'.format(img_size, img_size))
    
    features = []
    labels = []
    
    # loop over the input images
    for kimage, imagePath in tqdm(enumerate(filenames), total=len(filenames)):
        img = image.load_img(imagePath, target_size=(img_size, img_size))
        img = image.img_to_array(img, dtype='uint8')[:,:,:1]
        img = np.expand_dims(img, axis=0)
        img = PreTrainedModelSystem.preprocess_input(img)
        features.append(img[0])
        
        # extract the class label from the image path and update the
        # labels list
        label = imagePath.split(os.path.sep)[-2] # /path/to/data/class_name/filename.jpg
        labels.append(label)
        
        del imagePath
    
    return features, labels

print("[INFO] Establishing the location and size of our images.")
img_width, img_height = 256, 256
# base_dir = '/Research/HST_Public_DLN/Data'
# train_data_dir = os.environ['HOME'] + base_dir + "/train"
# validation_data_dir = os.environ['HOME'] + base_dir + "/validation"

base_dir = '/Research/QuickLookDLN/dataset_all'
train_data_dir = os.environ['HOME'] + base_dir + "/train"
validation_data_dir = os.environ['HOME'] + base_dir + "/validation"

# nb_train_samples = 4125
# nb_validation_samples = 466

print("[INFO] Establishing the run parameters for the network.")
batch_size = 16
epochs = 50

# grab the image paths and randomly shuffle them
print("[INFO] loading training images...")
train_filenames = glob_subdirectories(train_data_dir)

print("[INFO] loading validation images...")
validation_filenames = glob_subdirectories(validation_data_dir)

random.seed(42)
random.shuffle(train_filenames)
random.shuffle(validation_filenames)

trainX, trainY = load_data_from_file(train_filenames, img_size=img_width)#, n_jobs=args['ncores'], verbose=True)
testX, testY = load_data_from_file(validation_filenames, img_size=img_width)#, n_jobs=args['ncores'], verbose=True)

# binarize the labels - one hot encoding
lb = LabelBinarizer()
trainY = lb.fit_transform(trainY)
testY = lb.transform(testY)

num_classes = len(lb.classes_)

print("[INFO] Creating image augmentation generator.")
# Initiate the train and test generators with data Augumentation 
train_datagen = ImageDataGenerator(
rescale = 1./255,
horizontal_flip = True,
fill_mode = "nearest",
zoom_range = 0.3,
width_shift_range = 0.3,
height_shift_range=0.3,
rotation_range=30)

print("[INFO] Establishing the base model network to transfer from.")
model = PreTrainedModel(weights = "imagenet", include_top=False, input_shape = (img_width, img_height, 3))

print("[INFO] Turning off all layers except top layer.")
# Freeze the layers which you don't want to train. Here I am freezing the first 5 layers.
for layer in model.layers:#[:5]
    layer.trainable = False

#Adding custom Layers 
print("[INFO] Adding new layers for transfer flexibility.")

hidden_new_layer1 = 1024
hidden_new_layer2 = 1024
dropout_rate = 0.5

x = model.output
x = Flatten()(x)
x = Dense(hidden_new_layer1, activation="relu")(x)
x = Dropout(dropout_rate)(x)
x = Dense(hidden_new_layer2, activation="relu")(x)
predictions = Dense(num_classes, activation="softmax")(x)

# creating the final model 
model_final = Model(input = model.input, output = predictions)

print("[INFO] Compiling the model for transfer training.")
# compile the model 
model_final.compile(loss = "categorical_crossentropy", optimizer='adam', metrics=["accuracy"])

print(model_final.summary())

print("[INFO] Creating our set of call back operations.")
# Save the model according to the conditions  
tensboard = TensorBoard(log_dir='./logs/log-{}'.format(int(time())))
checkpoint = ModelCheckpoint("{}_1.h5".format(base_model.name), monitor='val_acc', verbose=1, save_best_only=True, save_weights_only=False, mode='auto', period=1)
early = EarlyStopping(monitor='val_acc', min_delta=0, patience=10, verbose=1, mode='auto')
callbacks_list = [checkpoint, early, tensboard]

print("[INFO] Fitting the transfer network with `fit_generator` flowing from directory.")
# Train the model 
H = model.fit_generator(train_datagen.flow(trainX, trainY, batch_size=batch_size), epochs=epochs, verbose=True, 
                                  callbacks=callbacks_list, validation_data=(testX, testY), shuffle=True)
                                  # steps_per_epoch=len(trainX) // BATCH_SIZE, shuffle=SHUFFLE)


# model_final.fit_generator(
# train_generator,
# samples_per_epoch = nb_train_samples,
# epochs = epochs,
# validation_data = validation_generator,
# nb_val_samples = nb_validation_samples,
# callbacks = [checkpoint, early, tensboard])

print("[INFO] Finished full run process")

"""
Layer (type)                 Output Shape              Param #   
=================================================================
input_1 (InputLayer)         (None, 256, 256, 3)       0         
_________________________________________________________________
block1_conv1 (Conv2D)        (None, 256, 256, 64)      1792      
_________________________________________________________________
block1_conv2 (Conv2D)        (None, 256, 256, 64)      36928     
_________________________________________________________________
block1_pool (MaxPooling2D)   (None, 128, 128, 64)      0         
_________________________________________________________________
block2_conv1 (Conv2D)        (None, 128, 128, 128)     73856     
_________________________________________________________________
block2_conv2 (Conv2D)        (None, 128, 128, 128)     147584    
_________________________________________________________________
block2_pool (MaxPooling2D)   (None, 64, 64, 128)       0         
_________________________________________________________________
block3_conv1 (Conv2D)        (None, 64, 64, 256)       295168    
_________________________________________________________________
block3_conv2 (Conv2D)        (None, 64, 64, 256)       590080    
_________________________________________________________________
block3_conv3 (Conv2D)        (None, 64, 64, 256)       590080    
_________________________________________________________________
block3_conv4 (Conv2D)        (None, 64, 64, 256)       590080    
_________________________________________________________________
block3_pool (MaxPooling2D)   (None, 32, 32, 256)       0         
_________________________________________________________________
block4_conv1 (Conv2D)        (None, 32, 32, 512)       1180160   
_________________________________________________________________
block4_conv2 (Conv2D)        (None, 32, 32, 512)       2359808   
_________________________________________________________________
block4_conv3 (Conv2D)        (None, 32, 32, 512)       2359808   
_________________________________________________________________
block4_conv4 (Conv2D)        (None, 32, 32, 512)       2359808   
_________________________________________________________________
block4_pool (MaxPooling2D)   (None, 16, 16, 512)       0         
_________________________________________________________________
block5_conv1 (Conv2D)        (None, 16, 16, 512)       2359808   
_________________________________________________________________
block5_conv2 (Conv2D)        (None, 16, 16, 512)       2359808   
_________________________________________________________________
block5_conv3 (Conv2D)        (None, 16, 16, 512)       2359808   
_________________________________________________________________
block5_conv4 (Conv2D)        (None, 16, 16, 512)       2359808   
_________________________________________________________________
block5_pool (MaxPooling2D)   (None, 8, 8, 512)         0         
=================================================================
Total params: 20,024,384.0
Trainable params: 20,024,384.0
Non-trainable params: 0.0
"""
