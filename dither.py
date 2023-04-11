from PIL import Image
import numpy as np

from matplotlib import pyplot as plt
palette=[(int(R*255/7+0.5),int(G*255/7+0.5),int(B*255/3+0.5)) for R in range(8) for G in range(8) for B in  range(4)]

def nearest(i,n=8,imax=255):
  delta=imax/(n-1)
  iq=int(((i+delta/2)//delta)*delta+0.5)
  if iq<0:iq=0
  if iq>imax:iq=imax
  return iq,i-iq

def RGBto332(rgb):
  deltaRG=255/7
  deltaB=255/3
  return int(max(0,min(7,(rgb[0]+deltaRG/2)//deltaRG)))<<5 | int(max(0,min(7,(rgb[1]+deltaRG/2)//deltaRG)))<<2 | int(max(0,min(3,(rgb[2]+deltaB/2)//deltaB)))
 
def b332toRGB(b332):
  deltaRG=255/7
  deltaB=255/3
  return (int(((b332>>5)&7)*deltaRG+0.5),int(((b332>>2)&7)*deltaRG+0.5),int((b332&3)*deltaB+0.5))


img=Image.open('IMG_0077.jpeg').crop((35,0,604,427)).resize((640,480))
StarmanData=img.getdata()
imgarr=np.array([[[c for c in pixel] for x in range(640) for pixel in (StarmanData[(y*640+x)],)]for y in range(480)],dtype=float)

for ic in range(3): 
  for y in range(480):
    for x in range(640):
      old_color=imgarr[y,x,ic]
      new_color,error=nearest(old_color,n=[8,8,4][ic],imax=255)
      imgarr[y,x,ic]=new_color
      for dy,dx,f in [[1,-1,3/16],[1,0,5/16],[1,1,1/16],[0,1,7/16]]:
        if ((y+dy)<480) and (((x+dx)<640) or (dy!=0)):
          imgarr[y+dy,max(0,min(639,x+dx)),ic]+=error*f
          
im=Image.fromarray(obj=imgarr.astype(np.uint8),mode='RGB')
z=[RGBto332(pixel) for pixel in imgarr.reshape(-1,3)]
grayscaleImage=Image.new('L',(640,480))
grayscaleImage.putdata(z)

grayscaleImage.save('Starman.png')
z=bytes(Image.open('Starman.png').getdata()) 

imb=Image.new(mode='RGB',size=(640,480))
for y in range(480):
  for x in range(640):
    imb.putpixel((x,y),b332toRGB(z[y*640+x]))
    
grayscaleImage.show()
imb.show()
