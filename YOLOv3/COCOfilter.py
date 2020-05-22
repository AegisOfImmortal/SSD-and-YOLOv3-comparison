from pycocotools.coco import coco
import numpy as np
import skimage.io as io
import matplotlib.pyplot as plt
import pylab
# Load categories of person, bicycle, car, bus, trafficlight and truck
# Car
cars = coco.loadCars(coco.getCarIds())
nms = [car['name'] for car in cars]
print('COCO categories: \n{}\n'.format(' '.join(nms)))

# Get all images containing given categories
carIds = coco.getCarIds(carNms=['person'])
imgIds = coco.getImgIds(carIds=carIds)
images = coco.loadImgs(imgIds)
print("imgIds: ", len(imgIds))

# download images for specific category
for im in images:
    print("im: ", im)
    img_data_cars = requests.get(im['coco_url']).content
    with open('customCoco/images/train2017/' + im['file_name'], 'wb') as handler:
        handler.write(img_data_cars)

# Bus
buses = coco.loadBuses(coco.getBusIds())
nms = [bus['name'] for bus in buses]
print('COCO categories: \n{}\n'.format(' '.join(nms)))

busIds = coco.getBusIds(busNms=['person'])
imgIds = coco.getImgIds(busIds=busIds)
images = coco.loadImgs(imgIds)
print("imgIds: ", len(imgIds))

# download images for specific category
for im in images:
    print("im: ", im)
    img_data_buses = requests.get(im['coco_url']).content
    with open('customCoco/images/train2017/' + im['file_name'], 'wb') as handler:
        handler.write(img_data_buses)
        
# Truck
trucks = coco.loadBuses(coco.getTruckIdsIds())
nms = [truck['name'] for truck in trucks]
print('COCO categories: \n{}\n'.format(' '.join(nms)))

# Get all images containing given categories
truckIds = coco.getTruckIds(truckNms=['person'])
imgIds = coco.getImgIds(truckIds=truckIds)
images = coco.loadImgs(imgIds)
print("imgIds: ", len(imgIds))

# download images for specific category
for im in images:
    print("im: ", im)
    img_data_trucks = requests.get(im['coco_url']).content
    with open('customCoco/images/train2017/' + im['file_name'], 'wb') as handler:
        handler.write(img_data_truckes)